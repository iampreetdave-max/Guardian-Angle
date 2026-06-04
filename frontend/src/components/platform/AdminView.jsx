import { useEffect, useRef, useState } from "react";
import { Users, Plus, Loader2, Shield, ChevronDown, ChevronRight, Star, Mail, UserPlus, X, Check, Megaphone, Send, TriangleAlert, Lock, Unlock, Activity, Database, Download, ShieldAlert, Power, Cpu, HardDrive, MemoryStick, Server } from "lucide-react";
import * as API from "../../api";
import { setToken } from "../../api";

const STAFF_ROLES = ["officer", "lead", "admin"];

export default function AdminView() {
  const [users, setUsers] = useState([]);
  const [teams, setTeams] = useState([]);
  const [tab, setTab] = useState("users");
  const [creatingUser, setCreatingUser] = useState(false);
  const [creatingTeam, setCreatingTeam] = useState(false);

  const refresh = () => {
    API.listUsers().then(setUsers).catch(() => {});
    API.listTeams().then(setTeams).catch(() => {});
  };
  useEffect(() => { refresh(); }, []);

  const assignUserTeam = (uid, val) =>
    API.updateUser(uid, { team_id: val === "" ? null : Number(val) })
      .then(refresh)
      .catch(() => {});

  return (
    <div className="mx-auto max-w-5xl p-5">
      <div className="mb-4 flex items-center gap-3">
        <Shield size={20} className="text-accent" />
        <h2 className="text-lg font-bold text-white">Administration</h2>
        <div className="ml-auto flex items-center gap-1 rounded-lg bg-ink-900/60 p-1 text-xs">
          {["users", "teams", "broadcast", "security", "monitoring", "data"].map((t) => (
            <button key={t} onClick={() => setTab(t)} className={`rounded px-3 py-1 ${tab === t ? "bg-accent-600 text-white" : "text-slate-400"}`}>{t}</button>
          ))}
        </div>
      </div>

      {tab === "users" && (
        <>
          <button onClick={() => setCreatingUser(true)} className="mb-3 inline-flex items-center gap-1.5 rounded-lg bg-accent-600 px-3 py-1.5 text-xs font-semibold text-white hover:bg-accent-700"><Plus size={14} /> Add staff user</button>
          <div className="space-y-1.5">
            {users.map((u) => (
              <div key={u.id} className="flex items-center justify-between rounded-lg border border-ink-600 bg-ink-800/50 p-3 text-sm">
                <div>
                  <span className="font-semibold text-slate-100">{u.name}</span>
                  <span className="ml-2 text-xs text-slate-500">{u.email}</span>
                </div>
                <div className="flex items-center gap-2 text-xs">
                  {u.badge_no && <span className="text-slate-500">{u.badge_no}</span>}
                  {STAFF_ROLES.includes(u.role) && (
                    <UserTeamSelect user={u} teams={teams} onAssign={assignUserTeam} />
                  )}
                  <span className={`rounded px-2 py-0.5 ${u.role === "admin" ? "bg-signal-red/15 text-signal-red" : u.role === "lead" ? "bg-accent/15 text-accent" : u.role === "officer" ? "bg-signal-green/15 text-signal-green" : "bg-ink-700 text-slate-400"}`}>{u.role}</span>
                </div>
              </div>
            ))}
          </div>
        </>
      )}

      {tab === "teams" && (
        <>
          <button onClick={() => setCreatingTeam(true)} className="mb-3 inline-flex items-center gap-1.5 rounded-lg bg-accent-600 px-3 py-1.5 text-xs font-semibold text-white hover:bg-accent-700"><Plus size={14} /> Add team</button>
          <div className="space-y-1.5">
            {teams.map((t) => <TeamRow key={t.id} team={t} allUsers={users} onChanged={refresh} />)}
          </div>
        </>
      )}

      {tab === "broadcast" && <BroadcastPanel />}

      {tab === "security" && <SecurityPanel />}

      {tab === "monitoring" && <MonitoringPanel />}

      {tab === "data" && <DataPanel />}

      {creatingUser && <CreateUserModal teams={teams} onClose={() => setCreatingUser(false)} onDone={() => { setCreatingUser(false); refresh(); }} />}
      {creatingTeam && <CreateTeamModal onClose={() => setCreatingTeam(false)} onDone={() => { setCreatingTeam(false); refresh(); }} />}
    </div>
  );
}

