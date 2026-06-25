from datetime import timedelta
import random

from .config import AS_OF_DATE, DEFAULT_SCORING
from .rules import aging_bucket


CLIENTS = [
    ("CLI-001", "Sunrise Family Clinic", "Family Medicine", 45),
    ("CLI-002", "Islamabad Ortho Group", "Orthopedics", 40),
    ("CLI-003", "Crescent Pediatrics", "Pediatrics", 35),
    ("CLI-004", "Capital Cardiology", "Cardiology", 45),
    ("CLI-005", "Northview Imaging", "Radiology", 30),
]

PAYERS = [
    ("PAY-001", "Aetna", "Commercial", 28, 90, "Medium", "https://www.aetna.com"),
    ("PAY-002", "UnitedHealthcare", "Commercial", 35, 120, "High", "https://www.uhc.com"),
    ("PAY-003", "Medicare", "Medicare", 21, 120, "Low", "https://www.cms.gov"),
    ("PAY-004", "Blue Cross", "Commercial", 31, 90, "Medium", "https://www.bcbs.com"),
    ("PAY-005", "Cigna", "Commercial", 33, 90, "High", "https://www.cigna.com"),
]

EMPLOYEES = [
    ("EMP-001", "Ahmed Khan", "AR Follow-up", "Billing Executive", "Night", "EMP-005", True, "2024-02-12"),
    ("EMP-002", "Sara Malik", "AR Follow-up", "Billing Executive", "Day", "EMP-005", True, "2023-11-03"),
    ("EMP-003", "Bilal Raza", "AR Follow-up", "Billing Executive", "Night", "EMP-005", True, "2025-04-21"),
    ("EMP-004", "Hina Shah", "Coding", "Medical Coder", "Day", "EMP-005", True, "2022-09-01"),
    ("EMP-005", "Sajid Mehmood", "Management", "AR Manager", "Day", None, True, "2021-06-15"),
]

DENIAL_CATEGORIES = [
    ("Authorization", "CO-197", "Authorization missing or invalid"),
    ("Eligibility", "CO-27", "Patient not eligible on date of service"),
    ("COB", "CO-22", "Coordination of benefits order mismatch"),
    ("Coding", "CO-97", "Procedure inconsistent with diagnosis/modifier"),
    ("Timely Filing", "CO-29", "Claim submitted after payer filing window"),
    ("Documentation", "CO-50", "Medical necessity documentation required"),
]

CPT_CODES = ["99213", "99214", "93000", "71046", "80053", "97110", "36415", "99203"]
ICD_CODES = ["I10", "E11.9", "M54.5", "J06.9", "R07.9", "Z00.00", "K21.9"]


