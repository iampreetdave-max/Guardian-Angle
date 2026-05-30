import { useEffect, useState } from "react";
import { Plus, Loader2, Megaphone, ShieldAlert } from "lucide-react";
import * as API from "../../api";
import { useAuth, isLead } from "../../auth";

const STATUS_COLORS = {
  submitted: "bg-signal-amber/15 text-signal-amber",
  under_review: "bg-accent/15 text-accent",
  assigned: "bg-accent/15 text-accent",
  converted: "bg-signal-green/15 text-signal-green",
  rejected: "bg-signal-red/15 text-signal-red",
};

export default function ComplaintsView({ onOpenCase }) {
  const { user } = useAuth();
  const citizen = user.role === "citizen";
  const [items, setItems] = useState([]);
  const [loading, setLoading] = useState(true);
  const [form, setForm] = useState({ title: "", description: "", category: "", location: "" });
  const [triage, setTriage] = useState(null); // complaint being triaged

  const refresh = () => { setLoading(true); API.listComplaints().then(setItems).finally(() => setLoading(false)); };
  useEffect(() => { refresh(); }, []);

  const file = async (e) => {
    e.preventDefault();
    if (!form.title.trim() || !form.description.trim()) return;
    await API.fileComplaint(form);
    setForm({ title: "", description: "", category: "", location: "" });
    refresh();
  };

  return (
    <div className="mx-auto max-w-5xl p-5">
      <div className="mb-4 flex items-center gap-2">
        <Megaphone size={20} className="text-accent" />
        <h2 className="text-lg font-bold text-white">{citizen ? "My Complaints" : "Complaints Inbox"}</h2>
      </div>

      {citizen && (
        <form onSubmit={file} className="mb-5 rounded-xl border border-ink-600 bg-ink-800/70 p-4">
          <div className="mb-2 text-sm font-semibold text-slate-200">File a new complaint</div>
          <input required placeholder="Title" value={form.title} onChange={(e) => setForm({ ...form, title: e.target.value })} className={inp + " mb-2"} />
          <textarea required placeholder="Describe what happened" rows={3} value={form.description} onChange={(e) => setForm({ ...form, description: e.target.value })} className={inp + " mb-2 resize-y"} />
          <div className="mb-2 grid grid-cols-2 gap-2">
            <input placeholder="Category (e.g. cyber-fraud)" value={form.category} onChange={(e) => setForm({ ...form, category: e.target.value })} className={inp} />
            <input placeholder="Location" value={form.location} onChange={(e) => setForm({ ...form, location: e.target.value })} className={inp} />
          </div>
          <button className="inline-flex items-center gap-2 rounded-lg bg-accent-600 px-4 py-2 text-sm font-semibold text-white hover:bg-accent-700">
            <Plus size={15} /> Submit complaint
          </button>
        </form>
      )}

      {loading ? (
        <div className="flex justify-center py-10"><Loader2 className="animate-spin text-accent" /></div>
      ) : items.length === 0 ? (
        <p className="py-10 text-center text-sm text-slate-500">No complaints yet.</p>
      ) : (
        <div className="space-y-2">
          {items.map((c) => (
            <div key={c.id} className="rounded-lg border border-ink-600 bg-ink-800/50 p-3">
              <div className="flex items-center justify-between gap-2">
                <span className="text-sm font-semibold text-slate-100">{c.title}</span>
                <span className={`rounded px-2 py-0.5 text-[10px] font-medium ${STATUS_COLORS[c.status] || "bg-ink-700 text-slate-300"}`}>{c.status}</span>
              </div>
              <p className="mt-1 text-xs text-slate-400">{c.description}</p>
              <div className="mt-1 flex flex-wrap items-center gap-2 text-[11px] text-slate-500">
                {c.category && <span>{c.category}</span>}
                {c.location && <span>· {c.location}</span>}
                {c.severity && <span>· severity: {c.severity}</span>}
                {c.response_message && <span className="text-signal-green">· responded</span>}
              </div>
              {c.response_message && (
                <div className="mt-2 rounded bg-ink-900/50 p-2 text-[11px] text-slate-300">
                  <span className="text-slate-500">Police response:</span> {c.response_message}
                </div>
              )}
              {!citizen && isLead(user) && c.status !== "converted" && (
                <button onClick={() => setTriage(c)} className="mt-2 inline-flex items-center gap-1.5 rounded bg-ink-700 px-3 py-1.5 text-xs font-semibold text-slate-200 hover:bg-accent-600 hover:text-white">
                  <ShieldAlert size={13} /> Triage &amp; open case
                </button>
              )}
              {c.case_id && (
                <button onClick={() => onOpenCase?.(c.case_id)} className="mt-2 ml-2 rounded bg-ink-700 px-3 py-1.5 text-xs text-accent hover:bg-ink-600">
                  View case #{c.case_id}
                </button>
              )}
            </div>
          ))}
        </div>
      )}

      {triage && <TriageModal complaint={triage} onClose={() => setTriage(null)} onDone={() => { setTriage(null); refresh(); }} onOpenCase={onOpenCase} />}
    </div>
  );
}

function TriageModal({ complaint, onClose, onDone, onOpenCase }) {
  const [f, setF] = useState({ severity: "high", priority: 1, response_message: "", create_case: true });
  const [busy, setBusy] = useState(false);
  const submit = async () => {
    setBusy(true);
    try {
      const res = await API.triageComplaint(complaint.id, f);
      onDone();
      if (res.case_id) onOpenCase?.(res.case_id);
    } finally { setBusy(false); }
  };
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/80 p-4" onClick={onClose}>
      <div className="w-full max-w-md rounded-xl border border-ink-500 bg-ink-800 p-5" onClick={(e) => e.stopPropagation()}>
        <h3 className="mb-3 text-base font-semibold text-slate-100">Triage: {complaint.title}</h3>
        <label className="mb-1 block text-xs text-slate-400">Severity</label>
        <select value={f.severity} onChange={(e) => setF({ ...f, severity: e.target.value })} className={inp + " mb-3"}>
          {["low", "medium", "high", "critical"].map((s) => <option key={s} value={s}>{s}</option>)}
        </select>
        <label className="mb-1 block text-xs text-slate-400">Priority (1 = highest)</label>
        <input type="number" min={1} max={5} value={f.priority} onChange={(e) => setF({ ...f, priority: +e.target.value })} className={inp + " mb-3"} />
        <label className="mb-1 block text-xs text-slate-400">Response to citizen (emailed)</label>
        <textarea rows={2} value={f.response_message} onChange={(e) => setF({ ...f, response_message: e.target.value })} className={inp + " mb-3 resize-y"} placeholder="Your complaint is registered and under investigation..." />
        <label className="mb-3 flex items-center gap-2 text-xs text-slate-300">
          <input type="checkbox" checked={f.create_case} onChange={(e) => setF({ ...f, create_case: e.target.checked })} /> Open a case from this complaint
        </label>
        <div className="flex justify-end gap-2">
          <button onClick={onClose} className="rounded-lg bg-ink-700 px-4 py-2 text-sm text-slate-300">Cancel</button>
          <button onClick={submit} disabled={busy} className="inline-flex items-center gap-2 rounded-lg bg-accent-600 px-4 py-2 text-sm font-semibold text-white disabled:opacity-50">
            {busy && <Loader2 size={14} className="animate-spin" />} Confirm
          </button>
        </div>
      </div>
    </div>
  );
}

const inp = "w-full rounded-lg bg-ink-900/60 px-3 py-2 text-sm text-slate-100 outline-none ring-1 ring-ink-600 focus:ring-2 focus:ring-accent";
