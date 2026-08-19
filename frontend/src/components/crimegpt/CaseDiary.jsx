import { useCallback, useEffect, useState } from "react";
import {
  BookOpen, Plus, Loader2, FileText, Search, Boxes, Lock, StickyNote,
} from "lucide-react";
import * as API from "../../api";
import { useT } from "../../i18n";

// entry_type -> icon + accent, so the timeline reads at a glance.
const TYPE_META = {
  document: { icon: FileText, color: "text-accent" },
  investigation: { icon: Search, color: "text-signal-green" },
  seizure: { icon: Boxes, color: "text-signal-amber" },
  custody: { icon: Lock, color: "text-signal-red" },
  note: { icon: StickyNote, color: "text-slate-400" },
};

const ENTRY_TYPES = ["note", "investigation", "custody", "seizure"];

export default function CaseDiary({ caseId, refreshKey }) {
  const t = useT();
  const [items, setItems] = useState([]);
  const [loading, setLoading] = useState(true);
  const [form, setForm] = useState({ entry_type: "note", narrative: "" });
  const [busy, setBusy] = useState(false);

  const load = useCallback(() => {
    if (!caseId) return;
    setLoading(true);
    API.crimegptDiary(caseId)
      .then((d) => setItems(d.items || []))
      .catch(() => setItems([]))
      .finally(() => setLoading(false));
  }, [caseId]);

  useEffect(() => {
    load();
  }, [load, refreshKey]);

  const add = async (e) => {
    e.preventDefault();
    if (!form.narrative.trim()) return;
    setBusy(true);
    try {
      await API.crimegptAddDiary(caseId, form);
      setForm({ entry_type: "note", narrative: "" });
      load();
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="rounded-xl border border-ink-600 bg-ink-800/50 p-4">
      <div className="mb-3 flex items-center gap-2">
        <BookOpen size={18} className="text-accent" />
        <h3 className="text-sm font-semibold text-slate-200">
          {t("crimegpt.diaryTitle")}
        </h3>
        <span className="ml-auto text-xs text-slate-500">
          {t(items.length === 1 ? "crimegpt.entryOne" : "crimegpt.entryMany", {
            n: items.length,
          })}
        </span>
      </div>

      <form onSubmit={add} className="mb-4 flex flex-wrap gap-2">
        <select
          value={form.entry_type}
          onChange={(e) => setForm({ ...form, entry_type: e.target.value })}
          className="rounded-lg border border-ink-600 bg-ink-800 px-2.5 py-1.5 text-sm text-slate-100"
        >
          {ENTRY_TYPES.map((et) => (
            <option key={et} value={et}>
              {t(`crimegpt.entry.${et}`)}
            </option>
          ))}
        </select>
        <input
          className="min-w-[12rem] flex-1 rounded-lg border border-ink-600 bg-ink-800 px-3 py-1.5 text-sm text-slate-100 placeholder:text-slate-500 focus:border-accent focus:outline-none"
          placeholder={t("crimegpt.phDiary")}
          value={form.narrative}
          onChange={(e) => setForm({ ...form, narrative: e.target.value })}
        />
        <button
          disabled={busy}
          className="inline-flex items-center gap-1.5 rounded-lg bg-accent-600 px-3 py-1.5 text-xs font-semibold text-white hover:bg-accent-700 disabled:opacity-50"
        >
          <Plus size={14} /> {t("common.add")}
        </button>
      </form>

      {loading ? (
        <div className="flex items-center justify-center py-10 text-slate-400">
          <Loader2 size={20} className="animate-spin text-accent" />
        </div>
      ) : items.length === 0 ? (
        <p className="text-xs text-slate-500">
          {t("crimegpt.noEntries")}
        </p>
      ) : (
        <ol className="relative space-y-3 border-l border-ink-600 pl-4">
          {items.map((e) => {
            const meta = TYPE_META[e.entry_type] || TYPE_META.note;
            const Icon = meta.icon;
            return (
              <li key={e.id} className="relative">
                <span className="absolute -left-[1.42rem] top-0.5 flex h-5 w-5 items-center justify-center rounded-full bg-ink-800 ring-1 ring-ink-600">
                  <Icon size={11} className={meta.color} />
                </span>
                <div className="rounded-lg border border-ink-600 bg-ink-800/60 px-3 py-2">
                  <div className="flex items-center gap-2">
                    <span className={`text-[10px] font-semibold uppercase ${meta.color}`}>
                      {TYPE_META[e.entry_type]
                        ? t(`crimegpt.entry.${e.entry_type}`)
                        : e.entry_type}
                    </span>
                    <span className="text-[10px] text-slate-500">
                      {(e.created_at || "").replace("T", " ").slice(0, 16)}
                    </span>
                    {e.created_by_name && (
                      <span className="ml-auto text-[10px] text-slate-500">
                        {e.created_by_name}
                      </span>
                    )}
                  </div>
                  <p className="mt-0.5 text-sm text-slate-200">{e.narrative}</p>
                </div>
              </li>
            );
          })}
        </ol>
      )}
    </div>
  );
}
