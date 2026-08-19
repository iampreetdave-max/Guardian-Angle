import { useEffect, useState } from "react";
import {
  Scale, FileText, BookOpen, MessagesSquare, Loader2, Sparkles,
  WifiOff, AlertTriangle,
} from "lucide-react";
import * as API from "../../api";
import { useT } from "../../i18n";

// Module-level, so these hold dictionary KEYS — t() is called at the render site.
const MODES = [
  { key: "sections", labelKey: "arbiter.modeSections", icon: BookOpen,
    hintKey: "arbiter.hintSections" },
  { key: "fir", labelKey: "arbiter.modeFir", icon: FileText,
    hintKey: "arbiter.hintFir" },
  { key: "query", labelKey: "arbiter.modeQuery", icon: MessagesSquare,
    hintKey: "arbiter.hintQuery" },
];

// Placeholder keys for the FIR detail inputs; [stateKey, dictKey].
const FIR_FIELDS = [
  ["complainant", "arbiter.phComplainant"],
  ["accused", "arbiter.phAccused"],
  ["location", "arbiter.phLocation"],
  ["occurred_at", "arbiter.phOccurred"],
];

const LANGS = [
  { code: "en", label: "English" },
  { code: "hi", label: "हिन्दी" },
  { code: "gu", label: "ગુજરાતી" },
];

