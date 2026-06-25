# Demo Script

## Opening

This is not a chatbot. It is a deterministic AR work queue and denial resolution layer for outsourced RCM operations. It ingests synthetic PM/EHR-style data, classifies workability, scores risk, recommends one next action, and exports manager/client packs.

## Flow

1. Open Dashboard.
   - Show actionable claims, critical priority, 90+ AR, untouched 7+ days.
   - Point out the numbers are fetched from `/api/v1/dashboard/summary`.

2. Click Critical Priority.
   - Queue opens filtered to `Critical`.
   - Explain that priority is based on dollars at risk, aging, deadline, stale follow-up, payer risk, and repeat denial.

3. Open `CLM-10021`.
   - Show Authorization denial, deadline in 6 days, score breakdown, and action `AUTH_URGENT_APPEAL`.
   - Explain every point in the score.

4. Log a follow-up.
   - Save a follow-up note.
   - Queue refreshes, proving the UI is dynamic.

5. Open Upload.
   - Download the template.
   - Upload it with validation first.
   - Optionally apply it to prove the queue can ingest a CSV.

6. Open Reps.
   - Emphasize recovered value and touch efficiency, not raw touches.

7. Open Clients.
   - Export a client Excel pack.
   - Explain the sheets: AR Summary, Open Denials, Action Backlog, Top Claims, Period Trend.

8. Open Settings.
   - Change scoring weights while keeping total at 100.
   - Save and refresh queue to show configurable rules.

## Closing

The demo uses synthetic data only. Production would add private hosting, role-based access, audit logging, and PHI controls. The valuable part is already here: explainable prioritization and manager-ready workflow visibility.
