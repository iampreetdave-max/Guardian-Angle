import { useEffect, useState } from "react";
import {
  ArrowLeft, Loader2, FileText, Boxes, MessagesSquare, History, Eye, EyeOff,
  Lock, CheckCircle2, Star, Send, Plus, CalendarClock, MapPin, Trash2,
} from "lucide-react";
import * as API from "../../api";
import { useAuth, isStaff, isLead } from "../../auth";
import { useT } from "../../i18n";

/* Module scope: hooks cannot run here, so these hold translation KEYS and the
   render site calls t() on them. */
const TABS = [
  { key: "evidence", labelKey: "cases.tabEvidence", icon: Boxes },
  { key: "documents", labelKey: "cases.tabDocuments", icon: FileText, staffOnly: true },
  { key: "messages", labelKey: "cases.tabMessages", icon: MessagesSquare },
  { key: "schedule", labelKey: "cases.tabSchedule", icon: CalendarClock, staffOnly: true },
  { key: "timeline", labelKey: "cases.tabTimeline", icon: History, staffOnly: true },
];

// Enum-ish values that also come back from the API; anything unmapped renders raw.
const KIND_KEY = { note: "cases.kindNote", frame: "cases.kindFrame", video: "cases.kindVideo", file: "cases.kindFile", report: "cases.kindReport" };
const VIS_KEY = { team: "cases.visTeam", station: "cases.visStation", department: "cases.visDepartment", citizen: "cases.visCitizen" };
const DOC_KEY = { brief: "cases.docBrief", chargesheet: "cases.docChargesheet", other: "cases.docOther" }; // FIR stays FIR
const SEV_KEY = { low: "common.low", medium: "common.medium", high: "common.high", critical: "common.critical" };
const STATUS_KEY = { open: "common.open", active: "common.active", closed: "common.closed", pending: "common.pending" };

