import { useEffect, useState } from "react";
import { Users, Plus, Loader2, Shield, ChevronDown, ChevronRight, Star, Mail, UserPlus, X } from "lucide-react";
import * as API from "../../api";

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
          {["users", "teams"].map((t) => (
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
                    <select
                      value={u.team_id ?? ""}
                      onChange={(e) => assignUserTeam(u.id, e.target.value)}
                      title="Assign to team"
                      className="rounded-md bg-ink-900/60 px-2 py-1 text-[11px] text-slate-200 outline-none ring-1 ring-ink-600 focus:ring-2 focus:ring-accent"
                    >
                      <option value="">No team</option>
                      {teams.map((t) => <option key={t.id} value={t.id}>{t.name}</option>)}
                    </select>
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

      {creatingUser && <CreateUserModal teams={teams} onClose={() => setCreatingUser(false)} onDone={() => { setCreatingUser(false); refresh(); }} />}
      {creatingTeam && <CreateTeamModal onClose={() => setCreatingTeam(false)} onDone={() => { setCreatingTeam(false); refresh(); }} />}
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
