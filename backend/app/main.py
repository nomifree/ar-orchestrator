from datetime import date, datetime
from io import BytesIO, StringIO
import csv
import json

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response, StreamingResponse
from pydantic import BaseModel
from openpyxl import Workbook

from .config import AS_OF_DATE, DEFAULT_SCORING
from .db import connect, fetch_dicts, get_config, init_db, rebuild_queue, update_scoring_config


app = FastAPI(title="AR Work Queue & Denial Resolution Orchestrator", version="1.0.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class ScoringConfigPayload(BaseModel):
    weight_days_ar: int
    weight_balance: int
    weight_denial_deadline: int
    weight_stale_followup: int
    weight_payer_risk: int
    weight_repeat_denial: int


class FollowupPayload(BaseModel):
    employee_id: str = "EMP-001"
    action_code: str
    action_description: str = ""
    status_code: str = "IN_PROGRESS"
    amount_recovered: float = 0
    next_action_date: date | None = None
    notes: str = ""


@app.on_event("startup")
def startup() -> None:
    init_db()


def queue_base() -> str:
    return """
    SELECT
        w.claim_id, w.workability_status, w.priority_score, w.priority_level,
        w.score_breakdown, w.recommended_action, w.recommended_action_code,
        w.assigned_to, w.queue_generated_at,
        c.client_id, cl.client_name, c.payer_id, p.payer_name,
        c.patient_id, c.billed_amount, c.paid_amount, c.patient_balance,
        (c.billed_amount - c.paid_amount) AS outstanding_amount,
        c.claim_status, c.days_in_ar, c.aging_bucket, c.submit_date, c.service_date,
        e.employee_name AS assigned_name
    FROM work_queue w
    JOIN claims c ON c.claim_id = w.claim_id
    JOIN clients cl ON cl.client_id = c.client_id
    JOIN payers p ON p.payer_id = c.payer_id
    LEFT JOIN employees e ON e.employee_id = w.assigned_to
    """


@app.get("/health")
def health() -> dict:
    with connect() as conn:
        counts = {}
        for table in ["clients", "payers", "employees", "claims", "denials", "followups", "work_queue"]:
            counts[table] = conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
    return {"status": "ok", "as_of_date": AS_OF_DATE.isoformat(), "counts": counts}


@app.post("/api/v1/queue/refresh")
def refresh_queue() -> dict:
    with connect() as conn:
        rows = rebuild_queue(conn)
    return {"rows": rows, "refreshed_at": datetime.utcnow().isoformat() + "Z"}


@app.get("/api/v1/dashboard/summary")
def dashboard_summary() -> dict:
    with connect() as conn:
        row = fetch_dicts(
            conn,
            """
            SELECT
                COUNT(*) FILTER (WHERE workability_status IN ('Active Workable','Denial Workable','Patient Balance','Escalation Required')) AS actionable_claims,
                COUNT(*) FILTER (WHERE priority_level = 'Critical') AS critical_priority,
                COUNT(*) FILTER (WHERE c.aging_bucket = '90+') AS ar_90_plus,
                COUNT(*) FILTER (WHERE lf.last_followup IS NULL OR DATE_DIFF('day', lf.last_followup, ?) >= 7) AS untouched_7_days,
                SUM(c.billed_amount - c.paid_amount) AS total_outstanding
            FROM work_queue w
            JOIN claims c ON c.claim_id = w.claim_id
            LEFT JOIN (
                SELECT claim_id, MAX(followup_date) AS last_followup
                FROM followups GROUP BY claim_id
            ) lf ON lf.claim_id = w.claim_id
            """,
            [AS_OF_DATE],
        )[0]
        last_refreshed = conn.execute("SELECT MAX(queue_generated_at) FROM work_queue").fetchone()[0]
    return {**row, "as_of_date": AS_OF_DATE.isoformat(), "last_refreshed": str(last_refreshed)}


@app.get("/api/v1/dashboard/aging")
def aging() -> list[dict]:
    with connect() as conn:
        return fetch_dicts(
            conn,
            """
            SELECT c.aging_bucket AS bucket, COUNT(*) AS claim_count,
                   SUM(c.billed_amount - c.paid_amount) AS outstanding_amount
            FROM work_queue w JOIN claims c ON c.claim_id = w.claim_id
            GROUP BY c.aging_bucket
            ORDER BY CASE c.aging_bucket WHEN '0-30' THEN 1 WHEN '31-60' THEN 2 WHEN '61-90' THEN 3 ELSE 4 END
            """,
        )


@app.get("/api/v1/dashboard/denial-mix")
def denial_mix() -> list[dict]:
    with connect() as conn:
        return fetch_dicts(
            conn,
            """
            SELECT denial_category AS category, COUNT(*) AS claim_count, SUM(denied_amount) AS denied_amount
            FROM denials WHERE open_flag = true
            GROUP BY denial_category
            ORDER BY claim_count DESC
            """,
        )


@app.get("/api/v1/dashboard/workability")
def workability() -> list[dict]:
    with connect() as conn:
        return fetch_dicts(
            conn,
            """
            SELECT w.workability_status AS status, COUNT(*) AS claim_count,
                   SUM(c.billed_amount - c.paid_amount) AS outstanding_amount
            FROM work_queue w JOIN claims c ON c.claim_id = w.claim_id
            GROUP BY w.workability_status
            ORDER BY claim_count DESC
            """,
        )


@app.get("/api/v1/meta/filters")
def filters() -> dict:
    with connect() as conn:
        return {
            "clients": fetch_dicts(conn, "SELECT client_id, client_name FROM clients ORDER BY client_name"),
            "payers": fetch_dicts(conn, "SELECT payer_id, payer_name FROM payers ORDER BY payer_name"),
            "employees": fetch_dicts(conn, "SELECT employee_id, employee_name FROM employees WHERE active_flag = true ORDER BY employee_name"),
            "priorities": ["Critical", "High", "Medium", "Low"],
            "workability": fetch_dicts(conn, "SELECT DISTINCT workability_status AS value FROM work_queue ORDER BY value"),
            "aging": ["0-30", "31-60", "61-90", "90+"],
        }


@app.get("/api/v1/queue")
def queue(
    priority: str | None = None,
    client_id: str | None = None,
    payer_id: str | None = None,
    assigned_to: str | None = None,
    workability_status: str | None = None,
    aging_bucket: str | None = None,
    sort: str = "priority_score",
    direction: str = "desc",
    page: int = 1,
    page_size: int = Query(50, le=100),
) -> dict:
    where = []
    params = []
    for column, value in [
        ("w.priority_level", priority),
        ("c.client_id", client_id),
        ("c.payer_id", payer_id),
        ("w.assigned_to", assigned_to),
        ("w.workability_status", workability_status),
        ("c.aging_bucket", aging_bucket),
    ]:
        if value:
            where.append(f"{column} = ?")
            params.append(value)
    where_sql = " WHERE " + " AND ".join(where) if where else ""
    sort_map = {
        "priority_score": "q.priority_score",
        "claim_id": "q.claim_id",
        "outstanding_amount": "q.outstanding_amount",
        "days_in_ar": "q.days_in_ar",
        "last_touch": "lf.last_followup",
    }
    order = "DESC" if direction.lower() == "desc" else "ASC"
    order_col = sort_map.get(sort, "w.priority_score")
    offset = max(page - 1, 0) * page_size
    with connect() as conn:
        count = conn.execute(f"SELECT COUNT(*) FROM ({queue_base()} {where_sql}) q", params).fetchone()[0]
        rows = fetch_dicts(
            conn,
            f"""
            SELECT q.*, lf.last_followup
            FROM ({queue_base()} {where_sql}) q
            LEFT JOIN (
                SELECT claim_id, MAX(followup_date) AS last_followup FROM followups GROUP BY claim_id
            ) lf ON lf.claim_id = q.claim_id
            ORDER BY {order_col} {order}, q.claim_id ASC
            LIMIT ? OFFSET ?
            """,
            params + [page_size, offset],
        )
    for row in rows:
        row["score_breakdown"] = json.loads(row["score_breakdown"])
    return {"rows": rows, "total": count, "page": page, "page_size": page_size}


@app.get("/api/v1/claims/{claim_id}")
def claim_detail(claim_id: str) -> dict:
    with connect() as conn:
        claims = fetch_dicts(conn, f"{queue_base()} WHERE w.claim_id = ?", [claim_id])
        if not claims:
            raise HTTPException(status_code=404, detail="claim not found")
        claim = claims[0]
        claim["score_breakdown"] = json.loads(claim["score_breakdown"])
        denials = fetch_dicts(conn, "SELECT * FROM denials WHERE claim_id = ? ORDER BY denial_date DESC, denial_id DESC", [claim_id])
        followups = fetch_dicts(
            conn,
            """
            SELECT f.*, e.employee_name
            FROM followups f LEFT JOIN employees e ON e.employee_id = f.employee_id
            WHERE f.claim_id = ? ORDER BY f.followup_date DESC, f.followup_id DESC
            """,
            [claim_id],
        )
        payer = fetch_dicts(conn, "SELECT * FROM payers WHERE payer_id = ?", [claim["payer_id"]])[0]
    return {"claim": claim, "denials": denials, "timeline": followups, "payer": payer}


@app.post("/api/v1/claims/{claim_id}/followups")
def log_followup(claim_id: str, payload: FollowupPayload) -> dict:
    with connect() as conn:
        exists = conn.execute("SELECT COUNT(*) FROM claims WHERE claim_id = ?", [claim_id]).fetchone()[0]
        if not exists:
            raise HTTPException(status_code=404, detail="claim not found")
        count = conn.execute("SELECT COUNT(*) FROM followups WHERE claim_id = ?", [claim_id]).fetchone()[0]
        followup_id = f"FUP-{claim_id[-5:]}-{count + 1}"
        conn.execute(
            """
            INSERT INTO followups
            (followup_id, claim_id, employee_id, followup_date, action_code, action_description,
             status_code, amount_recovered, next_action_date, notes)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            [
                followup_id,
                claim_id,
                payload.employee_id,
                AS_OF_DATE,
                payload.action_code,
                payload.action_description,
                payload.status_code,
                payload.amount_recovered,
                payload.next_action_date,
                payload.notes,
            ],
        )
        rebuild_queue(conn)
    return {"followup_id": followup_id, "claim_id": claim_id, "refreshed": True}


@app.get("/api/v1/reps")
def reps() -> list[dict]:
    with connect() as conn:
        rows = fetch_dicts(
            conn,
            """
            SELECT e.employee_id, e.employee_name, e.team, e.role, e.shift,
                   COUNT(DISTINCT w.claim_id) AS queue_size,
                   COALESCE(SUM(f.amount_recovered), 0) AS recovered_amount,
                   COUNT(f.followup_id) AS total_touches,
                   COUNT(f.followup_id) FILTER (WHERE f.status_code = 'RESOLVED') AS resolved_touches,
                   COUNT(DISTINCT w.claim_id) FILTER (WHERE w.priority_level = 'Critical') AS critical_claims,
                   COUNT(DISTINCT w.claim_id) FILTER (WHERE c.days_in_ar > 90) AS stale_claims
            FROM employees e
            LEFT JOIN work_queue w ON w.assigned_to = e.employee_id
            LEFT JOIN claims c ON c.claim_id = w.claim_id
            LEFT JOIN followups f ON f.employee_id = e.employee_id
            WHERE e.team IN ('AR Follow-up', 'Coding', 'Management')
            GROUP BY e.employee_id, e.employee_name, e.team, e.role, e.shift
            ORDER BY recovered_amount DESC
            """,
        )
    for row in rows:
        touches = row["total_touches"] or 0
        row["touch_efficiency"] = round((row["resolved_touches"] or 0) / touches * 100, 1) if touches else 0
        row["denial_win_rate"] = row["touch_efficiency"]
        row["performance_band"] = "High" if row["touch_efficiency"] >= 35 else ("Average" if row["touch_efficiency"] >= 18 else "Needs Coaching")
    return rows


@app.get("/api/v1/clients")
def clients() -> list[dict]:
    with connect() as conn:
        rows = fetch_dicts(
            conn,
            """
            SELECT cl.client_id, cl.client_name, cl.specialty,
                   COUNT(DISTINCT w.claim_id) AS queue_size,
                   SUM(c.billed_amount - c.paid_amount) AS outstanding_amount,
                   COUNT(DISTINCT d.denial_id) FILTER (WHERE d.open_flag = true) AS open_denials,
                   COUNT(DISTINCT c.claim_id) FILTER (WHERE c.aging_bucket = '90+') AS ar_90_plus,
                   COUNT(DISTINCT w.claim_id) FILTER (WHERE w.priority_level = 'Critical') AS critical_claims
            FROM clients cl
            LEFT JOIN claims c ON c.client_id = cl.client_id
            LEFT JOIN work_queue w ON w.claim_id = c.claim_id
            LEFT JOIN denials d ON d.claim_id = c.claim_id
            GROUP BY cl.client_id, cl.client_name, cl.specialty
            ORDER BY outstanding_amount DESC
            """,
        )
    for row in rows:
        row["sla_status"] = "Breached" if row["critical_claims"] >= 10 else ("At Risk" if row["ar_90_plus"] >= 12 else "On Track")
    return rows


@app.get("/api/v1/clients/{client_id}/pack")
def client_pack(client_id: str) -> dict:
    with connect() as conn:
        client_rows = fetch_dicts(conn, "SELECT * FROM clients WHERE client_id = ?", [client_id])
        if not client_rows:
            raise HTTPException(status_code=404, detail="client not found")
        summary = [row for row in clients() if row["client_id"] == client_id][0]
        backlog = fetch_dicts(conn, f"{queue_base()} WHERE c.client_id = ? ORDER BY w.priority_score DESC LIMIT 10", [client_id])
        denials = fetch_dicts(
            conn,
            """
            SELECT denial_category, COUNT(*) AS count, SUM(denied_amount) AS denied_amount
            FROM denials d JOIN claims c ON c.claim_id = d.claim_id
            WHERE c.client_id = ? AND d.open_flag = true
            GROUP BY denial_category ORDER BY count DESC
            """,
            [client_id],
        )
    trend = "Critical backlog needs manager review this week." if summary["critical_claims"] else "AR queue is stable with no critical concentration."
    return {"client": client_rows[0], "summary": summary, "denials": denials, "top_claims": backlog, "trend_sentence": trend}


@app.get("/api/v1/settings/scoring")
def get_scoring() -> dict:
    with connect() as conn:
        return get_config(conn)


@app.put("/api/v1/settings/scoring")
def put_scoring(payload: ScoringConfigPayload) -> dict:
    try:
        with connect() as conn:
            return update_scoring_config(conn, payload.model_dump())
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


def rows_to_csv(rows: list[dict]) -> str:
    output = StringIO()
    if not rows:
        return ""
    writer = csv.DictWriter(output, fieldnames=list(rows[0].keys()), extrasaction="ignore")
    writer.writeheader()
    writer.writerows(rows)
    return output.getvalue()


@app.get("/api/v1/exports/queue.csv")
def export_queue_csv(priority: str | None = None) -> Response:
    data = queue(priority=priority, page_size=100)["rows"]
    for row in data:
        row["score_breakdown"] = json.dumps(row["score_breakdown"])
    return Response(
        rows_to_csv(data),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=ar_work_queue.csv"},
    )


def workbook_response(wb: Workbook, filename: str) -> StreamingResponse:
    stream = BytesIO()
    wb.save(stream)
    stream.seek(0)
    return StreamingResponse(
        stream,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )


def add_sheet(wb: Workbook, title: str, rows: list[dict]) -> None:
    ws = wb.create_sheet(title)
    if not rows:
        ws.append(["No rows"])
        return
    headers = list(rows[0].keys())
    ws.append(headers)
    for row in rows:
        ws.append([json.dumps(row[h]) if isinstance(row.get(h), (dict, list)) else row.get(h) for h in headers])


@app.get("/api/v1/exports/queue.xlsx")
def export_queue_xlsx() -> StreamingResponse:
    wb = Workbook()
    wb.remove(wb.active)
    add_sheet(wb, "Queue", queue(page_size=100)["rows"])
    add_sheet(wb, "Aging", aging())
    add_sheet(wb, "Denial Mix", denial_mix())
    add_sheet(wb, "Critical Claims", queue(priority="Critical", page_size=100)["rows"])
    return workbook_response(wb, "ar_work_queue_pack.xlsx")


@app.get("/api/v1/exports/client/{client_id}.xlsx")
def export_client_xlsx(client_id: str) -> StreamingResponse:
    pack = client_pack(client_id)
    wb = Workbook()
    wb.remove(wb.active)
    add_sheet(wb, "AR Summary", [pack["summary"]])
    add_sheet(wb, "Open Denials", pack["denials"])
    add_sheet(wb, "Action Backlog", pack["top_claims"])
    add_sheet(wb, "Top Claims", pack["top_claims"][:10])
    add_sheet(wb, "Period Trend", [{"trend": pack["trend_sentence"]}])
    return workbook_response(wb, f"{client_id}_client_pack.xlsx")