export default function CaseWorkspace({ caseId, onBack }) {
  const { user } = useAuth();
  const t = useT();
  const staff = isStaff(user);
  const [c, setC] = useState(null);
  const [tab, setTab] = useState("evidence");
  const [evidence, setEvidence] = useState([]);
  const [documents, setDocuments] = useState([]);
  const [messages, setMessages] = useState([]);
  const [timeline, setTimeline] = useState([]);
  const [meetings, setMeetings] = useState([]);
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);

  const loadCase = () => API.getCase(caseId).then(setC).catch(() => onBack());
  const loadTab = async (k) => {
    if (k === "evidence") setEvidence(await API.listEvidence(caseId));
    else if (k === "documents") setDocuments(await API.listDocuments(caseId).catch(() => []));
    else if (k === "messages") setMessages(await API.listMessages(caseId));
    else if (k === "schedule") setMeetings(await API.listMeetings(caseId).catch(() => []));
    else if (k === "timeline") setTimeline(await API.caseTimeline(caseId).catch(() => []));
  };

  useEffect(() => { setLoading(true); loadCase().finally(() => setLoading(false)); }, [caseId]);
  useEffect(() => { if (c) loadTab(tab); }, [tab, c]);

  if (loading || !c) return <div className="flex justify-center py-20"><Loader2 className="animate-spin text-accent" /></div>;

  const toggleVisibility = async () => {
    setBusy(true);
    try { await API.setCitizenVisibility(caseId, { citizen_visible: !c.citizen_visible }); await loadCase(); }
    finally { setBusy(false); }
  };

  return (
    <div className="mx-auto max-w-5xl p-5">
      <button onClick={onBack} className="mb-3 inline-flex items-center gap-1.5 text-xs text-slate-400 hover:text-slate-200">
        <ArrowLeft size={14} /> {t("cases.backToCases")}
      </button>

      {/* header */}
      <div className="mb-4 rounded-xl border border-ink-600 bg-ink-800/70 p-4">
        <div className="flex items-start justify-between gap-3">
          <div>
            <h2 className="text-lg font-bold text-white">#{c.id} · {c.title}</h2>
            <p className="mt-0.5 text-xs text-slate-400">{c.description}</p>
            <div className="mt-1 flex flex-wrap gap-2 text-[11px] text-slate-500">
              <span>{t("common.status")}: <span className="text-slate-300">{STATUS_KEY[c.status] ? t(STATUS_KEY[c.status]) : c.status}</span></span>
              <span>· {t("common.severity")}: {SEV_KEY[c.severity] ? t(SEV_KEY[c.severity]) : c.severity}</span><span>· {t("cases.priority")} {c.priority}</span>
              {c.members?.length ? <span>· {t("cases.members", { n: c.members.length })}</span> : null}
            </div>
          </div>
          {staff && (
            <div className="flex flex-col gap-2">
              <button onClick={toggleVisibility} disabled={busy}
                className={`inline-flex items-center gap-1.5 rounded-lg px-3 py-1.5 text-xs font-semibold ${c.citizen_visible ? "bg-signal-green/15 text-signal-green" : "bg-ink-700 text-slate-300"}`}>
                {c.citizen_visible ? <Eye size={13} /> : <EyeOff size={13} />}
                {c.citizen_visible ? t("cases.citizenCanView") : t("cases.hiddenFromCitizen")}
              </button>
              {isLead(user) && c.status !== "closed" && <CloseButton caseId={caseId} onDone={loadCase} />}
            </div>
          )}
        </div>
        {c.status === "closed" && c.verdict && (
          <div className="mt-3 rounded-lg bg-ink-900/50 p-3 text-xs">
            <span className="font-semibold text-signal-green">{t("cases.verdict")}:</span> <span className="text-slate-300">{c.verdict}</span>
          </div>
        )}
        {/* citizen rating on closed case */}
        {!staff && c.status === "closed" && <RateBox caseId={caseId} />}
      </div>

      {/* tabs */}
      <div className="mb-3 flex flex-wrap gap-1.5">
        {TABS.filter((tb) => staff || !tb.staffOnly).map((tb) => (
          <button key={tb.key} onClick={() => setTab(tb.key)}
            className={`inline-flex items-center gap-1.5 rounded-lg px-3 py-1.5 text-xs font-medium ${tab === tb.key ? "bg-accent-600 text-white" : "bg-ink-700 text-slate-300 hover:bg-ink-600"}`}>
            <tb.icon size={14} /> {t(tb.labelKey)}
          </button>
        ))}
      </div>

      {tab === "evidence" && <EvidenceTab caseId={caseId} items={evidence} staff={staff} reload={() => loadTab("evidence")} />}
      {tab === "documents" && staff && <DocumentsTab caseId={caseId} items={documents} reload={() => loadTab("documents")} />}
      {tab === "messages" && <MessagesTab caseId={caseId} items={messages} user={user} reload={() => loadTab("messages")} />}
      {tab === "schedule" && staff && <ScheduleTab caseId={caseId} items={meetings} user={user} reload={() => loadTab("schedule")} />}
      {tab === "timeline" && staff && <TimelineTab items={timeline} />}
    </div>
  );
}

function EvidenceTab({ caseId, items, staff, reload }) {
  const t = useT();
  const [f, setF] = useState({ kind: "note", caption: "", visibility: "team", ref: "" });
  const add = async () => { if (!f.caption.trim()) return; await API.addEvidence(caseId, f); setF({ ...f, caption: "", ref: "" }); reload(); };
  return (
    <div className="space-y-2">
      {staff && (
        <div className="rounded-lg border border-ink-600 bg-ink-800/50 p-3">
          <div className="grid grid-cols-2 gap-2">
            <select value={f.kind} onChange={(e) => setF({ ...f, kind: e.target.value })} className={inp}>
              {["note", "frame", "video", "file", "report"].map((k) => <option key={k} value={k}>{t(KIND_KEY[k])}</option>)}
            </select>
            <select value={f.visibility} onChange={(e) => setF({ ...f, visibility: e.target.value })} className={inp}>
              {["team", "station", "department", "citizen"].map((v) => <option key={v} value={v}>{t("cases.visible")}: {t(VIS_KEY[v])}</option>)}
            </select>
          </div>
          <input placeholder={t("cases.captionPh")} value={f.caption} onChange={(e) => setF({ ...f, caption: e.target.value })} className={inp + " mt-2"} />
          <input placeholder={t("cases.refPh")} value={f.ref} onChange={(e) => setF({ ...f, ref: e.target.value })} className={inp + " mt-2"} />
          <button onClick={add} className="mt-2 inline-flex items-center gap-1.5 rounded bg-accent-600 px-3 py-1.5 text-xs font-semibold text-white hover:bg-accent-700"><Plus size={13} /> {t("cases.addEvidence")}</button>
        </div>
      )}
      {items.length === 0 ? <p className="py-6 text-center text-xs text-slate-500">{t("cases.noEvidence")}</p> :
        items.map((e) => (
          <div key={e.id} className="rounded-lg border border-ink-600 bg-ink-800/50 p-3 text-xs">
            <div className="flex items-center justify-between">
              <span className="font-semibold text-slate-200">{KIND_KEY[e.kind] ? t(KIND_KEY[e.kind]) : e.kind}{e.ref ? ` · ${e.ref}` : ""}</span>
              <span className="rounded bg-ink-700 px-1.5 py-0.5 text-[10px] text-slate-400">{VIS_KEY[e.visibility] ? t(VIS_KEY[e.visibility]) : e.visibility}</span>
            </div>
            <p className="mt-1 text-slate-400">{e.caption}</p>
            {e.added_by_name && <p className="mt-0.5 text-[10px] text-slate-500">{t("cases.addedBy", { name: e.added_by_name })} · {e.created_at}</p>}
          </div>
        ))}
    </div>
  );
}