// ---- city-wide broadcast (disaster / advisory) ----
const SEVERITIES = ["low", "medium", "high", "critical"];

function BroadcastPanel() {
  const [f, setF] = useState({ kind: "advisory", title: "", message: "", area: "", severity: "medium", link: "", expires_at: "" });
  const [areas, setAreas] = useState([]);
  const [history, setHistory] = useState([]);
  const [busy, setBusy] = useState(false);
  const [result, setResult] = useState(null);

  const refresh = () => API.listBroadcasts().then(setHistory).catch(() => {});
  useEffect(() => {
    refresh();
    API.getAreas().then((d) => setAreas(d.areas)).catch(() => {});
  }, []);

  const send = async () => {
    if (!f.title.trim() || !f.message.trim()) return;
    setBusy(true); setResult(null);
    try {
      const r = await API.sendBroadcast({
        ...f,
        area: f.area || null,
        link: f.link || null,
        expires_at: f.expires_at || null,
      });
      setResult(`Sent to ${r.recipients} users.`);
      setF({ kind: "advisory", title: "", message: "", area: "", severity: "medium", link: "", expires_at: "" });
      refresh();
    } catch (e) {
      setResult(e?.response?.data?.detail || "Failed to send");
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="grid gap-4 lg:grid-cols-2">
      <div className="rounded-xl border border-ink-600 bg-ink-800/70 p-4">
        <div className="mb-2 flex items-center gap-2 text-sm font-semibold text-slate-200">
          <Megaphone size={15} className="text-accent" /> Send a city-wide alert
        </div>
        <p className="mb-3 text-[11px] text-slate-500">
          Disaster alerts (floods, emergencies) and advisories reach every user
          instantly — notification + banner. Critical alerts stay pinned until
          deactivated.
        </p>
        <div className="mb-2 grid grid-cols-2 gap-2">
          <select value={f.kind} onChange={(e) => setF({ ...f, kind: e.target.value })} className={inp}>
            <option value="advisory">Advisory</option>
            <option value="disaster">Disaster alert</option>
          </select>
          <select value={f.severity} onChange={(e) => setF({ ...f, severity: e.target.value })} className={inp}>
            {SEVERITIES.map((s) => <option key={s} value={s}>{s}</option>)}
          </select>
        </div>
        <input placeholder="Title (e.g. Flood warning — Sabarmati riverfront)" value={f.title}
          onChange={(e) => setF({ ...f, title: e.target.value })} className={inp + " mb-2"} />
        <textarea placeholder="Message for citizens and staff" rows={3} value={f.message}
          onChange={(e) => setF({ ...f, message: e.target.value })} className={inp + " mb-2 resize-y"} />
        <div className="mb-2 grid grid-cols-2 gap-2">
          <select value={f.area} onChange={(e) => setF({ ...f, area: e.target.value })} className={inp}>
            <option value="">City-wide (all areas)</option>
            {areas.map((a) => <option key={a.name} value={a.name}>{a.name}</option>)}
          </select>
          <input type="datetime-local" title="Expires at (optional)" value={f.expires_at}
            onChange={(e) => setF({ ...f, expires_at: e.target.value })} className={inp} />
        </div>
        <input placeholder="More-info link (optional)" value={f.link}
          onChange={(e) => setF({ ...f, link: e.target.value })} className={inp + " mb-3"} />
        <button onClick={send} disabled={busy || !f.title.trim() || !f.message.trim()}
          className="inline-flex items-center gap-2 rounded-lg bg-accent-600 px-4 py-2 text-sm font-semibold text-white hover:bg-accent-700 disabled:opacity-50">
          {busy ? <Loader2 size={14} className="animate-spin" /> : <Send size={14} />} Broadcast
        </button>
        {result && <div className="mt-2 text-[11px] text-slate-400">{result}</div>}
      </div>

      <div className="rounded-xl border border-ink-600 bg-ink-800/70 p-4">
        <div className="mb-2 text-sm font-semibold text-slate-200">Recent broadcasts</div>
        {history.length === 0 ? (
          <p className="py-6 text-center text-xs text-slate-500">No broadcasts sent yet.</p>
        ) : (
          <div className="space-y-1.5">
            {history.map((b) => (
              <div key={b.id} className="rounded-lg bg-ink-900/40 p-2.5 text-xs">
                <div className="flex items-center gap-2">
                  {b.kind === "disaster" && <TriangleAlert size={12} className="text-signal-red" />}
                  <span className="font-semibold text-slate-200">{b.title}</span>
                  <span className={`rounded px-1.5 py-0.5 text-[10px] ${
                    b.severity === "critical" ? "bg-signal-red/15 text-signal-red"
                    : b.severity === "high" ? "bg-orange-500/15 text-orange-400"
                    : "bg-accent/15 text-accent"}`}>{b.severity}</span>
                  {!b.active ? (
                    <span className="ml-auto text-[10px] text-slate-600">inactive</span>
                  ) : (
                    <button onClick={() => API.deactivateBroadcast(b.id).then(refresh)}
                      className="ml-auto rounded px-1.5 py-0.5 text-[10px] text-slate-400 hover:bg-signal-red/20 hover:text-signal-red">
                      deactivate
                    </button>
                  )}
                </div>
                <div className="mt-0.5 text-slate-400">{b.message}</div>
                <div className="mt-0.5 text-[10px] text-slate-600">
                  {b.area || "city-wide"} · by {b.sender} · {b.created_at}
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}

// ---- security: lockdown, sign-out-all, security events ----
function SecurityPanel() {
  const [locked, setLocked] = useState(false);
  const [confirming, setConfirming] = useState(false); // inline confirm before enabling
  const [busy, setBusy] = useState(false);
  const [signingOut, setSigningOut] = useState(false);
  const [events, setEvents] = useState({ login_attempts: [], audit: [] });

  const refresh = () => {
    API.getSystemStatus().then((s) => setLocked(!!s.lockdown)).catch(() => {});
    API.getSecurityEvents().then((e) =>
      setEvents({ login_attempts: e.login_attempts || [], audit: e.audit || [] })
    ).catch(() => {});
  };
  useEffect(() => { refresh(); }, []);

  const apply = async (enabled) => {
    setBusy(true); setConfirming(false);
    try { const r = await API.setLockdown(enabled); setLocked(!!r.lockdown); }
    catch { /* leave state as-is */ } finally { setBusy(false); }
  };

  const toggle = () => {
    if (locked) { apply(false); return; }   // disabling is immediate
    setConfirming(true);                     // enabling needs an inline confirm
  };

  const signOutAll = async () => {
    setSigningOut(true);
    try {
      await API.logoutAll();
      setToken(null);
      window.location.reload();
    } catch { setSigningOut(false); }
  };

  return (
    <div className="grid gap-4 lg:grid-cols-2">
      {/* lockdown */}
      <div className={`rounded-xl border p-4 ${locked ? "border-signal-red/60 bg-signal-red/10" : "border-ink-600 bg-ink-800/70"}`}>
        <div className="mb-2 flex items-center gap-2 text-sm font-semibold text-slate-200">
          <ShieldAlert size={15} className={locked ? "text-signal-red" : "text-accent"} /> Emergency lockdown
        </div>
        <p className="mb-3 text-[11px] text-slate-500">
          When active, only administrators can operate the platform — every other
          request is rejected (HTTP 423). Use during a live incident or breach.
        </p>
        <div className="mb-3 text-xs">
          Current state:{" "}
          <span className={locked ? "font-semibold text-signal-red" : "font-semibold text-signal-green"}>
            {locked ? "LOCKED DOWN" : "normal operation"}
          </span>
        </div>
        {confirming ? (
          <div className="flex items-center gap-2">
            <span className="text-[11px] text-slate-300">Lock down the entire platform?</span>
            <button onClick={() => apply(true)} disabled={busy}
              title="Confirm lockdown"
              className="inline-flex items-center gap-1 rounded-lg bg-signal-red px-3 py-1.5 text-xs font-semibold text-white hover:bg-red-600 disabled:opacity-50">
              {busy ? <Loader2 size={13} className="animate-spin" /> : <Check size={13} />} Confirm
            </button>
            <button onClick={() => setConfirming(false)} disabled={busy}
              title="Cancel"
              className="rounded-lg bg-ink-700 px-3 py-1.5 text-xs text-slate-300 disabled:opacity-50">
              <X size={13} />
            </button>
          </div>
        ) : (
          <button onClick={toggle} disabled={busy}
            className={`inline-flex items-center gap-2 rounded-lg px-4 py-2 text-sm font-semibold text-white disabled:opacity-50 ${
              locked ? "bg-signal-red hover:bg-red-600" : "bg-accent-600 hover:bg-accent-700"
            }`}>
            {busy ? <Loader2 size={14} className="animate-spin" /> : locked ? <Unlock size={14} /> : <Lock size={14} />}
            {locked ? "Lift lockdown" : "Activate lockdown"}
          </button>
        )}

        <div className="mt-4 border-t border-ink-700 pt-3">
          <div className="mb-1.5 text-xs font-semibold text-slate-300">My sessions</div>
          <p className="mb-2 text-[11px] text-slate-500">
            Revoke every token issued to your account (including this one). You
            will be signed out and returned to the login screen.
          </p>
          <button onClick={signOutAll} disabled={signingOut}
            className="inline-flex items-center gap-2 rounded-lg bg-ink-700 px-3 py-1.5 text-xs font-semibold text-slate-200 hover:bg-ink-600 disabled:opacity-50">
            {signingOut ? <Loader2 size={13} className="animate-spin" /> : <Power size={13} />} Sign out all my sessions
          </button>
        </div>
      </div>

      {/* security events */}
      <div className="rounded-xl border border-ink-600 bg-ink-800/70 p-4">
        <div className="mb-2 text-sm font-semibold text-slate-200">Recent login attempts</div>
        {events.login_attempts.length === 0 ? (
          <p className="py-3 text-center text-xs text-slate-500">No login attempts recorded.</p>
        ) : (
          <div className="max-h-56 overflow-auto rounded-lg border border-ink-700">
            <table className="w-full text-[11px]">
              <thead className="sticky top-0 bg-ink-900/80 text-slate-400">
                <tr>
                  <th className="px-2 py-1.5 text-left font-medium">Email</th>
                  <th className="px-2 py-1.5 text-left font-medium">IP</th>
                  <th className="px-2 py-1.5 text-left font-medium">Result</th>
                  <th className="px-2 py-1.5 text-left font-medium">Time</th>
                </tr>
              </thead>
              <tbody>
                {events.login_attempts.map((a, i) => (
                  <tr key={a.id ?? i} className="border-t border-ink-700/70">
                    <td className="px-2 py-1 text-slate-200">{a.email}</td>
                    <td className="px-2 py-1 text-slate-500">{a.ip || "—"}</td>
                    <td className="px-2 py-1">
                      <span className={`rounded px-1.5 py-0.5 text-[10px] ${
                        a.ok ? "bg-signal-green/15 text-signal-green" : "bg-signal-red/15 text-signal-red"
                      }`}>{a.ok ? "ok" : "failed"}</span>
                    </td>
                    <td className="px-2 py-1 text-slate-500">{a.created_at}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}

        <div className="mb-2 mt-4 text-sm font-semibold text-slate-200">Security audit log</div>
        {events.audit.length === 0 ? (
          <p className="py-3 text-center text-xs text-slate-500">No security events logged.</p>
        ) : (
          <div className="max-h-56 space-y-1 overflow-auto">
            {events.audit.map((e, i) => (
              <div key={e.id ?? i} className="rounded-lg bg-ink-900/40 p-2 text-[11px]">
                <div className="flex items-center gap-2">
                  <span className="rounded bg-accent/15 px-1.5 py-0.5 text-[10px] text-accent">{e.action}</span>
                  <span className="text-slate-300">{e.actor_name || ""}</span>
                  <span className="ml-auto text-[10px] text-slate-600">{e.created_at}</span>
                </div>
                {e.detail && <div className="mt-0.5 text-slate-500">{e.detail}</div>}
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}

// ---- monitoring: live system status (polls every 5s) ----
function MonitoringPanel() {
  const [s, setS] = useState(null);
  const timer = useRef(null);

  useEffect(() => {
    const poll = () => API.getSystemStatus().then(setS).catch(() => {});
    poll();
    timer.current = setInterval(poll, 5000);
    return () => clearInterval(timer.current);
  }, []);

  if (!s) {
    return (
      <div className="flex items-center gap-2 py-8 text-sm text-slate-500">
        <Loader2 size={15} className="animate-spin" /> Loading system status…
      </div>
    );
  }

  const host = s.host || {};
  const metrics = s.metrics || {};
  const cpu = host.cpu_percent;
  const ram = host.mem_percent;
  const diskUsed = host.disk_used_gb;
  const diskTotal = host.disk_total_gb;
  const dbMb = s.db_size_mb;
  const models = s.models || {};

  return (
    <div className="space-y-4">
      <div className="grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-4">
        <Kpi icon={Cpu} label="CPU" value={cpu != null ? `${Math.round(cpu)}%` : "—"} />
        <Kpi icon={MemoryStick} label="RAM" value={ram != null ? `${Math.round(ram)}%` : "—"} />
        <Kpi icon={HardDrive} label="Disk used" value={diskUsed != null ? `${diskUsed} / ${diskTotal ?? "—"} GB` : "—"} />
        <Kpi icon={Database} label="DB size" value={dbMb != null ? `${dbMb} MB` : "—"} />
        <Kpi icon={Activity} label="Uptime" value={fmtUptime(metrics.uptime_sec)} />
        <Kpi icon={Server} label="Requests" value={metrics.requests != null ? metrics.requests.toLocaleString() : "—"} />
        <Kpi icon={ShieldAlert} label="Errors (5xx)" value={metrics.errors != null ? metrics.errors.toLocaleString() : "—"} />
        <Kpi icon={Database} label="Indexed frames" value={s.indexed_frames != null ? s.indexed_frames.toLocaleString() : "—"} />
      </div>

      <div className="rounded-xl border border-ink-600 bg-ink-800/70 p-4">
        <div className="mb-3 flex items-center gap-2 text-sm font-semibold text-slate-200">
          <Activity size={15} className="text-accent" /> Model status
        </div>
        <div className="flex flex-wrap gap-2">
          <ModelChip label="CLIP" on={models.clip} />
          <ModelChip label="YOLO" on={models.yolo} />
          <ModelChip label="Face" on={models.face} />
          <span className={`inline-flex items-center gap-1.5 rounded-full px-3 py-1 text-xs font-medium ${
            s.lockdown ? "bg-signal-red/15 text-signal-red" : "bg-signal-green/15 text-signal-green"
          }`}>
            {s.lockdown ? <Lock size={12} /> : <Unlock size={12} />} {s.lockdown ? "Lockdown" : "Operational"}
          </span>
        </div>
      </div>
    </div>
  );
}

function Kpi({ icon: Icon, label, value }) {
  return (
    <div className="rounded-xl border border-ink-600 bg-ink-800/70 p-3">
      <div className="mb-1 flex items-center gap-1.5 text-[11px] text-slate-500">
        <Icon size={13} className="text-accent" /> {label}
      </div>
      <div className="text-lg font-bold text-slate-100">{value}</div>
    </div>
  );
}

function ModelChip({ label, on }) {
  return (
    <span className={`inline-flex items-center gap-1.5 rounded-full px-3 py-1 text-xs font-medium ${
      on ? "bg-signal-green/15 text-signal-green" : "bg-ink-700 text-slate-500"
    }`}>
      <span className={`h-1.5 w-1.5 rounded-full ${on ? "bg-signal-green" : "bg-slate-600"}`} />
      {label} {on ? "loaded" : "off"}
    </span>
  );
}

function fmtUptime(sec) {
  if (sec == null) return "—";
  const d = Math.floor(sec / 86400);
  const h = Math.floor((sec % 86400) / 3600);
  const m = Math.floor((sec % 3600) / 60);
  if (d) return `${d}d ${h}h`;
  if (h) return `${h}h ${m}m`;
  return `${m}m`;
}

// ---- data: export / backup downloads ----
const EXPORTS = [
  { kind: "backup.zip", icon: Database, title: "Full backup (.zip)", desc: "WAL-safe SQLite snapshot of the entire platform database.", file: "visionscan-backup.zip" },
  { kind: "cases.csv", icon: Download, title: "Cases (.csv)", desc: "All cases with creator and team names.", file: "cases.csv" },
  { kind: "complaints.csv", icon: Download, title: "Complaints (.csv)", desc: "Complaints with area, location, severity and status.", file: "complaints.csv" },
  { kind: "audit.csv", icon: Download, title: "Audit log (.csv)", desc: "Full administrative and security audit trail.", file: "audit.csv" },
];

function DataPanel() {
  const [busy, setBusy] = useState(null); // kind currently downloading
  const [err, setErr] = useState(null);

  const download = async (item) => {
    setBusy(item.kind); setErr(null);
    try {
      const blob = await API.fetchExportBlob(item.kind);
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = item.file;
      document.body.appendChild(a);
      a.click();
      a.remove();
      URL.revokeObjectURL(url);
    } catch (e) {
      setErr(e?.response?.data?.detail || "Download failed");
    } finally {
      setBusy(null);
    }
  };

  return (
    <div>
      <p className="mb-3 text-[11px] text-slate-500">
        Export platform data for offline review, backup, or handover. Every
        download is recorded in the audit log.
      </p>
      <div className="grid gap-3 sm:grid-cols-2">
        {EXPORTS.map((item) => {
          const Icon = item.icon;
          return (
            <div key={item.kind} className="rounded-xl border border-ink-600 bg-ink-800/70 p-4">
              <div className="mb-1 flex items-center gap-2 text-sm font-semibold text-slate-200">
                <Icon size={15} className="text-accent" /> {item.title}
              </div>
              <p className="mb-3 text-[11px] text-slate-500">{item.desc}</p>
              <button onClick={() => download(item)} disabled={busy === item.kind}
                className="inline-flex items-center gap-2 rounded-lg bg-accent-600 px-3 py-1.5 text-xs font-semibold text-white hover:bg-accent-700 disabled:opacity-50">
                {busy === item.kind ? <Loader2 size={13} className="animate-spin" /> : <Download size={13} />} Download
              </button>
            </div>
          );
        })}
      </div>
      {err && <div className="mt-3 text-[11px] text-signal-red">{err}</div>}
    </div>
  );
}

function UserTeamSelect({ user, teams, onAssign }) {
  const current = user.team_id ?? "";
  const [pending, setPending] = useState(null); // null = no pending change
  const [busy, setBusy] = useState(false);
  const value = pending === null ? current : pending;
  const dirty = pending !== null && pending !== current;
  const teamName = (id) =>
    id === "" || id === null ? "No team" : (teams.find((t) => String(t.id) === String(id))?.name || "team");

  const confirm = async () => {
    setBusy(true);
    try { await onAssign(user.id, pending); setPending(null); }
    finally { setBusy(false); }
  };

  return (
    <div className="flex items-center gap-1">
      <select
        value={value}
        disabled={busy}
        onChange={(e) => setPending(e.target.value)}
        title="Assign to team"
        className={`rounded-md bg-ink-900/60 px-2 py-1 text-[11px] text-slate-200 outline-none ring-1 focus:ring-2 focus:ring-accent ${dirty ? "ring-accent" : "ring-ink-600"}`}
      >
        <option value="">No team</option>
        {teams.map((t) => <option key={t.id} value={t.id}>{t.name}</option>)}
      </select>
      {dirty && (
        <>
          <button onClick={confirm} disabled={busy}
            title={`Confirm move to ${teamName(pending)}`}
            className="rounded p-1 text-signal-green hover:bg-signal-green/15 disabled:opacity-40">
            {busy ? <Loader2 size={12} className="animate-spin" /> : <Check size={13} />}
          </button>
          <button onClick={() => setPending(null)} disabled={busy}
            title="Cancel"
            className="rounded p-1 text-slate-500 hover:bg-signal-red/20 hover:text-signal-red disabled:opacity-40">
            <X size={13} />
          </button>
        </>
      )}
    </div>
  );
}

function TeamRow({ team, allUsers, onChanged }) {
  const [open, setOpen] = useState(false);
  const [members, setMembers] = useState(null);
  const [adding, setAdding] = useState("");
  const [busy, setBusy] = useState(false);

  const load = () => API.listTeamMembers(team.id).then(setMembers).catch(() => setMembers([]));
  const toggle = () => {
    const next = !open;
    setOpen(next);
    if (next && members === null) load();
  };
  const roleClass = (r) =>
    r === "admin" ? "bg-signal-red/15 text-signal-red"
    : r === "lead" ? "bg-accent/15 text-accent"
    : r === "officer" ? "bg-signal-green/15 text-signal-green"
    : "bg-ink-700 text-slate-400";

  // staff not already on this team
  const candidates = (allUsers || []).filter(
    (u) => STAFF_ROLES.includes(u.role) && u.team_id !== team.id
  );
  const change = async (uid, team_id) => {
    setBusy(true);
    try { await API.updateUser(uid, { team_id }); await load(); onChanged && onChanged(); }
    finally { setBusy(false); }
  };
  const addMember = async () => {
    if (!adding) return;
    await change(Number(adding), team.id);
    setAdding("");
  };

  return (
    <div className="rounded-lg border border-ink-600 bg-ink-800/50 text-sm">
      <button onClick={toggle} className="flex w-full items-center justify-between gap-2 p-3 text-left">
        <div className="flex items-center gap-2">
          {open ? <ChevronDown size={15} className="text-slate-400" /> : <ChevronRight size={15} className="text-slate-400" />}
          <span className="font-semibold text-slate-100">{team.name}</span>
          <span className="text-xs text-slate-500">{team.station}</span>
        </div>
        <span className="inline-flex items-center gap-1 text-xs text-slate-400"><Users size={12} /> {team.members}</span>
      </button>
      {open && (
        <div className="border-t border-ink-700 px-3 py-2">
          {members === null ? (
            <div className="flex items-center gap-2 py-2 text-xs text-slate-500"><Loader2 size={13} className="animate-spin" /> Loading members…</div>
          ) : members.length === 0 ? (
            <p className="py-2 text-xs text-slate-500">No members assigned to this team yet.</p>
          ) : (
            <div className="space-y-1">
              {members.map((m) => (
                <div key={m.id} className="flex items-center justify-between rounded-md bg-ink-900/40 px-2.5 py-1.5">
                  <div className="flex items-center gap-2">
                    <span className="font-medium text-slate-200">{m.name}</span>
                    {m.is_lead && <span className="inline-flex items-center gap-0.5 text-[10px] text-signal-amber"><Star size={10} className="fill-signal-amber" /> lead</span>}
                    <span className="inline-flex items-center gap-1 text-[11px] text-slate-500"><Mail size={10} /> {m.email}</span>
                  </div>
                  <div className="flex items-center gap-2 text-[11px]">
                    {m.badge_no && <span className="text-slate-500">{m.badge_no}</span>}
                    <span className={`rounded px-2 py-0.5 ${roleClass(m.role)}`}>{m.role}</span>
                    <button onClick={() => change(m.id, null)} disabled={busy}
                      title="Remove from team"
                      className="rounded p-0.5 text-slate-500 hover:bg-signal-red/20 hover:text-signal-red disabled:opacity-40">
                      <X size={13} />
                    </button>
                  </div>
                </div>
              ))}
            </div>
          )}

          {/* add an existing officer to this team */}
          {members !== null && (
            <div className="mt-2 flex items-center gap-2 border-t border-ink-700 pt-2">
              <select value={adding} onChange={(e) => setAdding(e.target.value)}
                className="flex-1 rounded-md bg-ink-900/60 px-2 py-1 text-[11px] text-slate-200 outline-none ring-1 ring-ink-600 focus:ring-2 focus:ring-accent">
                <option value="">{candidates.length ? "Add an officer to this team…" : "No available officers"}</option>
                {candidates.map((u) => (
                  <option key={u.id} value={u.id}>
                    {u.name} ({u.role}){u.team_id ? " · in another team" : ""}
                  </option>
                ))}
              </select>
              <button onClick={addMember} disabled={!adding || busy}
                className="inline-flex items-center gap-1 rounded-md bg-accent-600 px-2.5 py-1 text-[11px] font-semibold text-white hover:bg-accent-700 disabled:opacity-40">
                {busy ? <Loader2 size={12} className="animate-spin" /> : <UserPlus size={12} />} Add
              </button>
            </div>
          )}
        </div>
      )}
    </div>
  );
}

function CreateUserModal({ teams, onClose, onDone }) {
  const [f, setF] = useState({ name: "", email: "", password: "", role: "officer", team_id: "", badge_no: "" });
  const [busy, setBusy] = useState(false); const [err, setErr] = useState(null);
  const submit = async () => {
    setBusy(true); setErr(null);
    try { await API.createUser({ ...f, team_id: f.team_id || null }); onDone(); }
    catch (e) { setErr(e?.response?.data?.detail || "Failed"); } finally { setBusy(false); }
  };
  return (
    <Modal onClose={onClose} title="Add staff user">
      <input placeholder="Name" value={f.name} onChange={(e) => setF({ ...f, name: e.target.value })} className={inp + " mb-2"} />
      <input placeholder="Email" value={f.email} onChange={(e) => setF({ ...f, email: e.target.value })} className={inp + " mb-2"} />
      <input type="password" placeholder="Temp password" value={f.password} onChange={(e) => setF({ ...f, password: e.target.value })} className={inp + " mb-2"} />
      <div className="mb-2 grid grid-cols-2 gap-2">
        <select value={f.role} onChange={(e) => setF({ ...f, role: e.target.value })} className={inp}>
          {["officer", "lead", "admin"].map((r) => <option key={r} value={r}>{r}</option>)}
        </select>
        <select value={f.team_id} onChange={(e) => setF({ ...f, team_id: e.target.value })} className={inp}>
          <option value="">No team</option>
          {teams.map((t) => <option key={t.id} value={t.id}>{t.name}</option>)}
        </select>
      </div>
      <input placeholder="Badge no (optional)" value={f.badge_no} onChange={(e) => setF({ ...f, badge_no: e.target.value })} className={inp} />
      {err && <div className="mt-2 text-[11px] text-signal-red">{err}</div>}
      <ModalActions busy={busy} onClose={onClose} onSubmit={submit} />
    </Modal>
  );
}

function CreateTeamModal({ onClose, onDone }) {
  const [f, setF] = useState({ name: "", station: "Ahmedabad Cyber Crime Branch" });
  const [busy, setBusy] = useState(false);
  const submit = async () => { setBusy(true); try { await API.createTeam(f); onDone(); } finally { setBusy(false); } };
  return (
    <Modal onClose={onClose} title="Add team">
      <input placeholder="Team name" value={f.name} onChange={(e) => setF({ ...f, name: e.target.value })} className={inp + " mb-2"} />
      <input placeholder="Station" value={f.station} onChange={(e) => setF({ ...f, station: e.target.value })} className={inp} />
      <ModalActions busy={busy} onClose={onClose} onSubmit={submit} />
    </Modal>
  );
}

function Modal({ title, children, onClose }) {
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/80 p-4" onClick={onClose}>
      <div className="w-full max-w-md rounded-xl border border-ink-500 bg-ink-800 p-5" onClick={(e) => e.stopPropagation()}>
        <h3 className="mb-3 text-base font-semibold text-slate-100">{title}</h3>
        {children}
      </div>
    </div>
  );
}
function ModalActions({ busy, onClose, onSubmit }) {
  return (
    <div className="mt-4 flex justify-end gap-2">
      <button onClick={onClose} className="rounded-lg bg-ink-700 px-4 py-2 text-sm text-slate-300">Cancel</button>
      <button onClick={onSubmit} disabled={busy} className="inline-flex items-center gap-2 rounded-lg bg-accent-600 px-4 py-2 text-sm font-semibold text-white disabled:opacity-50">
        {busy && <Loader2 size={14} className="animate-spin" />} Save
      </button>
    </div>
  );
}

const inp = "w-full rounded-lg bg-ink-900/60 px-3 py-2 text-sm text-slate-100 outline-none ring-1 ring-ink-600 focus:ring-2 focus:ring-accent";
