from datetime import date
from typing import Any

from .config import DEFAULT_SCORING


ACTIONABLE_STATUSES = {"Active Workable", "Denial Workable", "Patient Balance", "Escalation Required"}


def parse_date(value: Any) -> date | None:
    if value is None or value == "":
        return None
    if isinstance(value, date):
        return value
    return date.fromisoformat(str(value)[:10])


def dollars_outstanding(claim: dict[str, Any]) -> float:
    return max(float(claim.get("billed_amount") or 0) - float(claim.get("paid_amount") or 0), 0)


def aging_bucket(days_in_ar: int) -> str:
    if days_in_ar <= 30:
        return "0-30"
    if days_in_ar <= 60:
        return "31-60"
    if days_in_ar <= 90:
        return "61-90"
    return "90+"


def priority_level(score: int) -> str:
    if score >= 80:
        return "Critical"
    if score >= 60:
        return "High"
    if score >= 40:
        return "Medium"
    return "Low"


def days_since_followup(latest_followup: dict[str, Any] | None, as_of: date) -> int | None:
    if not latest_followup:
        return None
    followup_date = parse_date(latest_followup.get("followup_date"))
    if not followup_date:
        return None
    return max((as_of - followup_date).days, 0)


def classify_workability(
    claim: dict[str, Any],
    latest_denial: dict[str, Any] | None,
    latest_followup: dict[str, Any] | None,
    payer: dict[str, Any],
    as_of: date,
) -> str:
    status = claim.get("claim_status")
    if status in {"Paid", "Voided"}:
        return "Closed"
    if status in {"Write-Off", "Written Off"}:
        return "Closed Write-Off"

    if latest_denial and latest_denial.get("open_flag"):
        deadline = parse_date(latest_denial.get("appeal_deadline"))
        if deadline and deadline < as_of:
            return "Escalation Required"
        return "Denial Workable"

    patient_balance = float(claim.get("patient_balance") or 0)
    if status == "Partial" and patient_balance > 0:
        return "Patient Balance"

    next_action_date = parse_date((latest_followup or {}).get("next_action_date"))
    if next_action_date and next_action_date > as_of:
        if claim.get("blocker_owner") == "Client" or (latest_followup or {}).get("status_code") == "WAITING_CLIENT":
            return "Waiting Client"
        return "Waiting Payer"

    days_in_ar = int(claim.get("days_in_ar") or 0)
    followup_age = days_since_followup(latest_followup, as_of)
    unresolved_touches = int(claim.get("unresolved_touches") or 0)
    if days_in_ar > 90 and (followup_age is None or followup_age > 14 or unresolved_touches >= 3):
        return "Escalation Required"

    if status in {"System Hold", "Submitted"}:
        return "System Hold"

    avg_response_days = int(payer.get("avg_response_days") or 30)
    if status == "Pending" and days_in_ar <= avg_response_days:
        return "System Hold"

    if status in {"Pending", "Active"} and (days_in_ar > avg_response_days or followup_age is None or followup_age > 7):
        return "Active Workable"

    if claim.get("blocker_owner") == "Client":
        return "Waiting Client"
    return "Waiting Payer"