function DocumentsTab({ caseId, items, reload }) {
  const t = useT();
  const [f, setF] = useState({ doc_type: "FIR", title: "", content: "" });
  const add = async () => { if (!f.title.trim()) return; await API.addDocument(caseId, f); setF({ doc_type: "FIR", title: "", content: "" }); reload(); };
  return (
    <div className="space-y-2">
      <div className="rounded-lg border border-ink-600 bg-ink-800/50 p-3">
        <div className="grid grid-cols-2 gap-2">
          <select value={f.doc_type} onChange={(e) => setF({ ...f, doc_type: e.target.value })} className={inp}>
            {["FIR", "brief", "chargesheet", "other"].map((d) => <option key={d} value={d}>{DOC_KEY[d] ? t(DOC_KEY[d]) : d}</option>)}
          </select>
          <input placeholder={t("common.title")} value={f.title} onChange={(e) => setF({ ...f, title: e.target.value })} className={inp} />
        </div>
        <textarea placeholder={t("cases.docContentPh")} rows={4} value={f.content} onChange={(e) => setF({ ...f, content: e.target.value })} className={inp + " mt-2 resize-y"} />
        <button onClick={add} className="mt-2 inline-flex items-center gap-1.5 rounded bg-accent-600 px-3 py-1.5 text-xs font-semibold text-white hover:bg-accent-700"><Plus size={13} /> {t("cases.addDocument")}</button>
      </div>
      {items.map((d) => (
        <div key={d.id} className="rounded-lg border border-ink-600 bg-ink-800/50 p-3">
          <div className="flex items-center justify-between text-xs">
            <span className="font-semibold text-accent">{DOC_KEY[d.doc_type] ? t(DOC_KEY[d.doc_type]) : d.doc_type}: {d.title}</span>
            <span className="text-[10px] text-slate-500">{d.created_by_name}</span>
          </div>
          <pre className="mt-2 whitespace-pre-wrap text-[11px] text-slate-300">{d.content}</pre>
        </div>
      ))}
    </div>
  );
}

function MessagesTab({ caseId, items, user, reload }) {
  const t = useT();
  const [body, setBody] = useState("");
  const [err, setErr] = useState(null);
  const send = async () => {
    if (!body.trim()) return;
    try { await API.postMessage(caseId, { body }); setBody(""); setErr(null); reload(); }
    catch (e) { setErr(e?.response?.data?.detail || t("cases.failed")); }
  };
  return (
    <div className="space-y-2">
      {items.length === 0 ? <p className="py-4 text-center text-xs text-slate-500">{t("cases.noMessages")}</p> :
        items.map((m) => (
          <div key={m.id} className={`rounded-lg p-2.5 text-xs ${m.sender_role === "citizen" ? "bg-ink-700/40" : "bg-accent/10"}`}>
            <div className="font-semibold text-slate-200">{m.sender_name} <span className="text-[10px] font-normal text-slate-500">· {m.sender_role}</span></div>
            <p className="mt-0.5 text-slate-300">{m.body}</p>
          </div>
        ))}
      {err && <div className="text-[11px] text-signal-red">{err}</div>}
      <div className="flex gap-2">
        <input value={body} onChange={(e) => setBody(e.target.value)} placeholder={user.role === "citizen" ? t("cases.oneMessagePh") : t("cases.messagePh")} className={inp} />
        <button onClick={send} className="inline-flex items-center gap-1.5 rounded bg-accent-600 px-3 text-xs font-semibold text-white hover:bg-accent-700"><Send size={13} /></button>
      </div>
    </div>
  );
}

