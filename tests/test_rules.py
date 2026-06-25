from datetime import date, timedelta

from backend.app.rules import classify_workability, next_best_action, priority_level, score_priority


AS_OF = date(2026, 6, 25)
PAYER = {"avg_response_days": 30, "risk_level": "High"}
CONFIG = {
    "weight_days_ar": 25,
    "weight_balance": 20,
    "weight_denial_deadline": 20,
    "weight_stale_followup": 15,
    "weight_payer_risk": 10,
    "weight_repeat_denial": 10,
}


def claim(**overrides):
    base = {
        "claim_id": "CLM-T",
        "claim_status": "Active",
        "days_in_ar": 45,
        "billed_amount": 1000,
        "paid_amount": 0,
        "patient_balance": 0,
        "blocker_owner": None,
        "unresolved_touches": 0,
    }
    base.update(overrides)
    return base


def denial(category="Authorization", days_left=7, repeat=False, proof=True):
    return {
        "denial_category": category,
        "appeal_deadline": AS_OF + timedelta(days=days_left),
        "open_flag": True,
        "is_repeat_denial": repeat,
        "proof_on_file": proof,
    }


def followup(days_ago=10, status="IN_PROGRESS", next_days=None):
    return {
        "followup_date": AS_OF - timedelta(days=days_ago),
        "status_code": status,
        "next_action_date": AS_OF + timedelta(days=next_days) if next_days else None,
    }


def test_paid_and_voided_claims_are_closed():
    assert classify_workability(claim(claim_status="Paid"), None, None, PAYER, AS_OF) == "Closed"
    assert classify_workability(claim(claim_status="Voided"), None, None, PAYER, AS_OF) == "Closed"


def test_expired_appeal_deadline_escalates_before_denial_workable():
    result = classify_workability(claim(claim_status="Denied", days_in_ar=100), denial(days_left=-1), None, PAYER, AS_OF)
    assert result == "Escalation Required"


def test_authorization_deadline_branches_are_ordered():
    assert next_best_action("Denial Workable", claim(), denial(days_left=-2), None, AS_OF)[0] == "AUTH_EXPIRED_WRITEOFF_REVIEW"
    assert next_best_action("Denial Workable", claim(), denial(days_left=6), None, AS_OF)[0] == "AUTH_URGENT_APPEAL"
    assert next_best_action("Denial Workable", claim(), denial(days_left=30), None, AS_OF)[0] == "AUTH_PREP_APPEAL"


def test_all_six_denial_categories_return_codes():
    expected = {
        "Eligibility": "VERIFY_ELIGIBILITY_RESUBMIT",
        "COB": "CORRECT_COB_RESUBMIT",
        "Coding": "CODER_REVIEW_RESUBMIT",
        "Timely Filing": "TIMELY_FILING_APPEAL_PROOF",
        "Documentation": "REQUEST_RECORDS_RESUBMIT",
    }
    for category, code in expected.items():
        assert next_best_action("Denial Workable", claim(), denial(category=category), None, AS_OF)[0] == code


def test_patient_balance_and_waiting_client_classification():
    assert classify_workability(claim(claim_status="Partial", patient_balance=650), None, None, PAYER, AS_OF) == "Patient Balance"
    assert classify_workability(claim(blocker_owner="Client"), None, followup(next_days=5, status="WAITING_CLIENT"), PAYER, AS_OF) == "Waiting Client"


def test_pending_inside_payer_window_is_system_hold():
    result = classify_workability(claim(claim_status="Pending", days_in_ar=12), None, None, PAYER, AS_OF)
    assert result == "System Hold"


def test_90_plus_unresolved_claim_escalates():
    result = classify_workability(claim(days_in_ar=110, unresolved_touches=3), None, followup(days_ago=20), PAYER, AS_OF)
    assert result == "Escalation Required"


def test_priority_score_breakdown_and_clamp():
    score, level, breakdown = score_priority(
        claim(days_in_ar=120, billed_amount=5000),
        denial(days_left=3, repeat=True),
        None,
        PAYER,
        CONFIG,
        AS_OF,
    )
    assert score == 100
    assert level == "Critical"
    assert sum(breakdown.values()) >= 100


def test_priority_boundaries():
    assert priority_level(39) == "Low"
    assert priority_level(40) == "Medium"
    assert priority_level(59) == "Medium"
    assert priority_level(60) == "High"
    assert priority_level(79) == "High"
    assert priority_level(80) == "Critical"


def test_config_weight_change_changes_score():
    original = score_priority(claim(days_in_ar=20, billed_amount=2500), None, None, PAYER, CONFIG, AS_OF)[0]
    changed = dict(CONFIG, weight_balance=40, weight_days_ar=5)
    new_score = score_priority(claim(days_in_ar=20, billed_amount=2500), None, None, PAYER, changed, AS_OF)[0]
    assert new_score != original