def score_priority(
    claim: dict[str, Any],
    latest_denial: dict[str, Any] | None,
    latest_followup: dict[str, Any] | None,
    payer: dict[str, Any],
    config: dict[str, int] | None,
    as_of: date,
) -> tuple[int, str, dict[str, int]]:
    cfg = {**DEFAULT_SCORING, **(config or {})}
    days_in_ar = int(claim.get("days_in_ar") or 0)
    bucket = aging_bucket(days_in_ar)
    days_points = {"0-30": 4, "31-60": 10, "61-90": 18, "90+": 25}[bucket]
    days_points = round(days_points / 25 * cfg["weight_days_ar"])

    balance = dollars_outstanding(claim)
    if balance <= 250:
        balance_base = 4
    elif balance <= 500:
        balance_base = 8
    elif balance <= 1000:
        balance_base = 15
    else:
        balance_base = 20
    balance_points = round(balance_base / 20 * cfg["weight_balance"])

    deadline_points = 0
    if latest_denial and latest_denial.get("open_flag"):
        deadline = parse_date(latest_denial.get("appeal_deadline"))
        if deadline:
            days_left = (deadline - as_of).days
            if days_left < 0:
                deadline_points = cfg["weight_denial_deadline"]
            elif days_left <= 7:
                deadline_points = cfg["weight_denial_deadline"]
            elif days_left <= 30:
                deadline_points = round(cfg["weight_denial_deadline"] * 0.75)
            elif days_left <= 60:
                deadline_points = round(cfg["weight_denial_deadline"] * 0.5)
            else:
                deadline_points = round(cfg["weight_denial_deadline"] * 0.25)

    followup_age = days_since_followup(latest_followup, as_of)
    if followup_age is None:
        stale_points = cfg["weight_stale_followup"]
    elif followup_age > 14:
        stale_points = cfg["weight_stale_followup"]
    elif followup_age > 7:
        stale_points = round(cfg["weight_stale_followup"] * 0.7)
    else:
        stale_points = round(cfg["weight_stale_followup"] * 0.2)

    payer_points = {"High": 1.0, "Medium": 0.6, "Low": 0.2}.get(payer.get("risk_level"), 0.6)
    payer_points = round(payer_points * cfg["weight_payer_risk"])

    repeat_points = cfg["weight_repeat_denial"] if latest_denial and latest_denial.get("is_repeat_denial") else 0
    breakdown = {
        "days_ar": int(days_points),
        "balance": int(balance_points),
        "denial_deadline": int(deadline_points),
        "stale_followup": int(stale_points),
        "payer_risk": int(payer_points),
        "repeat_denial": int(repeat_points),
    }
    score = max(0, min(100, sum(breakdown.values())))
    return score, priority_level(score), breakdown


def next_best_action(
    workability: str,
    claim: dict[str, Any],
    latest_denial: dict[str, Any] | None,
    latest_followup: dict[str, Any] | None,
    as_of: date,
) -> tuple[str, str]:
    if workability == "Denial Workable" and latest_denial:
        category = latest_denial.get("denial_category")
        deadline = parse_date(latest_denial.get("appeal_deadline"))
        days_left = (deadline - as_of).days if deadline else None
        if category == "Authorization":
            if days_left is not None and days_left < 0:
                return "AUTH_EXPIRED_WRITEOFF_REVIEW", "Appeal deadline passed - initiate write-off review"
            if days_left is not None and days_left <= 7:
                return "AUTH_URGENT_APPEAL", "URGENT: File authorization appeal today or escalate"
            return "AUTH_PREP_APPEAL", "Review authorization evidence; prepare appeal"
        if category == "Eligibility":
            return "VERIFY_ELIGIBILITY_RESUBMIT", "Verify patient eligibility on DOS; correct plan; resubmit"
        if category == "COB":
            return "CORRECT_COB_RESUBMIT", "Confirm primary/secondary payer order; resubmit with correct COB"
        if category == "Coding":
            return "CODER_REVIEW_RESUBMIT", "Flag to coder; review CPT/ICD-10; correct and resubmit"
        if category == "Timely Filing":
            if latest_denial.get("proof_on_file"):
                return "TIMELY_FILING_APPEAL_PROOF", "File appeal with original submission proof; otherwise prepare write-off review"
            return "TIMELY_FILING_WRITEOFF_REVIEW", "Check submission proof; if none exists, route to write-off review"
        if category == "Documentation":
            return "REQUEST_RECORDS_RESUBMIT", "Request medical records from provider; resubmit with documentation"

    if workability == "Active Workable":
        age = days_since_followup(latest_followup, as_of)
        if age is None or age > 14:
            return "CALL_PAYER_URGENT", "Call payer - claim may be lost in system"
        if age > 7:
            return "CHECK_PAYER_STATUS", "Check claim status with payer"
        return "STANDARD_FOLLOWUP", "Standard follow-up - check ERA/EFT status"

    if workability == "Patient Balance":
        if float(claim.get("patient_balance") or 0) > 500:
            return "PATIENT_PAYMENT_PLAN", "Send statement + payment plan offer"
        return "PATIENT_STANDARD_STATEMENT", "Send standard patient statement"

    if workability == "Escalation Required":
        return "MANAGER_ESCALATION", "Escalate to manager - review claim history and authorize next step"

    if workability == "Waiting Client":
        return "WAIT_CLIENT_DOCS", "Wait for provider/client response before next action"
    if workability in {"System Hold", "Waiting Payer"}:
        return "WAIT_NO_TOUCH", "No rep touch today - waiting on system or payer response"
    return "NO_ACTION", "No action required"