export default function ArbiterPanel({ seedText = "" }) {
  const t = useT();
  const [health, setHealth] = useState(null);
  const [mode, setMode] = useState("sections");
  const [text, setText] = useState(seedText);
  const [lang, setLang] = useState("en");
  const [fir, setFir] = useState({ complainant: "", accused: "", location: "", occurred_at: "" });
  const [busy, setBusy] = useState(false);
  const [result, setResult] = useState(null);
  const [error, setError] = useState(null);

  useEffect(() => {
    API.legalHealth().then(setHealth).catch(() => {});
  }, []);
  useEffect(() => {
    if (seedText) { setText(seedText); setMode("fir"); }
  }, [seedText]);

  const current = MODES.find((m) => m.key === mode);

  const submit = async () => {
    if (!text.trim()) return;
    setBusy(true);
    setError(null);
    setResult(null);
    try {
      let res;
      if (mode === "sections") res = await API.legalSections({ description: text.trim() });
      else if (mode === "fir")
        res = await API.legalFir({ incident: text.trim(), language: lang, ...fir });
      else res = await API.legalQuery({ question: text.trim(), language: lang });
      setResult({ mode, data: res });
    } catch (e) {
      setError(e?.response?.data?.detail || t("arbiter.requestFailed"));
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="mx-auto flex h-full max-w-5xl flex-col overflow-hidden p-5">
      {/* header */}
      <div className="mb-4 flex items-center gap-3">
        <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-accent-600">
          <Scale size={22} className="text-white" />
        </div>
        <div>
          <h2 className="text-lg font-bold text-white">
            Arbiter <span className="text-accent">{t("arbiter.legalIntelligence")}</span>
          </h2>
          <p className="text-[11px] text-slate-500">
            {t("arbiter.subtitle")}
          </p>
        </div>
        {health && (
          <span
            className={`ml-auto inline-flex items-center gap-1.5 rounded-full px-2.5 py-1 text-xs font-medium ${
              health.llm_online
                ? "bg-signal-green/15 text-signal-green"
                : "bg-signal-amber/15 text-signal-amber"
            }`}
            title={health.llm_online ? t("arbiter.geminiOnlineTitle") : t("arbiter.offlineTitle")}
          >
            {health.llm_online ? <Sparkles size={13} /> : <WifiOff size={13} />}
            {health.llm_online ? t("arbiter.geminiOnline") : t("arbiter.offlineMode")}
            <span className="text-slate-500">· {t("arbiter.corpusSections", { n: health.corpus_sections })}</span>
          </span>
        )}
      </div>

      {/* controls */}
      <div className="rounded-xl border border-ink-600 bg-ink-800/70 p-4">
        <div className="mb-3 flex flex-wrap gap-1.5">
          {MODES.map((m) => (
            <button
              key={m.key}
              onClick={() => { setMode(m.key); setResult(null); }}
              className={`inline-flex items-center gap-1.5 rounded-lg px-3 py-1.5 text-xs font-medium transition ${
                mode === m.key ? "bg-accent-600 text-white" : "bg-ink-700 text-slate-300 hover:bg-ink-600"
              }`}
            >
              <m.icon size={14} /> {t(m.labelKey)}
            </button>
          ))}
          {mode !== "sections" && (
            <select
              value={lang}
              onChange={(e) => setLang(e.target.value)}
              className="ml-auto rounded-lg bg-ink-700 px-2 py-1.5 text-xs text-slate-200 outline-none"
              title={t("arbiter.answerLang")}
            >
              {LANGS.map((l) => <option key={l.code} value={l.code}>{l.label}</option>)}
            </select>
          )}
        </div>

        <textarea
          value={text}
          onChange={(e) => setText(e.target.value)}
          rows={mode === "fir" ? 4 : 3}
          placeholder={t(current.hintKey)}
          className="w-full resize-y rounded-lg bg-ink-900/60 p-3 text-sm text-slate-100 outline-none ring-1 ring-ink-600 focus:ring-2 focus:ring-accent"
        />

        {mode === "fir" && (
          <div className="mt-2 grid grid-cols-2 gap-2">
            {FIR_FIELDS.map(([k, phKey]) => (
              <input
                key={k}
                value={fir[k]}
                onChange={(e) => setFir({ ...fir, [k]: e.target.value })}
                placeholder={t(phKey)}
                className="rounded-lg bg-ink-900/60 px-3 py-2 text-xs text-slate-100 outline-none ring-1 ring-ink-600 focus:ring-2 focus:ring-accent"
              />
            ))}
          </div>
        )}

        <button
          onClick={submit}
          disabled={busy || !text.trim()}
          className="mt-3 inline-flex items-center gap-2 rounded-lg bg-accent-600 px-5 py-2.5 text-sm font-semibold text-white transition hover:bg-accent-700 disabled:opacity-40"
        >
          {busy ? <Loader2 size={16} className="animate-spin" /> : <current.icon size={16} />}
          {mode === "fir"
            ? t("arbiter.btnFir")
            : mode === "query"
            ? t("arbiter.btnAnswer")
            : t("arbiter.btnSections")}
        </button>
      </div>

      {/* results */}
      <div className="-mr-2 mt-4 flex-1 overflow-y-auto pr-2">
        {error && (
          <div className="rounded-lg border border-signal-red/30 bg-signal-red/10 p-3 text-sm text-signal-red">
            {error}
          </div>
        )}
        {result && <Result result={result} />}
        {!result && !error && (
          <div className="flex flex-col items-center justify-center py-20 text-center text-slate-500">
            <Scale size={34} className="text-ink-500" />
            <p className="mt-3 max-w-md text-sm">
              {health?.llm_online ? t("arbiter.emptyOnline") : t("arbiter.emptyOffline")}
            </p>
          </div>
        )}
      </div>
    </div>
  );
}

function SectionCard({ s }) {
  const t = useT();
  return (
    <div className="rounded-lg border border-ink-600 bg-ink-800/50 p-3">
      <div className="flex items-center justify-between gap-2">
        <span className="text-sm font-semibold text-accent">{s.citation}</span>
        <span className="rounded bg-ink-700 px-1.5 py-0.5 text-[10px] text-slate-400">
          {t("arbiter.matchPct", { n: Math.round((s.score || 0) * 100) })}
        </span>
      </div>
      <div className="mt-0.5 text-xs font-medium text-slate-200">{s.title}</div>
      <p className="mt-1 text-xs leading-relaxed text-slate-400">{s.summary}</p>
      {s.punishment && (
        <p className="mt-1 text-[11px] text-slate-500">
          <span className="text-slate-400">{t("arbiter.punishment")}</span> {s.punishment}
        </p>
      )}
    </div>
  );
}

function Result({ result }) {
  const t = useT();
  const { mode, data } = result;

  if (mode === "sections") {
    return (
      <div className="space-y-2">
        <p className="text-sm text-slate-300">
          <span className="font-bold text-white">{data.count}</span> {t("arbiter.applicableSections")}
        </p>
        {data.sections.map((s) => <SectionCard key={s.id} s={s} />)}
      </div>
    );
  }

  if (mode === "fir") {
    return (
      <div className="space-y-3">
        <div className="flex flex-wrap gap-1.5">
          {data.applicable_sections?.map((s) => (
            <span key={s.id} className="rounded-full bg-accent/15 px-2 py-0.5 text-[11px] text-accent">
              {s.citation}
            </span>
          ))}
          <span className={`ml-auto rounded-full px-2 py-0.5 text-[10px] ${data.llm_used ? "bg-signal-green/15 text-signal-green" : "bg-signal-amber/15 text-signal-amber"}`}>
            {data.llm_used ? t("arbiter.geminiDraft") : t("arbiter.templateDraft")}
          </span>
        </div>
        <pre className="whitespace-pre-wrap rounded-lg border border-ink-600 bg-ink-900/60 p-4 text-xs leading-relaxed text-slate-200">
{data.fir_draft}
        </pre>
        <Disclaimer text={data.disclaimer} />
      </div>
    );
  }

  // query
  return (
    <div className="space-y-3">
      <div className="rounded-lg border border-ink-600 bg-ink-800/60 p-4">
        <p className="whitespace-pre-wrap text-sm leading-relaxed text-slate-100">{data.answer}</p>
        <div className="mt-2 flex flex-wrap gap-1.5">
          {data.citations?.map((c) => (
            <span key={c} className="rounded-full bg-accent/15 px-2 py-0.5 text-[11px] text-accent">{c}</span>
          ))}
        </div>
      </div>
      <div className="space-y-2">
        {data.sections?.map((s) => <SectionCard key={s.id} s={s} />)}
      </div>
      <Disclaimer text={data.disclaimer} />
    </div>
  );
}

function Disclaimer({ text }) {
  return (
    <div className="flex items-start gap-2 rounded-lg bg-signal-amber/10 p-2.5 text-[11px] leading-snug text-signal-amber/90">
      <AlertTriangle size={15} className="mt-0.5 shrink-0" />
      <span>{text}</span>
    </div>
  );
}
