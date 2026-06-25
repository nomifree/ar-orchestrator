import { useEffect, useMemo, useState } from "react";
import {
  AlertTriangle,
  BarChart3,
  BriefcaseBusiness,
  Download,
  FileSpreadsheet,
  Filter,
  Gauge,
  RefreshCcw,
  Settings,
  SlidersHorizontal,
  Users,
} from "lucide-react";
import {
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  Pie,
  PieChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

const API = import.meta.env.VITE_API_URL || "http://127.0.0.1:8000";
const priorityColors = {
  Critical: "#DC2626",
  High: "#EA580C",
  Medium: "#D97706",
  Low: "#16A34A",
};
const pages = [
  ["dashboard", "Dashboard", BarChart3],
  ["queue", "Queue", BriefcaseBusiness],
  ["reps", "Reps", Users],
  ["clients", "Clients", FileSpreadsheet],
  ["settings", "Settings", Settings],
];

function money(value) {
  return new Intl.NumberFormat("en-US", { style: "currency", currency: "USD", maximumFractionDigits: 0 }).format(value || 0);
}

async function api(path, options) {
  const response = await fetch(`${API}${path}`, options);
  if (!response.ok) throw new Error(await response.text());
  return response.json();
}

function useLoad(loader, deps = []) {
  const [state, setState] = useState({ loading: true, error: "", data: null });
  useEffect(() => {
    let live = true;
    setState((s) => ({ ...s, loading: true, error: "" }));
    loader()
      .then((data) => live && setState({ loading: false, error: "", data }))
      .catch((error) => live && setState({ loading: false, error: error.message, data: null }));
    return () => {
      live = false;
    };
  }, deps);
  return state;
}

function Badge({ value }) {
  return (
    <span className="badge" style={{ "--badge": priorityColors[value] || "#64748B" }}>
      {value}
    </span>
  );
}

function Shell({ page, setPage, title, refresh, children }) {
  return (
    <div className="shell">
      <aside className="sidebar">
        <div className="brand">
          <Gauge size={24} />
          <div>
            <strong>AR Orchestrator</strong>
            <span>Interview prototype</span>
          </div>
        </div>
        <nav>
          {pages.map(([id, label, Icon]) => (
            <button key={id} className={page === id ? "active" : ""} onClick={() => setPage(id)}>
              <Icon size={18} />
              {label}
            </button>
          ))}
        </nav>
      </aside>
      <main>
        <header className="topbar">
          <div>
            <h1>{title}</h1>
            <p>Seeded synthetic data. Fixed rules date: 2026-06-25.</p>
          </div>
          <button className="primary" onClick={refresh}>
            <RefreshCcw size={16} />
            Refresh Queue
          </button>
        </header>
        {children}
      </main>
    </div>
  );
}

function Dashboard({ goQueue, reloadKey }) {
  const summary = useLoad(() => api("/api/v1/dashboard/summary"), [reloadKey]);
  const aging = useLoad(() => api("/api/v1/dashboard/aging"), [reloadKey]);
  const denial = useLoad(() => api("/api/v1/dashboard/denial-mix"), [reloadKey]);
  const workability = useLoad(() => api("/api/v1/dashboard/workability"), [reloadKey]);
  if (summary.loading) return <Status text="Loading dashboard from backend..." />;
  if (summary.error) return <Status error text="Could not load dashboard data. Try refreshing." />;
  const cards = [
    ["Actionable Claims Today", summary.data.actionable_claims, "queue"],
    ["Critical Priority", summary.data.critical_priority, "critical"],
    ["90+ Days AR", summary.data.ar_90_plus, "90+"],
    ["Untouched 7+ Days", summary.data.untouched_7_days, "stale"],
  ];
  return (
    <section className="content">
      <div className="kpi-grid">
        {cards.map(([label, value, target]) => (
          <button className="kpi" key={label} onClick={() => goQueue(target)}>
            <span>{label}</span>
            <strong>{value}</strong>
          </button>
        ))}
        <div className="kpi">
          <span>Total AR Outstanding</span>
          <strong>{money(summary.data.total_outstanding)}</strong>
        </div>
      </div>
      <div className="grid-2">
        <Panel title="AR Aging">
          <ChartState state={aging}>
            <ResponsiveContainer width="100%" height={260}>
              <BarChart data={aging.data}>
                <CartesianGrid strokeDasharray="3 3" vertical={false} />
                <XAxis dataKey="bucket" />
                <YAxis />
                <Tooltip formatter={(v, n) => (n === "outstanding_amount" ? money(v) : v)} />
                <Bar dataKey="claim_count" fill="#1B6CA8" radius={[4, 4, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </ChartState>
        </Panel>
        <Panel title="Open Denial Mix">
          <ChartState state={denial}>
            <ResponsiveContainer width="100%" height={260}>
              <PieChart>
                <Pie data={denial.data} dataKey="claim_count" nameKey="category" innerRadius={58} outerRadius={96}>
                  {denial.data?.map((_, index) => (
                    <Cell key={index} fill={["#DC2626", "#EA580C", "#D97706", "#1B6CA8", "#16A34A", "#64748B"][index % 6]} />
                  ))}
                </Pie>
                <Tooltip />
              </PieChart>
            </ResponsiveContainer>
          </ChartState>
        </Panel>
      </div>
      <Panel title="Workability Distribution">
        <ChartState state={workability}>
          <table>
            <thead>
              <tr>
                <th>Status</th>
                <th>Claims</th>
                <th>Outstanding</th>
              </tr>
            </thead>
            <tbody>
              {workability.data?.map((row) => (
                <tr key={row.status} onClick={() => goQueue(row.status)} className="clickable">
                  <td>{row.status}</td>
                  <td>{row.claim_count}</td>
                  <td>{money(row.outstanding_amount)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </ChartState>
      </Panel>
    </section>
  );
}

function Queue({ initialFilters, selectClaim, reloadKey }) {
  const [filters, setFilters] = useState(initialFilters || {});
  const [sort, setSort] = useState("priority_score");
  useEffect(() => setFilters(initialFilters || {}), [initialFilters]);
  const meta = useLoad(() => api("/api/v1/meta/filters"), [reloadKey]);
  const query = new URLSearchParams({ page_size: "50", sort, ...Object.fromEntries(Object.entries(filters).filter(([, v]) => v)) });
  const queue = useLoad(() => api(`/api/v1/queue?${query}`), [JSON.stringify(filters), sort, reloadKey]);
  return (
    <section className="content">
      <Panel title="Daily Work Queue" action={<ExportButtons />}>
        <div className="filters">
          <Filter size={16} />
          <select value={filters.priority || ""} onChange={(e) => setFilters({ ...filters, priority: e.target.value })}>
            <option value="">All priorities</option>
            {meta.data?.priorities.map((p) => <option key={p}>{p}</option>)}
          </select>
          <select value={filters.workability_status || ""} onChange={(e) => setFilters({ ...filters, workability_status: e.target.value })}>
            <option value="">All workability</option>
            {meta.data?.workability.map((p) => <option key={p.value}>{p.value}</option>)}
          </select>
          <select value={filters.client_id || ""} onChange={(e) => setFilters({ ...filters, client_id: e.target.value })}>
            <option value="">All clients</option>
            {meta.data?.clients.map((c) => <option key={c.client_id} value={c.client_id}>{c.client_name}</option>)}
          </select>
          <select value={filters.payer_id || ""} onChange={(e) => setFilters({ ...filters, payer_id: e.target.value })}>
            <option value="">All payers</option>
            {meta.data?.payers.map((p) => <option key={p.payer_id} value={p.payer_id}>{p.payer_name}</option>)}
          </select>
          <button onClick={() => setFilters({})}>Reset</button>
        </div>
        <div className="sortbar">
          <span>{queue.data?.total || 0} queue rows</span>
          <select value={sort} onChange={(e) => setSort(e.target.value)}>
            <option value="priority_score">Sort by score</option>
            <option value="days_in_ar">Sort by days AR</option>
            <option value="outstanding_amount">Sort by outstanding</option>
            <option value="claim_id">Sort by claim ID</option>
          </select>
        </div>
        <TableState state={queue}>
          <table className="queue-table">
            <thead>
              <tr>
                <th>Priority</th>
                <th>Score</th>
                <th>Claim</th>
                <th>Client</th>
                <th>Payer</th>
                <th>Outstanding</th>
                <th>Days AR</th>
                <th>Assigned</th>
                <th>Next Action</th>
              </tr>
            </thead>
            <tbody>
              {queue.data?.rows.map((row) => (
                <tr key={row.claim_id} onClick={() => selectClaim(row.claim_id)} className="clickable">
                  <td><Badge value={row.priority_level} /></td>
                  <td><ScoreBar score={row.priority_score} /></td>
                  <td><strong>{row.claim_id}</strong><span>{row.workability_status}</span></td>
                  <td>{row.client_name}</td>
                  <td>{row.payer_name}</td>
                  <td>{money(row.outstanding_amount)}</td>
                  <td>{row.days_in_ar}</td>
                  <td>{row.assigned_name || "Unassigned"}</td>
                  <td className="action">{row.recommended_action}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </TableState>
      </Panel>
    </section>
  );
}

function ClaimDrilldown({ claimId, back, reload }) {
  const detail = useLoad(() => api(`/api/v1/claims/${claimId}`), [claimId]);
  const [openLog, setOpenLog] = useState(false);
  if (detail.loading) return <Status text="Loading claim evidence..." />;
  if (detail.error) return <Status error text="Could not load claim detail." />;
  const { claim, denials, timeline, payer } = detail.data;
  const breakdown = Object.entries(claim.score_breakdown);
  const totalBreakdown = breakdown.reduce((sum, [, v]) => sum + v, 0);
  return (
    <section className="content">
      <button className="back" onClick={back}>Back to Queue</button>
      <div className="claim-header">
        <div>
          <h2>{claim.claim_id}</h2>
          <p>{claim.client_name} / {claim.payer_name}</p>
        </div>
        <Badge value={claim.priority_level} />
        <strong>{money(claim.outstanding_amount)}</strong>
      </div>
      <div className="grid-2">
        <Panel title="Priority Explainability">
          <div className="score-circle" style={{ "--score": claim.priority_score }}>
            <strong>{claim.priority_score}</strong>
            <span>{claim.priority_level}</span>
          </div>
          <div className="breakdown">
            {breakdown.map(([key, value]) => (
              <div key={key}>
                <span>{key.replaceAll("_", " ")}</span>
                <ScoreBar score={value} max={25} />
              </div>
            ))}
          </div>
          <p className="muted">Breakdown sum: {totalBreakdown}. Displayed score is clamped 0-100.</p>
        </Panel>
        <Panel title="Recommended Action" action={<button className="primary" onClick={() => setOpenLog(true)}>Log Follow-Up</button>}>
          <div className="action-box">
            <strong>{claim.recommended_action_code}</strong>
            <p>{claim.recommended_action}</p>
          </div>
          <dl className="facts">
            <dt>Status</dt><dd>{claim.workability_status}</dd>
            <dt>Days AR</dt><dd>{claim.days_in_ar}</dd>
            <dt>Payer Risk</dt><dd>{payer.risk_level}</dd>
            <dt>Appeal Window</dt><dd>{payer.appeal_window_days} days</dd>
          </dl>
        </Panel>
      </div>
      <div className="grid-2">
        <Panel title="Denial History">
          <MiniTable rows={denials} columns={["denial_date", "denial_category", "denied_amount", "appeal_deadline", "appeal_status"]} />
        </Panel>
        <Panel title="Follow-Up Timeline">
          <div className="timeline">
            {timeline.map((item) => (
              <div key={item.followup_id}>
                <strong>{item.followup_date} / {item.action_code}</strong>
                <p>{item.action_description || item.notes}</p>
                <span>{item.employee_name} / {item.status_code}</span>
              </div>
            ))}
          </div>
        </Panel>
      </div>
      {openLog && <FollowupModal claimId={claimId} close={() => setOpenLog(false)} afterSave={reload} />}
    </section>
  );
}

function FollowupModal({ claimId, close, afterSave }) {
  const [notes, setNotes] = useState("");
  const [saving, setSaving] = useState(false);
  async function save() {
    setSaving(true);
    await api(`/api/v1/claims/${claimId}/followups`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ action_code: "CALL_PAYER", action_description: "Logged from demo UI", status_code: "IN_PROGRESS", notes }),
    });
    setSaving(false);
    close();
    afterSave();
  }
  return (
    <div className="modal">
      <div>
        <h3>Log Follow-Up</h3>
        <textarea value={notes} onChange={(e) => setNotes(e.target.value)} placeholder="Notes" />
        <footer>
          <button onClick={close}>Cancel</button>
          <button className="primary" onClick={save} disabled={saving}>{saving ? "Saving..." : "Save"}</button>
        </footer>
      </div>
    </div>
  );
}

function Reps({ reloadKey }) {
  const reps = useLoad(() => api("/api/v1/reps"), [reloadKey]);
  const totalRecovered = reps.data?.reduce((sum, r) => sum + Number(r.recovered_amount || 0), 0) || 0;
  return (
    <section className="content">
      <div className="kpi-grid">
        <div className="kpi"><span>Active Reps</span><strong>{reps.data?.length || 0}</strong></div>
        <div className="kpi"><span>Total Recoveries</span><strong>{money(totalRecovered)}</strong></div>
        <div className="kpi"><span>Top Rep</span><strong>{reps.data?.[0]?.employee_name || "-"}</strong></div>
      </div>
      <Panel title="Rep Effectiveness">
        <TableState state={reps}>
          <MiniTable rows={reps.data || []} columns={["employee_name", "role", "queue_size", "recovered_amount", "touch_efficiency", "denial_win_rate", "stale_claims", "performance_band"]} />
        </TableState>
      </Panel>
    </section>
  );
}

function Clients({ reloadKey }) {
  const clients = useLoad(() => api("/api/v1/clients"), [reloadKey]);
  return (
    <section className="content">
      <Panel title="Client Portfolio">
        <TableState state={clients}>
          <table>
            <thead>
              <tr><th>Client</th><th>Specialty</th><th>Outstanding</th><th>Open Denials</th><th>90+ AR</th><th>SLA</th><th>Export</th></tr>
            </thead>
            <tbody>
              {clients.data?.map((c) => (
                <tr key={c.client_id}>
                  <td><strong>{c.client_name}</strong></td>
                  <td>{c.specialty}</td>
                  <td>{money(c.outstanding_amount)}</td>
                  <td>{c.open_denials}</td>
                  <td>{c.ar_90_plus}</td>
                  <td><span className={`sla ${c.sla_status.replaceAll(" ", "-").toLowerCase()}`}>{c.sla_status}</span></td>
                  <td><a className="icon-link" href={`${API}/api/v1/exports/client/${c.client_id}.xlsx`}><Download size={16} /> XLSX</a></td>
                </tr>
              ))}
            </tbody>
          </table>
        </TableState>
      </Panel>
    </section>
  );
}

function SettingsPage({ reload }) {
  const loaded = useLoad(() => api("/api/v1/settings/scoring"), []);
  const [config, setConfig] = useState(null);
  useEffect(() => loaded.data && setConfig(loaded.data), [loaded.data]);
  const total = useMemo(() => (config ? Object.values(config).reduce((a, b) => a + Number(b), 0) : 0), [config]);
  async function save() {
    await api("/api/v1/settings/scoring", { method: "PUT", headers: { "Content-Type": "application/json" }, body: JSON.stringify(config) });
    reload();
  }
  if (loaded.loading || !config) return <Status text="Loading scoring settings..." />;
  return (
    <section className="content">
      <Panel title="Scoring Weights" action={<SlidersHorizontal size={18} />}>
        <div className="settings-grid">
          {Object.entries(config).map(([key, value]) => (
            <label key={key}>
              <span>{key.replace("weight_", "").replaceAll("_", " ")}</span>
              <input type="range" min="0" max="40" value={value} onChange={(e) => setConfig({ ...config, [key]: Number(e.target.value) })} />
              <strong>{value}</strong>
            </label>
          ))}
        </div>
        <div className="settings-actions">
          <span className={total === 100 ? "ok" : "bad"}>Total weight: {total}</span>
          <button onClick={() => setConfig({ weight_days_ar: 25, weight_balance: 20, weight_denial_deadline: 20, weight_stale_followup: 15, weight_payer_risk: 10, weight_repeat_denial: 10 })}>Reset Defaults</button>
          <button className="primary" disabled={total !== 100} onClick={save}>Save & Refresh Queue</button>
        </div>
      </Panel>
    </section>
  );
}

function ExportButtons() {
  return (
    <div className="actions">
      <a className="icon-link" href={`${API}/api/v1/exports/queue.csv`}><Download size={16} /> CSV</a>
      <a className="icon-link" href={`${API}/api/v1/exports/queue.xlsx`}><Download size={16} /> Excel</a>
    </div>
  );
}

function Panel({ title, action, children }) {
  return (
    <section className="panel">
      <header><h2>{title}</h2>{action}</header>
      {children}
    </section>
  );
}

function Status({ text, error }) {
  return <div className={`status ${error ? "error" : ""}`}>{error && <AlertTriangle size={18} />}{text}</div>;
}
function ChartState({ state, children }) {
  if (state.loading) return <Status text="Loading..." />;
  if (state.error) return <Status error text="Could not load chart data." />;
  if (!state.data?.length) return <Status text="No actionable claims today. Queue is clear." />;
  return children;
}
function TableState({ state, children }) {
  if (state.loading) return <Status text="Loading table..." />;
  if (state.error) return <Status error text="Could not load table data." />;
  return children;
}
function ScoreBar({ score, max = 100 }) {
  return <span className="scorebar"><i style={{ width: `${Math.min(100, (score / max) * 100)}%` }} />{score}</span>;
}
function MiniTable({ rows, columns }) {
  return (
    <table>
      <thead><tr>{columns.map((c) => <th key={c}>{c.replaceAll("_", " ")}</th>)}</tr></thead>
      <tbody>
        {rows.map((row, i) => (
          <tr key={row.claim_id || row.employee_id || row.denial_id || i}>
            {columns.map((c) => <td key={c}>{c.includes("amount") || c.includes("recovered") ? money(row[c]) : String(row[c] ?? "-")}</td>)}
          </tr>
        ))}
      </tbody>
    </table>
  );
}

export default function App() {
  const [page, setPage] = useState("dashboard");
  const [reloadKey, setReloadKey] = useState(0);
  const [queueFilters, setQueueFilters] = useState({});
  const [claimId, setClaimId] = useState(null);
  async function refresh() {
    await api("/api/v1/queue/refresh", { method: "POST" });
    setReloadKey((x) => x + 1);
  }
  function goQueue(target) {
    const next = {};
    if (target === "critical") next.priority = "Critical";
    if (target === "90+") next.aging_bucket = "90+";
    if (target && !["queue", "critical", "90+", "stale"].includes(target)) next.workability_status = target;
    setQueueFilters(next);
    setClaimId(null);
    setPage("queue");
  }
  const title = claimId ? "Claim Drilldown" : pages.find(([id]) => id === page)?.[1] || "Dashboard";
  return (
    <Shell page={page} setPage={(id) => { setPage(id); setClaimId(null); }} title={title} refresh={refresh}>
      {claimId ? (
        <ClaimDrilldown claimId={claimId} back={() => setClaimId(null)} reload={refresh} />
      ) : page === "dashboard" ? (
        <Dashboard goQueue={goQueue} reloadKey={reloadKey} />
      ) : page === "queue" ? (
        <Queue initialFilters={queueFilters} selectClaim={setClaimId} reloadKey={reloadKey} />
      ) : page === "reps" ? (
        <Reps reloadKey={reloadKey} />
      ) : page === "clients" ? (
        <Clients reloadKey={reloadKey} />
      ) : (
        <SettingsPage reload={refresh} />
      )}
    </Shell>
  );
}
