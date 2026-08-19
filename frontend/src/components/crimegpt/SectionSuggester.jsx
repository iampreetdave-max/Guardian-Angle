import { useEffect, useState } from "react";
import { Sparkles, Loader2, ScrollText, TriangleAlert, Gavel } from "lucide-react";
import * as API from "../../api";
import { useT } from "../../i18n";

const INPUT =
  "w-full rounded-lg border border-ink-600 bg-ink-800 px-3 py-2 text-sm text-slate-100 placeholder:text-slate-500 focus:border-accent focus:outline-none";

// READ-ONLY section intelligence: scores the case narrative against the offline
// BNS/BNSS catalogue and shows ranked suggestions with why-matched terms. It
// never writes to the case — it only informs the officer which sections apply.
export default function SectionSuggester({ narrative }) {
  const t = useT();
  const [text, setText] = useState(narrative || "");
  const [results, setResults] = useState(null);
  const [busy, setBusy] = useState(false);

  // Auto-run once on mount when the case already has a narrative.
  useEffect(() => {
    setText(narrative || "");
    if (narrative && narrative.trim().length > 8) run(narrative);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [narrative]);

  const run = async (override) => {
    const n = override ?? text;
    if (!n.trim()) return;
    setBusy(true);
    try {
      const data = await API.crimegptSuggestSections({ narrative: n, top_k: 8 });
      setResults(data);
    } catch {
      setResults(null);
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="rounded-xl border border-ink-600 bg-ink-800/50 p-4">
      <textarea
        className={INPUT}
        rows={4}
        value={text}
        onChange={(e) => setText(e.target.value)}
        placeholder={t("crimegpt.phNarrative")}
      />
      <button
        onClick={() => run()}
        disabled={busy}
        className="mt-2 inline-flex items-center gap-1.5 rounded-lg bg-accent-600 px-3 py-1.5 text-xs font-semibold text-white hover:bg-accent-700 disabled:opacity-50"
      >
        {busy ? <Loader2 size={14} className="animate-spin" /> : <Sparkles size={14} />}
        {t("crimegpt.suggestSections")}
      </button>

      {results && (
        <div className="mt-4">
          <p className="mb-2 text-xs text-slate-400">
            {t(results.count === 1 ? "crimegpt.matchOne" : "crimegpt.matchMany", {
              n: results.count,
            })}
          </p>
          {results.count === 0 ? (
            <p className="text-sm text-slate-500">
              {t("crimegpt.noMatch")}
            </p>
          ) : (
            <div className="space-y-2">
              {results.suggestions.map((s) => (
                <div key={s.key} className="rounded-lg border border-ink-600 bg-ink-800/70 p-3">
                  <div className="flex items-start justify-between gap-2">
                    <div className="flex items-center gap-2">
                      <ScrollText size={15} className="text-accent" />
                      <span className="font-semibold text-slate-100">{s.label}</span>
                      {s.verify && (
                        <span className="inline-flex items-center gap-1 rounded bg-signal-amber/15 px-1.5 py-0.5 text-[10px] font-semibold text-signal-amber">
                          <TriangleAlert size={10} /> {t("crimegpt.verifyClause")}
                        </span>
                      )}
                    </div>
                    <span className="rounded-full bg-ink-900/80 px-2 py-0.5 text-[10px] text-slate-400">
                      {t("crimegpt.score", { n: s.score })}
                    </span>
                  </div>

                  {s.bns.length > 0 && (
                    <div className="mt-1.5 flex flex-wrap gap-1.5">
                      {s.bns.map((b) => (
                        <span key={b} className="rounded bg-accent/10 px-2 py-0.5 text-[11px] text-accent">
                          {b}
                        </span>
                      ))}
                    </div>
                  )}
                  {s.other?.length > 0 && (
                    <div className="mt-1 flex flex-wrap gap-1.5">
                      {s.other.map((o) => (
                        <span key={o} className="rounded bg-signal-green/10 px-2 py-0.5 text-[11px] text-signal-green">
                          {o}
                        </span>
                      ))}
                    </div>
                  )}
                  {s.bnss?.length > 0 && (
                    <p className="mt-1.5 text-[11px] text-slate-500">
                      <span className="font-semibold">{t("crimegpt.procedure")}</span>{" "}
                      {s.bnss.join("; ")}
                    </p>
                  )}
                  {s.judgments?.length > 0 && (
                    <p className="mt-1 flex items-start gap-1 text-[11px] text-slate-400">
                      <Gavel size={11} className="mt-0.5 shrink-0" />
                      <span>{s.judgments.join(" · ")}</span>
                    </p>
                  )}
                  {s.matched_terms?.length > 0 && (
                    <p className="mt-1.5 text-[10px] text-slate-500">
                      {t("crimegpt.matched")}{" "}
                      {s.matched_terms.map((m) => `“${m}”`).join(", ")}
                    </p>
                  )}
                </div>
              ))}
            </div>
          )}
          <p className="mt-3 text-[10px] text-slate-500">
            {t("crimegpt.suggestNote")}
          </p>
        </div>
      )}
    </div>
  );
}
