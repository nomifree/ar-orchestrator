from fastapi.testclient import TestClient

from backend.app.db import init_db
from backend.app.main import app


client = TestClient(app)


def setup_module():
    init_db(force_reset=True)


def test_health_counts_seeded_tables():
    response = client.get("/health")
    assert response.status_code == 200
    counts = response.json()["counts"]
    assert counts["claims"] == 321
    assert counts["work_queue"] > 0


def test_dashboard_summary_returns_expected_keys():
    data = client.get("/api/v1/dashboard/summary").json()
    for key in ["actionable_claims", "critical_priority", "ar_90_plus", "untouched_7_days", "total_outstanding"]:
        assert key in data


def test_queue_filters_by_priority_level():
    data = client.get("/api/v1/queue?priority=Critical").json()
    assert data["total"] > 0
    assert all(row["priority_level"] == "Critical" for row in data["rows"])


def test_claim_detail_includes_timeline_and_score_breakdown():
    data = client.get("/api/v1/claims/CLM-10021").json()
    assert data["claim"]["priority_level"] == "Critical"
    assert data["timeline"]
    assert "denial_deadline" in data["claim"]["score_breakdown"]


def test_scoring_config_update_refreshes_queue():
    payload = {
        "weight_days_ar": 20,
        "weight_balance": 25,
        "weight_denial_deadline": 20,
        "weight_stale_followup": 15,
        "weight_payer_risk": 10,
        "weight_repeat_denial": 10,
    }
    response = client.put("/api/v1/settings/scoring", json=payload)
    assert response.status_code == 200
    assert response.json()["weight_balance"] == 25
    data = client.get("/api/v1/claims/CLM-10021").json()
    assert data["claim"]["score_breakdown"]["balance"] >= 0


def test_export_queue_xlsx_returns_workbook():
    response = client.get("/api/v1/exports/queue.xlsx")
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("application/vnd.openxmlformats")
    assert response.content[:2] == b"PK"


def test_claim_upload_validates_and_applies_template_row():
    template = client.get("/api/v1/upload/claims/template.csv")
    assert template.status_code == 200
    response = client.post(
        "/api/v1/upload/claims?apply=true",
        files={"file": ("claims_upload_template.csv", template.text, "text/csv")},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["received_rows"] == 1
    assert data["valid_rows"] == 1
    assert data["error_rows"] == 0
    assert data["applied_rows"] == 1
    detail = client.get("/api/v1/claims/CLM-UPLOAD-001")
    assert detail.status_code == 200


def test_claim_upload_reports_bad_rows_without_apply():
    bad_csv = "\n".join(
        [
            "claim_id,client_id,payer_id,patient_id,service_date,submit_date,billed_amount,paid_amount,patient_balance,claim_status,cpt_codes,icd10_codes,claim_type,assigned_to",
            "CLM-BAD,CLI-NOPE,PAY-002,John Smith,2026-03-20,2026-03-15,-10,0,0,BadStatus,99214,I10,Professional,EMP-001",
        ]
    )
    response = client.post("/api/v1/upload/claims", files={"file": ("bad.csv", bad_csv, "text/csv")})
    assert response.status_code == 200
    data = response.json()
    assert data["valid_rows"] == 0
    assert data["error_rows"] == 1
    assert data["applied_rows"] == 0
    assert data["errors"][0]["errors"]