function ScheduleTab({ caseId, items, user, reload }) {
  const t = useT();
  const blank = { title: "", scheduled_at: "", duration_min: 60, location: "Ahmedabad Cyber Crime Branch", notes: "" };
  const [f, setF] = useState(blank);
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState(null);

  const add = async () => {
    if (!f.title.trim() || !f.scheduled_at) { setErr(t("cases.needTitleTime")); return; }
    setBusy(true); setErr(null);
    try { await API.createMeeting(caseId, f); setF(blank); reload(); }
    catch (e) { setErr(e?.response?.data?.detail || t("cases.scheduleFailed")); }
    finally { setBusy(false); }
  };
  const cancel = async (m) => {
    if (!confirm(t("cases.confirmCancelMeeting", { title: m.title }))) return;
    await API.cancelMeeting(caseId, m.id).catch(() => {});
    reload();
  };

  const now = Date.now();
  const fmt = (s) => {
    const d = new Date(s);
    return isNaN(d) ? s : d.toLocaleString([], { weekday: "short", day: "numeric", month: "short", hour: "2-digit", minute: "2-digit" });
  };
  const upcoming = items.filter((m) => new Date(m.scheduled_at).getTime() >= now);
  const past = items.filter((m) => new Date(m.scheduled_at).getTime() < now);
  const canManage = (m) => m.created_by === user.id || isLead(user);

  const Card = ({ m, dim }) => (
    <div className={`rounded-lg border border-ink-600 bg-ink-800/50 p-3 ${dim ? "opacity-60" : ""}`}>
      <div className="flex items-start justify-between gap-2">
        <div>
          <div className="flex items-center gap-2 text-sm font-semibold text-slate-100">
            <CalendarClock size={14} className="text-accent" /> {m.title}
          </div>
          <div className="mt-1 flex flex-wrap items-center gap-x-3 gap-y-0.5 text-[11px] text-slate-400">
            <span className="font-medium text-slate-300">{fmt(m.scheduled_at)}</span>
            <span>· {m.duration_min} {t("cases.min")}</span>
            <span className="inline-flex items-center gap-1"><MapPin size={11} /> {m.location}</span>
          </div>
          {m.notes && <p className="mt-1 text-xs text-slate-400">{m.notes}</p>}
          <p className="mt-1 text-[10px] text-slate-500">{t("cases.organisedBy", { name: m.created_by_name })}</p>
        </div>
        {canManage(m) && (
          <button onClick={() => cancel(m)} title={t("cases.cancelMeeting")}
            className="rounded-lg bg-ink-700 p-1.5 text-slate-400 hover:bg-signal-red/20 hover:text-signal-red">
            <Trash2 size={13} />
          </button>
        )}
      </div>
    </div>
  );

  return (
    <div className="space-y-3">
      {/* booking form */}
      <div className="rounded-lg border border-ink-600 bg-ink-800/50 p-3">
        <div className="mb-2 text-xs font-semibold text-slate-300">{t("cases.bookMeeting")}</div>
        <input placeholder={t("cases.meetingTitlePh")} value={f.title} onChange={(e) => setF({ ...f, title: e.target.value })} className={inp} />
        <div className="mt-2 grid grid-cols-1 gap-2 sm:grid-cols-3">
          <div>
            <label className="mb-0.5 block text-[10px] text-slate-500">{t("cases.dateTime")}</label>
            <input type="datetime-local" value={f.scheduled_at} onChange={(e) => setF({ ...f, scheduled_at: e.target.value })} className={inp} />
          </div>
          <div>
            <label className="mb-0.5 block text-[10px] text-slate-500">{t("cases.durationMin")}</label>
            <input type="number" min={5} max={600} step={5} value={f.duration_min} onChange={(e) => setF({ ...f, duration_min: Number(e.target.value) })} className={inp} />
          </div>
          <div>
            <label className="mb-0.5 block text-[10px] text-slate-500">{t("cases.location")}</label>
            <input value={f.location} onChange={(e) => setF({ ...f, location: e.target.value })} className={inp} />
          </div>
        </div>
        <input placeholder={t("cases.notesPh")} value={f.notes} onChange={(e) => setF({ ...f, notes: e.target.value })} className={inp + " mt-2"} />
        {err && <div className="mt-2 text-[11px] text-signal-red">{err}</div>}
        <button onClick={add} disabled={busy} className="mt-2 inline-flex items-center gap-1.5 rounded bg-accent-600 px-3 py-1.5 text-xs font-semibold text-white hover:bg-accent-700 disabled:opacity-50">
          {busy ? <Loader2 size={13} className="animate-spin" /> : <Plus size={13} />} {t("cases.scheduleMeeting")}
        </button>
        <p className="mt-1.5 text-[10px] text-slate-500">{t("cases.notifyNote")}</p>
      </div>

      {items.length === 0 && <p className="py-4 text-center text-xs text-slate-500">{t("cases.noMeetings")}</p>}
      {upcoming.length > 0 && (
        <div className="space-y-2">
          <div className="text-[11px] font-semibold uppercase tracking-wide text-slate-500">{t("cases.upcoming")}</div>
          {upcoming.map((m) => <Card key={m.id} m={m} />)}
        </div>
      )}
      {past.length > 0 && (
        <div className="space-y-2">
          <div className="text-[11px] font-semibold uppercase tracking-wide text-slate-500">{t("cases.past")}</div>
          {past.map((m) => <Card key={m.id} m={m} dim />)}
        </div>
      )}
    </div>
  );
}

