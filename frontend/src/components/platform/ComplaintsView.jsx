import { useEffect, useState } from "react";
import { Plus, Loader2, Megaphone, ShieldAlert, PhoneCall, ScrollText } from "lucide-react";
import * as API from "../../api";
import { useAuth, isLead } from "../../auth";
import { useT } from "../../i18n";

// Fraud channels mirror the controlled vocabulary in backend constants/cyber.py.
// The taxonomy itself is fetched from /complaints/cyber/categories at mount.
const CHANNEL_KEYS = {
  UPI: "chUPI", card: "chCard", phone_call: "chPhoneCall", SMS: "chSMS",
  WhatsApp: "chWhatsApp", fake_app: "chFakeApp", website: "chWebsite",
  social_media: "chSocial",
};

const STATUS_COLORS = {
  submitted: "bg-signal-amber/15 text-signal-amber",
  under_review: "bg-accent/15 text-accent",
  assigned: "bg-accent/15 text-accent",
  converted: "bg-signal-green/15 text-signal-green",
  rejected: "bg-signal-red/15 text-signal-red",
};

export default function ComplaintsView({ onOpenCase }) {
  const t = useT();
  const { user } = useAuth();
  const citizen = user.role === "citizen";
  const [items, setItems] = useState([]);
  const [loading, setLoading] = useState(true);
  const [form, setForm] = useState({
    title: "", description: "", category: "", location: "", area: "",
    cyber_category: "", amount_lost: "", fraud_channel: "", hours_since_incident: "",
  });
  const [areas, setAreas] = useState([]);
  const [cyber, setCyber] = useState(false);        // Cybercrime intake toggle
  const [cyberCats, setCyberCats] = useState([]);   // NCRP fraud taxonomy
  const [channels, setChannels] = useState([]);
  const [triage, setTriage] = useState(null); // complaint being triaged

  const refresh = () => { setLoading(true); API.listComplaints().then(setItems).finally(() => setLoading(false)); };
  useEffect(() => { refresh(); }, []);
  useEffect(() => { API.getAreas().then((d) => setAreas(d.areas)).catch(() => {}); }, []);
  useEffect(() => {
    // Fetch the taxonomy once for everyone: citizens need it for the intake
    // form, staff need it to label cyber complaints in the inbox.
    if (cyberCats.length) return;
    API.getCyberCategories().then((d) => {
      setCyberCats(d.categories || []);
      setChannels(d.fraud_channels || []);
    }).catch(() => {});
  }, [cyberCats.length]);

  // Fraud channel label: keyed in the dictionary, raw value if the API adds one.
  const chLabel = (ch) => (CHANNEL_KEYS[ch] ? t(`complaints.${CHANNEL_KEYS[ch]}`) : ch);
  // Map a taxonomy key to its label (falls back to the raw key for the inbox).
  const cyberLabel = (key) => cyberCats.find((c) => c.key === key)?.label || key;
  // The picked taxonomy entry drives the inline legal sections / tip / banner.
  const picked = cyberCats.find((c) => c.key === form.cyber_category) || null;
  const hrs = parseFloat(form.hours_since_incident);
  const goldenHour = !!picked?.golden_hour && !Number.isNaN(hrs) && hrs <= 24;

  const file = async (e) => {
    e.preventDefault();
    if (!form.title.trim() || !form.description.trim()) return;
    const payload = {
      title: form.title, description: form.description,
      category: form.category || null, location: form.location || null,
      area: form.area || null,
    };
    if (cyber) {
      // Only send cyber fields when the Cybercrime form is active. Blank
      // numeric/select inputs become null so the API validators are happy.
      payload.cyber_category = form.cyber_category || null;
      payload.fraud_channel = form.fraud_channel || null;
      payload.amount_lost = form.amount_lost === "" ? null : Number(form.amount_lost);
      payload.hours_since_incident =
        form.hours_since_incident === "" ? null : Number(form.hours_since_incident);
    }
    await API.fileComplaint(payload);
    setForm({
      title: "", description: "", category: "", location: "", area: "",
      cyber_category: "", amount_lost: "", fraud_channel: "", hours_since_incident: "",
    });
    refresh();
  };

  return (
    <div className="mx-auto max-w-5xl p-5">
      <div className="mb-4 flex items-center gap-2">
        <Megaphone size={20} className="text-accent" />
        <h2 className="text-lg font-bold text-white">{t(citizen ? "complaints.myComplaints" : "complaints.inbox")}</h2>
      </div>

      {citizen && (
        <form onSubmit={file} className="mb-5 rounded-xl border border-ink-600 bg-ink-800/70 p-4">
          <div className="mb-2 flex items-center justify-between gap-2">
            <div className="text-sm font-semibold text-slate-200">{t("complaints.fileNew")}</div>
            <label className="inline-flex cursor-pointer items-center gap-2 text-xs font-medium text-slate-300"
              title={t("complaints.cyberHint")}>
              <input type="checkbox" checked={cyber}
                onChange={(e) => setCyber(e.target.checked)} />
              <ShieldAlert size={13} className={cyber ? "text-signal-red" : "text-slate-500"} />
              {t("complaints.cyber")}
            </label>
          </div>
          <input required placeholder={t("common.title")} value={form.title} onChange={(e) => setForm({ ...form, title: e.target.value })} className={inp + " mb-2"} />
          <textarea required placeholder={t("complaints.descPh")} rows={3} value={form.description} onChange={(e) => setForm({ ...form, description: e.target.value })} className={inp + " mb-2 resize-y"} />
          <div className="mb-2 grid grid-cols-2 gap-2 sm:grid-cols-3">
            {cyber ? (
              <select value={form.cyber_category}
                onChange={(e) => setForm({ ...form, cyber_category: e.target.value })}
                className={inp} title={t("complaints.fraudTypeHint")}>
                <option value="">{t("complaints.fraudTypePh")}</option>
                {cyberCats.map((c) => <option key={c.key} value={c.key}>{c.label}</option>)}
              </select>
            ) : (
              <input placeholder={t("complaints.categoryPh")} value={form.category} onChange={(e) => setForm({ ...form, category: e.target.value })} className={inp} />
            )}
            <select value={form.area} onChange={(e) => setForm({ ...form, area: e.target.value })} className={inp}
              title={t("complaints.areaHint")}>
              <option value="">{t("complaints.areaPh")}</option>
              {areas.map((a) => <option key={a.name} value={a.name}>{a.name}</option>)}
            </select>
            <input placeholder={t("complaints.landmarkPh")} value={form.location} onChange={(e) => setForm({ ...form, location: e.target.value })} className={inp} />
          </div>

          {cyber && (
            <>
              <div className="mb-2 grid grid-cols-2 gap-2 sm:grid-cols-3">
                <input type="number" min={0} step="1" placeholder={t("complaints.amountPh")}
                  value={form.amount_lost}
                  onChange={(e) => setForm({ ...form, amount_lost: e.target.value })}
                  className={inp} title={t("complaints.amountHint")} />
                <select value={form.fraud_channel}
                  onChange={(e) => setForm({ ...form, fraud_channel: e.target.value })}
                  className={inp} title={t("complaints.channelHint")}>
                  <option value="">{t("complaints.channelPh")}</option>
                  {channels.map((ch) => <option key={ch} value={ch}>{chLabel(ch)}</option>)}
                </select>
                <input type="number" min={0} step="1" placeholder={t("complaints.hoursPh")}
                  value={form.hours_since_incident}
                  onChange={(e) => setForm({ ...form, hours_since_incident: e.target.value })}
                  className={inp} title={t("complaints.hoursHint")} />
              </div>

              {goldenHour && (
                <div className="mb-2 flex items-start gap-2 rounded-lg border border-signal-red bg-signal-red/15 p-3 text-xs font-semibold text-signal-red">
                  <PhoneCall size={16} className="mt-0.5 shrink-0" />
                  <span>{t("complaints.goldenPre")} <span className="font-bold">1930</span> {t("complaints.goldenPost")}</span>
                </div>
              )}

              {picked && (
                <div className="mb-2 rounded-lg border border-ink-600 bg-ink-900/50 p-3 text-[11px] text-slate-300">
                  <p className="text-slate-400">{picked.description}</p>
                  <div className="mt-1.5 flex items-start gap-1.5 text-slate-300">
                    <ScrollText size={13} className="mt-0.5 shrink-0 text-accent" />
                    <span><span className="text-slate-500">{t("complaints.sections")}</span> {picked.legal_sections}</span>
                  </div>
                  {picked.prevention && (
                    <p className="mt-1.5 text-signal-green">
                      <span className="text-slate-500">{t("complaints.tip")}</span> {picked.prevention}
                    </p>
                  )}
                </div>
              )}
            </>
          )}

          <button className="inline-flex items-center gap-2 rounded-lg bg-accent-600 px-4 py-2 text-sm font-semibold text-white hover:bg-accent-700">
            <Plus size={15} /> {t("complaints.submitComplaint")}
          </button>
        </form>
      )}

      {loading ? (
        <div className="flex justify-center py-10"><Loader2 className="animate-spin text-accent" /></div>
      ) : items.length === 0 ? (
        <p className="py-10 text-center text-sm text-slate-500">{t("complaints.empty")}</p>
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
                {c.cyber_category && (
                  <span className="rounded bg-signal-red/15 px-1.5 py-0.5 font-medium text-signal-red">
                    {cyberLabel(c.cyber_category)}
                  </span>
                )}
                {c.category && <span>{c.category}</span>}
                {c.amount_lost != null && <span>· ₹{Number(c.amount_lost).toLocaleString("en-IN")} {t("complaints.lost")}</span>}
                {c.fraud_channel && <span>· {t("complaints.via")} {chLabel(c.fraud_channel)}</span>}
                {c.location && <span>· {c.location}</span>}
                {c.severity && <span>· {t("common.severity")}: {t(`common.${c.severity}`)}</span>}
                {c.response_message && <span className="text-signal-green">· {t("complaints.responded")}</span>}
              </div>
              {c.response_message && (
                <div className="mt-2 rounded bg-ink-900/50 p-2 text-[11px] text-slate-300">
                  <span className="text-slate-500">{t("complaints.policeResponse")}</span> {c.response_message}
                </div>
              )}
              {!citizen && isLead(user) && c.status !== "converted" && (
                <button onClick={() => setTriage(c)} className="mt-2 inline-flex items-center gap-1.5 rounded bg-ink-700 px-3 py-1.5 text-xs font-semibold text-slate-200 hover:bg-accent-600 hover:text-white">
                  <ShieldAlert size={13} /> {t("complaints.triageOpen")}
                </button>
              )}
              {c.case_id && (
                <button onClick={() => onOpenCase?.(c.case_id)} className="mt-2 ml-2 rounded bg-ink-700 px-3 py-1.5 text-xs text-accent hover:bg-ink-600">
                  {t("complaints.viewCase", { id: c.case_id })}
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
  const t = useT();
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
        <h3 className="mb-3 text-base font-semibold text-slate-100">{t("complaints.triageOf", { title: complaint.title })}</h3>
        <label className="mb-1 block text-xs text-slate-400">{t("common.severity")}</label>
        <select value={f.severity} onChange={(e) => setF({ ...f, severity: e.target.value })} className={inp + " mb-3"}>
          {["low", "medium", "high", "critical"].map((s) => <option key={s} value={s}>{t(`common.${s}`)}</option>)}
        </select>
        <label className="mb-1 block text-xs text-slate-400">{t("complaints.priority")}</label>
        <input type="number" min={1} max={5} value={f.priority} onChange={(e) => setF({ ...f, priority: +e.target.value })} className={inp + " mb-3"} />
        <label className="mb-1 block text-xs text-slate-400">{t("complaints.responseLabel")}</label>
        <textarea rows={2} value={f.response_message} onChange={(e) => setF({ ...f, response_message: e.target.value })} className={inp + " mb-3 resize-y"} placeholder={t("complaints.responsePh")} />
        <label className="mb-3 flex items-center gap-2 text-xs text-slate-300">
          <input type="checkbox" checked={f.create_case} onChange={(e) => setF({ ...f, create_case: e.target.checked })} /> {t("complaints.createCase")}
        </label>
        <div className="flex justify-end gap-2">
          <button onClick={onClose} className="rounded-lg bg-ink-700 px-4 py-2 text-sm text-slate-300">{t("common.cancel")}</button>
          <button onClick={submit} disabled={busy} className="inline-flex items-center gap-2 rounded-lg bg-accent-600 px-4 py-2 text-sm font-semibold text-white disabled:opacity-50">
            {busy && <Loader2 size={14} className="animate-spin" />} {t("complaints.confirm")}
          </button>
        </div>
      </div>
    </div>
  );
}

const inp = "w-full rounded-lg bg-ink-900/60 px-3 py-2 text-sm text-slate-100 outline-none ring-1 ring-ink-600 focus:ring-2 focus:ring-accent";
