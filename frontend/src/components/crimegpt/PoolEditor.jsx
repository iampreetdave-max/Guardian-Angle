import { useState } from "react";
import { Plus, Trash2, Users, Boxes, Quote } from "lucide-react";
import * as API from "../../api";
import { useT } from "../../i18n";

const ROLE_BADGE = {
  accused: "bg-signal-red/15 text-signal-red",
  victim: "bg-accent/15 text-accent",
  witness: "bg-signal-green/15 text-signal-green",
};

// Shared utility class strings (kept local so the module needs no shared CSS).
const INPUT =
  "rounded-lg border border-ink-600 bg-ink-800 px-2.5 py-1.5 text-sm text-slate-100 placeholder:text-slate-500 focus:border-accent focus:outline-none";
const ADD_BTN =
  "inline-flex items-center justify-center gap-1.5 rounded-lg bg-accent-600 px-3 py-1.5 text-xs font-semibold text-white transition hover:bg-accent-700 disabled:opacity-50";
const DEL_BTN =
  "rounded-lg bg-ink-700 p-1.5 text-slate-400 transition hover:bg-signal-red/20 hover:text-signal-red";

// Tabbed pool editor: Parties / Seizures / Statements. Every add/delete writes
// to the unified pool and triggers onChange() to re-pull, so the data the
// document engine reads is always the single source of truth shown here.
export default function PoolEditor({ caseId, pool, onChange }) {
  const t = useT();
  const [sub, setSub] = useState("parties");

  const SUBS = [
    { key: "parties", label: t("crimegpt.subParties"), icon: Users, n: pool?.parties?.length || 0 },
    { key: "seizures", label: t("crimegpt.subSeizures"), icon: Boxes, n: pool?.seizures?.length || 0 },
    { key: "statements", label: t("crimegpt.subStatements"), icon: Quote, n: pool?.statements?.length || 0 },
  ];

  return (
    <div className="rounded-xl border border-ink-600 bg-ink-800/50 p-4">
      <div className="mb-4 flex items-center gap-1 rounded-lg bg-ink-900/60 p-1 text-xs">
        {SUBS.map((s) => (
          <button
            key={s.key}
            onClick={() => setSub(s.key)}
            className={`inline-flex items-center gap-1.5 rounded px-3 py-1.5 font-semibold ${
              sub === s.key ? "bg-accent-600 text-white" : "text-slate-400"
            }`}
          >
            <s.icon size={13} /> {s.label}
            <span className="rounded-full bg-ink-900/80 px-1.5 text-[10px]">{s.n}</span>
          </button>
        ))}
      </div>

      {sub === "parties" && (
        <Parties caseId={caseId} parties={pool?.parties || []} onChange={onChange} />
      )}
      {sub === "seizures" && (
        <Seizures caseId={caseId} seizures={pool?.seizures || []} onChange={onChange} />
      )}
      {sub === "statements" && (
        <Statements
          caseId={caseId}
          statements={pool?.statements || []}
          parties={pool?.parties || []}
          onChange={onChange}
        />
      )}
    </div>
  );
}

