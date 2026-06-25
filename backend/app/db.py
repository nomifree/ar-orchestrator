from collections import defaultdict
from datetime import datetime
import json

import duckdb

from .config import AS_OF_DATE, DATABASE_PATH, DEFAULT_SCORING
from .rules import ACTIONABLE_STATUSES, classify_workability, next_best_action, score_priority
from .schema import RESET_SQL, SCHEMA_SQL
from .seed import generate_seed_data


def connect() -> duckdb.DuckDBPyConnection:
    return duckdb.connect(str(DATABASE_PATH))


def init_db(force_reset: bool = False) -> None:
    with connect() as conn:
        if force_reset:
            conn.execute(RESET_SQL)
        conn.execute(SCHEMA_SQL)
        ensure_config(conn)
        count = conn.execute("SELECT COUNT(*) FROM claims").fetchone()[0]
        if count == 0:
            load_seed(conn)
        rebuild_queue(conn)


def ensure_config(conn: duckdb.DuckDBPyConnection) -> None:
    conn.execute(SCHEMA_SQL)
    exists = conn.execute("SELECT COUNT(*) FROM scoring_config").fetchone()[0]
    if not exists:
        conn.execute(
            """
            INSERT INTO scoring_config VALUES (1, 'default', ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
            """,
            [
                DEFAULT_SCORING["weight_days_ar"],
                DEFAULT_SCORING["weight_balance"],
                DEFAULT_SCORING["weight_denial_deadline"],
                DEFAULT_SCORING["weight_stale_followup"],
                DEFAULT_SCORING["weight_payer_risk"],
                DEFAULT_SCORING["weight_repeat_denial"],
            ],
        )


def load_seed(conn: duckdb.DuckDBPyConnection) -> None:
    data = generate_seed_data()
    for table, rows in data.items():
        if rows:
            conn.executemany(
                f"INSERT INTO {table} ({', '.join(rows[0].keys())}) VALUES ({', '.join(['?'] * len(rows[0]))})",
                [tuple(row.values()) for row in rows],
            )


def fetch_dicts(conn: duckdb.DuckDBPyConnection, query: str, params: list | None = None) -> list[dict]:
    cur = conn.execute(query, params or [])
    cols = [col[0] for col in cur.description]
    return [dict(zip(cols, row)) for row in cur.fetchall()]


def get_config(conn: duckdb.DuckDBPyConnection) -> dict[str, int]:
    rows = fetch_dicts(conn, "SELECT * FROM scoring_config WHERE config_id = 1")
    if not rows:
        return DEFAULT_SCORING.copy()
    row = rows[0]
    return {key: int(row[key]) for key in DEFAULT_SCORING}


def latest_by_claim(rows: list[dict], date_key: str, id_key: str) -> dict[str, dict]:
    latest: dict[str, dict] = {}
    for row in rows:
        claim_id = row["claim_id"]
        current = latest.get(claim_id)
        candidate_key = (str(row.get(date_key)), str(row.get(id_key)))
        current_key = (str(current.get(date_key)), str(current.get(id_key))) if current else ("", "")
        if current is None or candidate_key > current_key:
            latest[claim_id] = row
    return latest


def rebuild_queue(conn: duckdb.DuckDBPyConnection | None = None) -> int:
    own_conn = conn is None
    conn = conn or connect()
    try:
        config = get_config(conn)
        claims = fetch_dicts(conn, "SELECT * FROM claims")
        denials = fetch_dicts(conn, "SELECT * FROM denials")
        followups = fetch_dicts(conn, "SELECT * FROM followups")
        payers = {row["payer_id"]: row for row in fetch_dicts(conn, "SELECT * FROM payers")}
        latest_denials = latest_by_claim([d for d in denials if d.get("open_flag")], "denial_date", "denial_id")
        latest_followups = latest_by_claim(followups, "followup_date", "followup_id")
        unresolved = defaultdict(int)
        for f in followups:
            if f.get("status_code") in {"IN_PROGRESS", "WAITING", "ESCALATED", "WAITING_CLIENT"} and not float(f.get("amount_recovered") or 0):
                unresolved[f["claim_id"]] += 1

        conn.execute("DELETE FROM work_queue")
        rows = []
        for claim in claims:
            claim = dict(claim)
            claim["unresolved_touches"] = unresolved[claim["claim_id"]]
            payer = payers[claim["payer_id"]]
            latest_denial = latest_denials.get(claim["claim_id"])
            latest_followup = latest_followups.get(claim["claim_id"])
            workability = classify_workability(claim, latest_denial, latest_followup, payer, AS_OF_DATE)
            if workability in {"Closed", "Closed Write-Off"}:
                continue
            score, level, breakdown = score_priority(claim, latest_denial, latest_followup, payer, config, AS_OF_DATE)
            if workability not in ACTIONABLE_STATUSES:
                score = min(score, 39)
                level = "Low"
            action_code, action_text = next_best_action(workability, claim, latest_denial, latest_followup, AS_OF_DATE)
            rows.append(
                (
                    claim["claim_id"],
                    workability,
                    int(score),
                    level,
                    json.dumps(breakdown),
                    action_text,
                    action_code,
                    claim.get("assigned_to") or None,
                    datetime.utcnow(),
                )
            )
        conn.executemany(
            """
            INSERT INTO work_queue
            (claim_id, workability_status, priority_score, priority_level, score_breakdown,
             recommended_action, recommended_action_code, assigned_to, queue_generated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            rows,
        )
        return len(rows)
    finally:
        if own_conn:
            conn.close()


def update_scoring_config(conn: duckdb.DuckDBPyConnection, payload: dict[str, int]) -> dict[str, int]:
    current = get_config(conn)
    current.update({key: int(payload[key]) for key in DEFAULT_SCORING if key in payload})
    total = sum(current.values())
    if total != 100:
        raise ValueError(f"scoring weights must total 100, got {total}")
    conn.execute(
        """
        UPDATE scoring_config
        SET weight_days_ar = ?, weight_balance = ?, weight_denial_deadline = ?,
            weight_stale_followup = ?, weight_payer_risk = ?, weight_repeat_denial = ?,
            updated_at = CURRENT_TIMESTAMP
        WHERE config_id = 1
        """,
        [current[key] for key in DEFAULT_SCORING],
    )
    rebuild_queue(conn)
    return current
