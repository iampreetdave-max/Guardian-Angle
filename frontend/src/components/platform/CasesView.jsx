import { useEffect, useState } from "react";
import { Plus, Loader2, FolderClosed, FolderOpen } from "lucide-react";
import * as API from "../../api";
import { useAuth, isLead } from "../../auth";
import { useT } from "../../i18n";
import CaseWorkspace from "./CaseWorkspace";

const STATUS = {
  open: "bg-signal-amber/15 text-signal-amber",
  active: "bg-accent/15 text-accent",
  closed: "bg-slate-600/30 text-slate-400",
};

/* Status/severity values arrive from the API but the ones this screen can show
   already live in `common`, so translate those and pass anything else through
   untouched rather than rendering a raw dictionary key. */
const KNOWN = ["all", "open", "active", "closed", "pending", "low", "medium", "high", "critical"];

export default function CasesView({ openCaseId, onClearOpen }) {
  const { user } = useAuth();
  const t = useT();
  const [cases, setCases] = useState([]);
  const [loading, setLoading] = useState(true);
  const [active, setActive] = useState(openCaseId || null);
  const [filter, setFilter] = useState("all");
  const [creating, setCreating] = useState(false);

  const refresh = () => { setLoading(true); API.listCases().then(setCases).finally(() => setLoading(false)); };
  useEffect(() => { refresh(); }, []);
  useEffect(() => { if (openCaseId) setActive(openCaseId); }, [openCaseId]);

  if (active) {
    return <CaseWorkspace caseId={active} onBack={() => { setActive(null); onClearOpen?.(); refresh(); }} />;
  }

  const lbl = (v) => (KNOWN.includes(v) ? t(`common.${v}`) : v);
  const shown = cases.filter((c) => filter === "all" || c.status === filter);

  return (
    <div className="mx-auto max-w-5xl p-5">
      <div className="mb-4 flex items-center gap-3">
        <FolderOpen size={20} className="text-accent" />
        <h2 className="text-lg font-bold text-white">{user.role === "citizen" ? t("cases.myCases") : t("cases.heading")}</h2>
        <div className="ml-auto flex items-center gap-1 rounded-lg bg-ink-900/60 p-1 text-xs">
          {["all", "open", "active", "closed"].map((s) => (
            <button key={s} onClick={() => setFilter(s)} className={`rounded px-2.5 py-1 ${filter === s ? "bg-accent-600 text-white" : "text-slate-400"}`}>{lbl(s)}</button>
          ))}
        </div>
        {isLead(user) && (
          <button onClick={() => setCreating(true)} className="inline-flex items-center gap-1.5 rounded-lg bg-accent-600 px-3 py-1.5 text-xs font-semibold text-white hover:bg-accent-700">
            <Plus size={14} /> {t("cases.newCase")}
          </button>
        )}
      </div>

      {loading ? (
        <div className="flex justify-center py-10"><Loader2 className="animate-spin text-accent" /></div>
      ) : shown.length === 0 ? (
        <p className="py-10 text-center text-sm text-slate-500">{t("cases.noCases")}</p>
      ) : (
        <div className="space-y-2">
          {shown.map((c) => (
            <button key={c.id} onClick={() => setActive(c.id)} className="block w-full rounded-lg border border-ink-600 bg-ink-800/50 p-3 text-left transition hover:border-accent">
              <div className="flex items-center justify-between gap-2">
                <span className="text-sm font-semibold text-slate-100">#{c.id} · {c.title}</span>
                <span className={`inline-flex items-center gap-1 rounded px-2 py-0.5 text-[10px] font-medium ${STATUS[c.status]}`}>
                  {c.status === "closed" ? <FolderClosed size={11} /> : <FolderOpen size={11} />}{lbl(c.status)}
                </span>
              </div>
              <div className="mt-1 flex flex-wrap gap-2 text-[11px] text-slate-500">
                <span>{t("common.severity")}: {lbl(c.severity)}</span><span>· {t("cases.priority")} {c.priority}</span>
                <span>· {t("cases.evidenceCount", { n: c.evidence_count })}</span>
                {c.citizen_visible ? <span className="text-signal-green">· {t("cases.citizenVisible")}</span> : null}
              </div>
            </button>
          ))}
        </div>
      )}

      {creating && <NewCaseModal onClose={() => setCreating(false)} onDone={(id) => { setCreating(false); setActive(id); }} />}
    </div>
  );
}

function NewCaseModal({ onClose, onDone }) {
  const t = useT();
  const [f, setF] = useState({ title: "", description: "", severity: "medium", priority: 3 });
  const [busy, setBusy] = useState(false);
  const submit = async () => {
    if (!f.title.trim()) return;
    setBusy(true);
    try { const r = await API.createCase(f); onDone(r.id); } finally { setBusy(false); }
  };
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/80 p-4" onClick={onClose}>
      <div className="w-full max-w-md rounded-xl border border-ink-500 bg-ink-800 p-5" onClick={(e) => e.stopPropagation()}>
        <h3 className="mb-3 text-base font-semibold text-slate-100">{t("cases.newCase")}</h3>
        <input placeholder={t("cases.caseTitle")} value={f.title} onChange={(e) => setF({ ...f, title: e.target.value })} className={inp + " mb-2"} />
        <textarea placeholder={t("common.description")} rows={3} value={f.description} onChange={(e) => setF({ ...f, description: e.target.value })} className={inp + " mb-2 resize-y"} />
        <div className="mb-3 grid grid-cols-2 gap-2">
          <select value={f.severity} onChange={(e) => setF({ ...f, severity: e.target.value })} className={inp}>
            {["low", "medium", "high", "critical"].map((s) => <option key={s} value={s}>{t(`common.${s}`)}</option>)}
          </select>
          <input type="number" min={1} max={5} value={f.priority} onChange={(e) => setF({ ...f, priority: +e.target.value })} className={inp} />
        </div>
        <div className="flex justify-end gap-2">
          <button onClick={onClose} className="rounded-lg bg-ink-700 px-4 py-2 text-sm text-slate-300">{t("common.cancel")}</button>
          <button onClick={submit} disabled={busy} className="inline-flex items-center gap-2 rounded-lg bg-accent-600 px-4 py-2 text-sm font-semibold text-white disabled:opacity-50">
            {busy && <Loader2 size={14} className="animate-spin" />} {t("cases.create")}
          </button>
        </div>
      </div>
    </div>
  );
}

const inp = "w-full rounded-lg bg-ink-900/60 px-3 py-2 text-sm text-slate-100 outline-none ring-1 ring-ink-600 focus:ring-2 focus:ring-accent";