function TimelineTab({ items }) {
  const t = useT();
  return (
    <div className="space-y-1.5">
      {items.length === 0 ? <p className="py-4 text-center text-xs text-slate-500">{t("cases.noActivity")}</p> :
        items.map((a) => (
          <div key={a.id} className="flex items-center gap-2 rounded-lg border border-ink-700 bg-ink-800/40 p-2 text-[11px]">
            <History size={12} className="text-slate-500" />
            <span className="font-medium text-slate-300">{a.action}</span>
            {a.detail && <span className="text-slate-500">— {a.detail}</span>}
            <span className="ml-auto text-slate-600">{a.actor_name || t("cases.system")} · {a.created_at}</span>
          </div>
        ))}
    </div>
  );
}

function CloseButton({ caseId, onDone }) {
  const t = useT();
  const [open, setOpen] = useState(false);
  const [verdict, setVerdict] = useState("");
  const [busy, setBusy] = useState(false);
  const close = async () => { if (!verdict.trim()) return; setBusy(true); try { await API.closeCase(caseId, { verdict }); setOpen(false); onDone(); } finally { setBusy(false); } };
  if (!open) return <button onClick={() => setOpen(true)} className="inline-flex items-center gap-1.5 rounded-lg bg-ink-700 px-3 py-1.5 text-xs font-semibold text-slate-200 hover:bg-signal-red/20 hover:text-signal-red"><Lock size={13} /> {t("cases.closeCase")}</button>;
  return (
    <div className="rounded-lg border border-ink-600 bg-ink-900/60 p-2">
      <textarea rows={2} value={verdict} onChange={(e) => setVerdict(e.target.value)} placeholder={t("cases.verdictPh")} className={inp + " resize-y"} />
      <div className="mt-1 flex gap-2">
        <button onClick={() => setOpen(false)} className="rounded bg-ink-700 px-2 py-1 text-[11px] text-slate-300">{t("common.cancel")}</button>
        <button onClick={close} disabled={busy} className="inline-flex items-center gap-1 rounded bg-signal-red/80 px-2 py-1 text-[11px] font-semibold text-white"><CheckCircle2 size={12} /> {t("cases.confirmClose")}</button>
      </div>
    </div>
  );
}

function RateBox({ caseId }) {
  const t = useT();
  const [stars, setStars] = useState(0);
  const [done, setDone] = useState(false);
  const submit = async (s) => { setStars(s); await API.rateCase(caseId, { stars: s, comment: "" }).catch(() => {}); setDone(true); };
  if (done) return <div className="mt-3 text-xs text-signal-green">{t("cases.thanksRating", { stars })}</div>;
  return (
    <div className="mt-3 flex items-center gap-1 text-xs text-slate-400">
      {t("cases.rateExperience")}
      {[1, 2, 3, 4, 5].map((s) => (
        <button key={s} onClick={() => submit(s)}><Star size={16} className="text-signal-amber hover:fill-signal-amber" /></button>
      ))}
    </div>
  );
}

const inp = "w-full rounded-lg bg-ink-900/60 px-3 py-2 text-sm text-slate-100 outline-none ring-1 ring-ink-600 focus:ring-2 focus:ring-accent";
