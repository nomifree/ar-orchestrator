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


def test_open_denial_before_deadline_is_denial_workable():
    result = classify_workability(claim(claim_status="Denied", days_in_ar=65), denial(days_left=20), None, PAYER, AS_OF)
    assert result == "Denial Workable"


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


def test_future_next_action_returns_waiting_payer():
    result = classify_workability(claim(claim_status="Active", days_in_ar=50), None, followup(next_days=4), PAYER, AS_OF)
    assert result == "Waiting Payer"


def test_overdue_pending_claim_is_active_workable():
    result = classify_workability(claim(claim_status="Pending", days_in_ar=45), None, followup(days_ago=12), PAYER, AS_OF)
    assert result == "Active Workable"


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


def test_90_plus_denial_near_deadline_scores_above_80():
    score, level, breakdown = score_priority(
        claim(days_in_ar=96, billed_amount=850, paid_amount=0),
        denial(days_left=6, repeat=True),
        followup(days_ago=11),
        PAYER,
        CONFIG,
        AS_OF,
    )
    assert score == 90
    assert level == "Critical"
    assert breakdown["balance"] == 15


def test_recently_submitted_small_balance_scores_below_40():
    score, level, _ = score_priority(
        claim(days_in_ar=10, billed_amount=180, paid_amount=0),
        None,
        followup(days_ago=1),
        {"avg_response_days": 30, "risk_level": "Low"},
        CONFIG,
        AS_OF,
    )
    assert score < 40
    assert level == "Low"


def test_repeat_denial_adds_points():
    score_no_repeat = score_priority(claim(days_in_ar=70), denial(days_left=20, repeat=False), followup(days_ago=3), PAYER, CONFIG, AS_OF)[0]
    score_repeat = score_priority(claim(days_in_ar=70), denial(days_left=20, repeat=True), followup(days_ago=3), PAYER, CONFIG, AS_OF)[0]
    assert score_repeat - score_no_repeat == 10


def test_high_payer_risk_adds_more_than_low_payer_risk():
    low = score_priority(claim(days_in_ar=50), None, followup(days_ago=3), {"avg_response_days": 30, "risk_level": "Low"}, CONFIG, AS_OF)[0]
    high = score_priority(claim(days_in_ar=50), None, followup(days_ago=3), {"avg_response_days": 30, "risk_level": "High"}, CONFIG, AS_OF)[0]
    assert high > low


def test_never_touched_claim_gets_max_stale_points():
    _, _, breakdown = score_priority(claim(days_in_ar=50), None, None, PAYER, CONFIG, AS_OF)
    assert breakdown["stale_followup"] == 15


def test_balance_tiers_are_interview_defensible():
    assert score_priority(claim(billed_amount=200, paid_amount=0), None, None, PAYER, CONFIG, AS_OF)[2]["balance"] == 4
    assert score_priority(claim(billed_amount=400, paid_amount=0), None, None, PAYER, CONFIG, AS_OF)[2]["balance"] == 8
    assert score_priority(claim(billed_amount=850, paid_amount=0), None, None, PAYER, CONFIG, AS_OF)[2]["balance"] == 15
    assert score_priority(claim(billed_amount=1500, paid_amount=0), None, None, PAYER, CONFIG, AS_OF)[2]["balance"] == 20


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


def test_timely_filing_without_proof_routes_to_writeoff_review():
    action_code, _ = next_best_action("Denial Workable", claim(), denial(category="Timely Filing", proof=False), None, AS_OF)
    assert action_code == "TIMELY_FILING_WRITEOFF_REVIEW"


def test_active_workable_action_branches():
    assert next_best_action("Active Workable", claim(), None, None, AS_OF)[0] == "CALL_PAYER_URGENT"
    assert next_best_action("Active Workable", claim(), None, followup(days_ago=10), AS_OF)[0] == "CHECK_PAYER_STATUS"
    assert next_best_action("Active Workable", claim(), None, followup(days_ago=3), AS_OF)[0] == "STANDARD_FOLLOWUP"


def test_patient_balance_and_escalation_actions():
    assert next_best_action("Patient Balance", claim(patient_balance=650), None, None, AS_OF)[0] == "PATIENT_PAYMENT_PLAN"
    assert next_best_action("Patient Balance", claim(patient_balance=120), None, None, AS_OF)[0] == "PATIENT_STANDARD_STATEMENT"
    assert next_best_action("Escalation Required", claim(), None, None, AS_OF)[0] == "MANAGER_ESCALATION"
