# Business Rules

The prototype uses deterministic rules only. There is no LLM decisioning in the queue.

## Fixed Date

All rules use `AS_OF_DATE=2026-06-25` by default. This keeps tests, scores, exports, and demo claims reproducible.

## Workability Precedence

1. `Paid` or `Voided` claims are `Closed` and excluded from the queue.
2. Open denial with passed appeal deadline becomes `Escalation Required`.
3. Open denial inside appeal window becomes `Denial Workable`.
4. Partial pay with patient balance becomes `Patient Balance`.
5. Future next-action date becomes `Waiting Client` or `Waiting Payer`.
6. 90+ AR with no progress or repeated unresolved touches becomes `Escalation Required`.
7. Submitted/system-held or pending inside payer response window becomes `System Hold`.
8. Overdue payer response or stale/no follow-up becomes `Active Workable`.
9. Remaining open claims become waiting states.

## Priority Score

Each non-closed queue row gets an explainable score from six factors:

- Days in AR: max 25
- Outstanding balance: max 20
- Open denial/deadline proximity: max 20
- Days since last follow-up: max 15
- Payer risk: max 10
- Repeat denial: max 10

Score is clamped to `0-100`.

Balance points use practical AR tiers:

- `$0-250`: 4 base points
- `$251-500`: 8 base points
- `$501-1,000`: 15 base points
- `$1,001+`: 20 base points

Priority levels:

- `80-100`: Critical
- `60-79`: High
- `40-59`: Medium
- `0-39`: Low

## Next-Best-Action

Every queue row receives exactly one action code and one action text. Authorization deadlines check expired first, then seven-day urgent windows. Timely filing denials explicitly route to proof review or write-off review.

## Upload Validation

The upload screen accepts claims CSV files. It validates required columns, existing client/payer/employee IDs, dates, allowed statuses, allowed claim types, non-negative amounts, paid amount not exceeding billed amount, and anonymized patient IDs. Rows are loaded only when validation has zero row errors and the user chooses to apply the upload.