// ----------------------------------------------------------------- parties
function Parties({ caseId, parties, onChange }) {
  const t = useT();
  const blank = {
    role: "accused", name: "", age: "", gender: "", address: "", phone: "",
    id_proof: "", description: "",
  };
  const [form, setForm] = useState(blank);
  const [busy, setBusy] = useState(false);

  const add = async (e) => {
    e.preventDefault();
    if (!form.name.trim()) return;
    setBusy(true);
    try {
      await API.crimegptAddParty(caseId, {
        ...form,
        age: form.age === "" ? null : Number(form.age),
      });
      setForm(blank);
      onChange();
    } finally {
      setBusy(false);
    }
  };

  const del = async (id) => {
    await API.crimegptDeleteParty(caseId, id);
    onChange();
  };

  return (
    <div>
      <form onSubmit={add} className="mb-4 grid grid-cols-2 gap-2 sm:grid-cols-4">
        <select
          value={form.role}
          onChange={(e) => setForm({ ...form, role: e.target.value })}
          className={INPUT}
        >
          <option value="accused">{t("crimegpt.role.accused")}</option>
          <option value="victim">{t("crimegpt.role.victim")}</option>
          <option value="witness">{t("crimegpt.role.witness")}</option>
        </select>
        <input className={INPUT} placeholder={t("crimegpt.phName")} value={form.name}
          onChange={(e) => setForm({ ...form, name: e.target.value })} />
        <input className={INPUT} placeholder={t("crimegpt.phAge")} type="number" value={form.age}
          onChange={(e) => setForm({ ...form, age: e.target.value })} />
        <input className={INPUT} placeholder={t("crimegpt.phGender")} value={form.gender}
          onChange={(e) => setForm({ ...form, gender: e.target.value })} />
        <input className={`${INPUT} col-span-2`} placeholder={t("crimegpt.phAddress")} value={form.address}
          onChange={(e) => setForm({ ...form, address: e.target.value })} />
        <input className={INPUT} placeholder={t("crimegpt.phPhone")} value={form.phone}
          onChange={(e) => setForm({ ...form, phone: e.target.value })} />
        <input className={INPUT} placeholder={t("crimegpt.phIdProof")} value={form.id_proof}
          onChange={(e) => setForm({ ...form, id_proof: e.target.value })} />
        <input className={`${INPUT} col-span-2 sm:col-span-3`} placeholder={t("crimegpt.phPartyDesc")}
          value={form.description}
          onChange={(e) => setForm({ ...form, description: e.target.value })} />
        <button disabled={busy} className={ADD_BTN}>
          <Plus size={14} /> {t("common.add")}
        </button>
      </form>

      <div className="space-y-1.5">
        {parties.length === 0 && (
          <p className="text-xs text-slate-500">{t("crimegpt.noParties")}</p>
        )}
        {parties.map((p) => (
          <div key={p.id} className="flex items-center justify-between rounded-lg border border-ink-600 bg-ink-800/60 px-3 py-2 text-sm">
            <div className="min-w-0">
              <span className={`mr-2 rounded px-2 py-0.5 text-[10px] font-semibold uppercase ${ROLE_BADGE[p.role] || "bg-ink-700 text-slate-400"}`}>
                {ROLE_BADGE[p.role] ? t(`crimegpt.role.${p.role}`) : p.role}
              </span>
              <span className="font-semibold text-slate-100">{p.name}</span>
              <span className="ml-2 text-xs text-slate-500">
                {[p.age && t("crimegpt.ageYears", { n: p.age }), p.gender, p.phone]
                  .filter(Boolean)
                  .join(" · ")}
              </span>
              {p.description && (
                <div className="truncate text-xs text-slate-500">{p.description}</div>
              )}
            </div>
            <button onClick={() => del(p.id)} className={DEL_BTN}>
              <Trash2 size={14} />
            </button>
          </div>
        ))}
      </div>
    </div>
  );
}

