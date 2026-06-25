# AR Work Queue & Denial Resolution Orchestrator

Interview-grade prototype for an RCM workflow intelligence layer. It uses synthetic data, deterministic business rules, a FastAPI backend, DuckDB analytics storage, and a React/Vite frontend.

## What It Proves

- Claims are scored dynamically from backend data, not hardcoded UI numbers.
- Every priority score has a six-factor breakdown.
- Every claim gets one deterministic next-best-action.
- Managers can filter the live queue, drill into evidence, change scoring weights, and export Excel packs.

## Local Setup

```powershell
.venv\Scripts\python.exe -m uvicorn backend.app.main:app --reload --host 127.0.0.1 --port 8000
```

In another terminal:

```powershell
C:\Users\numl-\.cache\codex-runtimes\codex-primary-runtime\dependencies\bin\pnpm.cmd dev
```

Frontend: `http://127.0.0.1:5173`  
Backend API docs: `http://127.0.0.1:8000/docs`

## Tests

```powershell
.venv\Scripts\python.exe -m pytest
```

## Key Files

- `backend/app/rules.py`: workability, scoring, and next-best-action logic.
- `backend/app/seed.py`: deterministic synthetic data generator.
- `backend/app/db.py`: DuckDB startup, seed loading, queue rebuild.
- `backend/app/main.py`: FastAPI routes and exports.
- `src/App.jsx`: dynamic React app.
- `docs/tickets.md`: small-ticket execution map.
- `docs/business_rules.md`: plain-English rule contract.
- `docs/demo_script.md`: interview walkthrough.

## Anti-Static Checks

- Kill the backend: the frontend shows API errors instead of fake KPI data.
- Change scoring weights: queue scores and ordering refresh from the backend.
- Open `CLM-10021`: score breakdown and action come from the rules engine.
- Export queue/client packs: workbooks are generated from current backend data.