def generate_seed_data(seed: int = 42) -> dict[str, list[dict]]:
    rng = random.Random(seed)
    claims: list[dict] = []
    denials: list[dict] = []
    followups: list[dict] = []

    def add_claim(claim_id: str, client_id: str, payer_id: str, employee_id: str, days: int, billed: float, status: str, patient_balance: float = 0, blocker_owner: str | None = None) -> dict:
        paid = 0 if status in {"Denied", "Pending", "Active", "System Hold"} else round(billed * rng.uniform(0.35, 0.85), 2)
        if status == "Paid":
            paid = billed
        submit = AS_OF_DATE - timedelta(days=days)
        service = submit - timedelta(days=rng.randint(1, 18))
        claim = {
            "claim_id": claim_id,
            "client_id": client_id,
            "payer_id": payer_id,
            "patient_id": f"PAT-{claim_id[-5:]}",
            "service_date": service.isoformat(),
            "submit_date": submit.isoformat(),
            "billed_amount": round(billed, 2),
            "allowed_amount": round(billed * rng.uniform(0.45, 0.82), 2),
            "paid_amount": round(paid, 2),
            "patient_balance": round(patient_balance, 2),
            "claim_status": status,
            "days_in_ar": days,
            "aging_bucket": aging_bucket(days),
            "cpt_codes": ",".join(rng.sample(CPT_CODES, rng.randint(1, 2))),
            "icd10_codes": ",".join(rng.sample(ICD_CODES, rng.randint(1, 2))),
            "claim_type": rng.choice(["Professional", "Institutional"]),
            "blocker_owner": blocker_owner,
            "assigned_to": employee_id,
        }
        claims.append(claim)
        return claim

    demo = add_claim("CLM-10021", "CLI-001", "PAY-002", "EMP-001", 96, 850.00, "Denied")
    denials.append({
        "denial_id": "DEN-10021",
        "claim_id": demo["claim_id"],
        "denial_date": (AS_OF_DATE - timedelta(days=84)).isoformat(),
        "denial_category": "Authorization",
        "denial_reason": "Authorization missing for service",
        "denial_reason_code": "CO-197",
        "denied_amount": 640.00,
        "appeal_deadline": (AS_OF_DATE + timedelta(days=6)).isoformat(),
        "appeal_status": "Open",
        "open_flag": True,
        "is_repeat_denial": True,
        "preventable_flag": True,
        "proof_on_file": True,
    })
    followups.append({
        "followup_id": "FUP-10021-1",
        "claim_id": demo["claim_id"],
        "employee_id": "EMP-001",
        "followup_date": (AS_OF_DATE - timedelta(days=11)).isoformat(),
        "action_code": "CALL_PAYER",
        "action_description": "Called payer, authorization denial confirmed.",
        "status_code": "IN_PROGRESS",
        "amount_recovered": 0,
        "next_action_date": None,
        "notes": "Appeal packet needed before deadline.",
    })

    for i in range(1, 321):
        claim_id = f"CLM-{10021 + i:05d}"
        client = rng.choice(CLIENTS)[0]
        payer = rng.choice(PAYERS)
        employee = rng.choice(EMPLOYEES[:3])[0]
        days = rng.choice([rng.randint(4, 28), rng.randint(31, 60), rng.randint(61, 90), rng.randint(91, 160)])
        status = rng.choices(
            ["Pending", "Active", "Denied", "Partial", "Paid", "System Hold"],
            weights=[18, 24, 26, 12, 12, 8],
        )[0]
        patient_balance = rng.uniform(80, 900) if status == "Partial" else 0
        blocker_owner = "Client" if rng.random() < 0.08 else None
        billed = rng.lognormvariate(7.15, 0.55)
        claim = add_claim(claim_id, client, payer[0], employee, days, billed, status, patient_balance, blocker_owner)

        if status == "Denied":
            category, code, reason = rng.choice(DENIAL_CATEGORIES)
            denial_date = AS_OF_DATE - timedelta(days=rng.randint(3, min(days, 100)))
            appeal_window = int(payer[4])
            deadline = denial_date + timedelta(days=appeal_window)
            repeat = rng.random() < 0.22
            denials.append({
                "denial_id": f"DEN-{claim_id[-5:]}",
                "claim_id": claim_id,
                "denial_date": denial_date.isoformat(),
                "denial_category": category,
                "denial_reason": reason,
                "denial_reason_code": code,
                "denied_amount": round(claim["billed_amount"] * rng.uniform(0.5, 0.95), 2),
                "appeal_deadline": deadline.isoformat(),
                "appeal_status": "Open" if deadline >= AS_OF_DATE else "Expired",
                "open_flag": True,
                "is_repeat_denial": repeat,
                "preventable_flag": category in {"Authorization", "Eligibility", "Timely Filing"},
                "proof_on_file": rng.random() < 0.45,
            })

        touch_count = rng.choices([0, 1, 2, 3, 4], weights=[18, 32, 28, 15, 7])[0]
        for t in range(touch_count):
            f_date = AS_OF_DATE - timedelta(days=rng.randint(1, min(days, 45)))
            waiting_client = blocker_owner == "Client" and t == touch_count - 1
            resolved = status == "Paid" and t == touch_count - 1
            followups.append({
                "followup_id": f"FUP-{claim_id[-5:]}-{t+1}",
                "claim_id": claim_id,
                "employee_id": employee,
                "followup_date": f_date.isoformat(),
                "action_code": rng.choice(["CALL_PAYER", "CHECK_STATUS", "RESUBMIT", "APPEAL_FILED"]),
                "action_description": "Synthetic follow-up touch from seeded AR workflow.",
                "status_code": "WAITING_CLIENT" if waiting_client else ("RESOLVED" if resolved else rng.choice(["IN_PROGRESS", "WAITING", "ESCALATED"])),
                "amount_recovered": round(rng.uniform(50, 1200), 2) if resolved else 0,
                "next_action_date": (AS_OF_DATE + timedelta(days=rng.randint(2, 12))).isoformat() if rng.random() < 0.22 or waiting_client else None,
                "notes": "Seeded operational note; no PHI.",
            })

    return {
        "clients": [dict(zip(["client_id", "client_name", "specialty", "sla_target_days"], row)) for row in CLIENTS],
        "payers": [dict(zip(["payer_id", "payer_name", "payer_type", "avg_response_days", "appeal_window_days", "risk_level", "portal_url"], row)) for row in PAYERS],
        "employees": [dict(zip(["employee_id", "employee_name", "team", "role", "shift", "supervisor_id", "active_flag", "hire_date"], row)) for row in EMPLOYEES],
        "claims": claims,
        "denials": denials,
        "followups": followups,
    }
