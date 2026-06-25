from datetime import date
from pathlib import Path
import os


ROOT_DIR = Path(__file__).resolve().parents[2]
DATA_DIR = ROOT_DIR / "backend" / "data"
DATA_DIR.mkdir(parents=True, exist_ok=True)

DATABASE_PATH = Path(os.getenv("DATABASE_PATH", DATA_DIR / "ar_orchestrator.duckdb"))
AS_OF_DATE = date.fromisoformat(os.getenv("AS_OF_DATE", "2026-06-25"))

DEFAULT_SCORING = {
    "weight_days_ar": 25,
    "weight_balance": 20,
    "weight_denial_deadline": 20,
    "weight_stale_followup": 15,
    "weight_payer_risk": 10,
    "weight_repeat_denial": 10,
}
