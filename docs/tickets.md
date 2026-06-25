# AR Orchestrator Ticket Backlog

## Team Lanes

- Architect: schema, API boundaries, startup/deployment shape.
- Business logic: deterministic RCM rules, scoring, next-best-action, tests.
- Design: operational dashboard, queue, drilldown, rep/client/settings flows.
- Operator: exports, seed data, runbooks, demo sequence.
- Auditor: anti-static checks, edge-case tests, explainability, data integrity.

## Executed MVP Tickets

| ID | Ticket | Acceptance Evidence |
| --- | --- | --- |
| T01 | Scaffold repo | `backend/`, `src/`, Vite config, README, requirements. |
| T02 | Schema + seed generator | DuckDB tables and deterministic seed data with `CLM-10021` demo case. |
| T03 | Backend service layer | Startup initializes DB and rebuilds queue from seed data. |
| T04 | Rules engine | Pure functions for workability, scoring, priority level, and next-best-action. |
| T05 | Queue builder | `POST /api/v1/queue/refresh` rebuilds idempotent `work_queue`. |
| T06 | Dashboard + queue API | Summary, aging, denial mix, workability, queue filters. |
| T07 | Claim drilldown API | Claim facts, denials, timeline, payer, score breakdown. |
| T08 | Export endpoints | CSV and Excel queue exports, client pack workbook. |
| T09 | Dashboard UI | Live KPI cards and charts from API. |
| T10 | Work queue UI | Filters, sorting, row click into drilldown. |
| T11 | Claim drilldown UI | Score gauge, breakdown bars, recommended action, timeline. |
| T12 | Upload UI + validation | Claims CSV template, validation report, optional load, queue refresh. |
| T13 | Demo docs/tests | README, demo script, business rules, pytest guardrails. |

## Deferred Tickets

- XLSX upload and advanced field mapping.
- Persistent assignment endpoint.
- Production auth, RBAC, audit logs, private hosting, and PHI controls.
- Vercel/Render deployment wiring after local demo is approved.
