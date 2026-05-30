import { useEffect, useState } from "react";
import {
  Scale, FileText, BookOpen, MessagesSquare, Loader2, Sparkles,
  WifiOff, AlertTriangle,
} from "lucide-react";
import * as API from "../../api";

const MODES = [
  { key: "sections", label: "Section Lookup", icon: BookOpen,
    hint: "Describe a crime; get the applicable IPC / IT Act sections." },
  { key: "fir", label: "FIR Draft", icon: FileText,
    hint: "Describe the incident; get a structured FIR draft with sections." },
  { key: "query", label: "Legal Q&A", icon: MessagesSquare,
    hint: "Ask a legal question in plain language; get a cited answer." },
];

const LANGS = [
  { code: "en", label: "English" },
  { code: "hi", label: "हिन्दी" },
  { code: "gu", label: "ગુજરાતી" },
];

export default function ArbiterPanel({ seedText = "" }) {
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
      setError(e?.response?.data?.detail || "Request failed.");
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
            Arbiter <span className="text-accent">Legal Intelligence</span>
          </h2>
          <p className="text-[11px] text-slate-500">
            FIR drafting · section lookup · citizen Q&amp;A — over IPC, IT Act 2000 &amp; CrPC
          </p>
        </div>
        {health && (
          <span
            className={`ml-auto inline-flex items-center gap-1.5 rounded-full px-2.5 py-1 text-xs font-medium ${
              health.llm_online
                ? "bg-signal-green/15 text-signal-green"
                : "bg-signal-amber/15 text-signal-amber"
            }`}
            title={health.llm_online ? "Gemini generation online" : "Offline mode: RAG retrieval + templates"}
          >
            {health.llm_online ? <Sparkles size={13} /> : <WifiOff size={13} />}
            {health.llm_online ? "Gemini online" : "Offline mode"}
            <span className="text-slate-500">· {health.corpus_sections} sections</span>
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
              <m.icon size={14} /> {m.label}
            </button>
          ))}
          {mode !== "sections" && (
            <select
              value={lang}
              onChange={(e) => setLang(e.target.value)}
              className="ml-auto rounded-lg bg-ink-700 px-2 py-1.5 text-xs text-slate-200 outline-none"
              title="Answer language"
            >
              {LANGS.map((l) => <option key={l.code} value={l.code}>{l.label}</option>)}
            </select>
          )}
        </div>

        <textarea
          value={text}
          onChange={(e) => setText(e.target.value)}
          rows={mode === "fir" ? 4 : 3}
          placeholder={current.hint}
          className="w-full resize-y rounded-lg bg-ink-900/60 p-3 text-sm text-slate-100 outline-none ring-1 ring-ink-600 focus:ring-2 focus:ring-accent"
        />

        {mode === "fir" && (
          <div className="mt-2 grid grid-cols-2 gap-2">
            {[
              ["complainant", "Complainant name"],
              ["accused", "Accused (if known)"],
              ["location", "Place of offence"],
              ["occurred_at", "Date/time of offence"],
            ].map(([k, ph]) => (
              <input
                key={k}
                value={fir[k]}
                onChange={(e) => setFir({ ...fir, [k]: e.target.value })}
                placeholder={ph}
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
          {mode === "fir" ? "Draft FIR" : mode === "query" ? "Get Answer" : "Find Sections"}
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
              Describe an incident or ask a question. Arbiter retrieves the relevant
              statutes and {health?.llm_online ? "drafts a response with Gemini" : "composes a cited draft offline"}.
            </p>
          </div>
        )}
      </div>
    </div>
  );
}

function SectionCard({ s }) {
  return (
    <div className="rounded-lg border border-ink-600 bg-ink-800/50 p-3">
      <div className="flex items-center justify-between gap-2">
        <span className="text-sm font-semibold text-accent">{s.citation}</span>
        <span className="rounded bg-ink-700 px-1.5 py-0.5 text-[10px] text-slate-400">
          {Math.round((s.score || 0) * 100)}% match
        </span>
      </div>
      <div className="mt-0.5 text-xs font-medium text-slate-200">{s.title}</div>
      <p className="mt-1 text-xs leading-relaxed text-slate-400">{s.summary}</p>
      {s.punishment && (
        <p className="mt-1 text-[11px] text-slate-500">
          <span className="text-slate-400">Punishment:</span> {s.punishment}
        </p>
      )}
    </div>
  );
}

function Result({ result }) {
  const { mode, data } = result;

  if (mode === "sections") {
    return (
      <div className="space-y-2">
        <p className="text-sm text-slate-300">
          <span className="font-bold text-white">{data.count}</span> applicable sections
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
            {data.llm_used ? "Gemini draft" : "Template draft"}
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