// ----------------------------------------------------------------- seizures
function Seizures({ caseId, seizures, onChange }) {
  const t = useT();
  const blank = {
    item: "", quantity: "", description: "", seized_from: "", seized_at: "",
    witness_names: "",
  };
  const [form, setForm] = useState(blank);
  const [busy, setBusy] = useState(false);

  const add = async (e) => {
    e.preventDefault();
    if (!form.item.trim()) return;
    setBusy(true);
    try {
      await API.crimegptAddSeizure(caseId, form);
      setForm(blank);
      onChange();
    } finally {
      setBusy(false);
    }
  };
  const del = async (id) => {
    await API.crimegptDeleteSeizure(caseId, id);
    onChange();
  };

  return (
    <div>
      <form onSubmit={add} className="mb-4 grid grid-cols-2 gap-2 sm:grid-cols-3">
        <input className={INPUT} placeholder={t("crimegpt.phItem")} value={form.item}
          onChange={(e) => setForm({ ...form, item: e.target.value })} />
        <input className={INPUT} placeholder={t("crimegpt.phQuantity")} value={form.quantity}
          onChange={(e) => setForm({ ...form, quantity: e.target.value })} />
        <input className={INPUT} placeholder={t("crimegpt.phSeizedFrom")} value={form.seized_from}
          onChange={(e) => setForm({ ...form, seized_from: e.target.value })} />
        <input className={`${INPUT} col-span-2`} placeholder={t("crimegpt.phSeizureDesc")} value={form.description}
          onChange={(e) => setForm({ ...form, description: e.target.value })} />
        <input className={INPUT} placeholder={t("crimegpt.phSeizedAt")} value={form.seized_at}
          onChange={(e) => setForm({ ...form, seized_at: e.target.value })} />
        <input className={`${INPUT} col-span-2`} placeholder={t("crimegpt.phPanchWitnesses")} value={form.witness_names}
          onChange={(e) => setForm({ ...form, witness_names: e.target.value })} />
        <button disabled={busy} className={ADD_BTN}>
          <Plus size={14} /> {t("common.add")}
        </button>
      </form>

      <div className="space-y-1.5">
        {seizures.length === 0 && (
          <p className="text-xs text-slate-500">{t("crimegpt.noSeizures")}</p>
        )}
        {seizures.map((s) => (
          <div key={s.id} className="flex items-center justify-between rounded-lg border border-ink-600 bg-ink-800/60 px-3 py-2 text-sm">
            <div className="min-w-0">
              <span className="font-semibold text-slate-100">{s.item}</span>
              {s.quantity && <span className="ml-2 text-xs text-accent">×{s.quantity}</span>}
              <span className="ml-2 text-xs text-slate-500">
                {[
                  s.seized_from && t("crimegpt.fromWhom", { name: s.seized_from }),
                  s.witness_names,
                ]
                  .filter(Boolean)
                  .join(" · ")}
              </span>
            </div>
            <button onClick={() => del(s.id)} className={DEL_BTN}>
              <Trash2 size={14} />
            </button>
          </div>
        ))}
      </div>
    </div>
  );
}

// ----------------------------------------------------------------- statements
function Statements({ caseId, statements, parties, onChange }) {
  const t = useT();
  const [form, setForm] = useState({ party_id: "", statement_text: "" });
  const [busy, setBusy] = useState(false);

  const add = async (e) => {
    e.preventDefault();
    if (!form.statement_text.trim()) return;
    setBusy(true);
    try {
      await API.crimegptAddStatement(caseId, {
        party_id: form.party_id === "" ? null : Number(form.party_id),
        statement_text: form.statement_text,
      });
      setForm({ party_id: "", statement_text: "" });
      onChange();
    } finally {
      setBusy(false);
    }
  };
  const del = async (id) => {
    await API.crimegptDeleteStatement(caseId, id);
    onChange();
  };

  return (
    <div>
      <form onSubmit={add} className="mb-4 space-y-2">
        <select
          value={form.party_id}
          onChange={(e) => setForm({ ...form, party_id: e.target.value })}
          className={`${INPUT} w-full sm:w-64`}
        >
          <option value="">{t("crimegpt.phAttribute")}</option>
          {parties.map((p) => (
            <option key={p.id} value={p.id}>
              {ROLE_BADGE[p.role] ? t(`crimegpt.role.${p.role}`) : p.role}: {p.name}
            </option>
          ))}
        </select>
        <textarea
          className={`${INPUT} w-full`}
          rows={3}
          placeholder={t("crimegpt.phStatement")}
          value={form.statement_text}
          onChange={(e) => setForm({ ...form, statement_text: e.target.value })}
        />
        <button disabled={busy} className={ADD_BTN}>
          <Plus size={14} /> {t("crimegpt.recordStatement")}
        </button>
      </form>

      <div className="space-y-1.5">
        {statements.length === 0 && (
          <p className="text-xs text-slate-500">{t("crimegpt.noStatements")}</p>
        )}
        {statements.map((s) => (
          <div key={s.id} className="flex items-start justify-between gap-3 rounded-lg border border-ink-600 bg-ink-800/60 px-3 py-2 text-sm">
            <div className="min-w-0">
              {s.party_name && (
                <span className="mr-2 text-xs font-semibold text-accent">{s.party_name}</span>
              )}
              <span className="text-slate-200">{s.statement_text}</span>
              {s.recorded_by_name && (
                <div className="text-[11px] text-slate-500">
                  {t("crimegpt.recordedBy", { name: s.recorded_by_name })}
                </div>
              )}
            </div>
            <button onClick={() => del(s.id)} className={`${DEL_BTN} shrink-0`}>
              <Trash2 size={14} />
            </button>
          </div>
        ))}
      </div>
    </div>
  );
}
