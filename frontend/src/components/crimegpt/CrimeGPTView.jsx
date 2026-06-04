import { useCallback, useEffect, useMemo, useState } from "react";
import {
  FileText, Loader2, FolderOpen, Sparkles, Users, BookOpen,
} from "lucide-react";
import * as API from "../../api";
import PoolEditor from "./PoolEditor";
import SectionSuggester from "./SectionSuggester";
import DocumentGrid from "./DocumentGrid";
import CaseDiary from "./CaseDiary";

// Single-entry data pool reused across every generated document. The officer
// picks a case, fills the pool once, then suggests sections, generates the 7
// statutory documents, and reviews the auto-maintained diary.
export default function CrimeGPTView() {
  const [cases, setCases] = useState([]);
  const [caseId, setCaseId] = useState(null);
  const [pool, setPool] = useState(null);
  const [loadingPool, setLoadingPool] = useState(false);
  const [tab, setTab] = useState("pool"); // pool | sections | documents | diary
  const [diaryStamp, setDiaryStamp] = useState(0); // bump to refresh diary/docs

  // Active investigations the officer can document.
  useEffect(() => {
    API.listCases()
      .then((cs) => {
        const open = cs.filter((c) => c.status !== "closed");
        setCases(open);
        if (open.length && !caseId) setCaseId(open[0].id);
      })
      .catch(() => {});
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const loadPool = useCallback(() => {
    if (!caseId) return;
    setLoadingPool(true);
    API.crimegptGetPool(caseId)
      .then(setPool)
      .catch(() => setPool(null))
      .finally(() => setLoadingPool(false));
  }, [caseId]);

  useEffect(() => {
    loadPool();
  }, [loadPool]);

  const activeCase = useMemo(
    () => cases.find((c) => c.id === caseId) || null,
    [cases, caseId]
  );

  // The case narrative seeds the section suggester read-only.
  const narrative = activeCase
    ? `${activeCase.title || ""}. ${activeCase.description || ""}`.trim()
    : "";

  const TABS = [
    { key: "pool", label: "Data Pool", icon: Users },
    { key: "sections", label: "Suggest Sections", icon: Sparkles },
    { key: "documents", label: "Documents", icon: FileText },
    { key: "diary", label: "Case Diary", icon: BookOpen },
  ];

  return (
    <div className="mx-auto max-w-6xl p-5">
      <div className="mb-4 flex flex-wrap items-center gap-3">
        <FileText size={22} className="text-accent" />
        <div>
          <h2 className="text-lg font-bold text-white">CrimeGPT</h2>
          <p className="text-[11px] uppercase tracking-wide text-slate-500">
            Enter facts once · generate every legal document
          </p>
        </div>

        {/* case picker */}
        <div className="ml-auto flex items-center gap-2">
          <FolderOpen size={15} className="text-slate-400" />
          <select
            value={caseId || ""}
            onChange={(e) => {
              setCaseId(Number(e.target.value));
              setPool(null);
            }}
            className="rounded-lg border border-ink-600 bg-ink-800 px-3 py-1.5 text-sm text-slate-100"
          >
            {cases.length === 0 && <option value="">No open cases</option>}
            {cases.map((c) => (
              <option key={c.id} value={c.id}>
                #{c.id} · {c.title?.slice(0, 48) || "Untitled"}
              </option>
            ))}
          </select>
        </div>
      </div>

      {!caseId ? (
        <div className="flex flex-col items-center justify-center rounded-xl border border-ink-600 bg-ink-800/50 py-20 text-center text-slate-500">
          <FolderOpen size={34} />
          <p className="mt-3 max-w-sm text-sm">
            No open case to document yet. Triage a complaint into a case (or open
            one from the Cases tab), then return here to build the file.
          </p>
        </div>
      ) : (
        <>
          {/* tabs */}
          <div className="mb-4 flex flex-wrap items-center gap-1 rounded-lg bg-ink-900/60 p-1">
            {TABS.map((t) => (
              <button
                key={t.key}
                onClick={() => setTab(t.key)}
                className={`inline-flex items-center gap-1.5 rounded-md px-3 py-1.5 text-xs font-semibold transition ${
                  tab === t.key
                    ? "bg-accent-600 text-white"
                    : "text-slate-400 hover:text-slate-200"
                }`}
              >
                <t.icon size={14} /> {t.label}
              </button>
            ))}
          </div>

          {loadingPool && !pool ? (
            <div className="flex items-center justify-center py-20 text-slate-400">
              <Loader2 className="animate-spin text-accent" size={24} />
            </div>
          ) : (
            <>
              {tab === "pool" && (
                <PoolEditor caseId={caseId} pool={pool} onChange={loadPool} />
              )}
              {tab === "sections" && (
                <SectionSuggester narrative={narrative} />
              )}
              {tab === "documents" && (
                <DocumentGrid
                  caseId={caseId}
                  refreshKey={diaryStamp}
                  onGenerated={() => setDiaryStamp((n) => n + 1)}
                />
              )}
              {tab === "diary" && (
                <CaseDiary caseId={caseId} refreshKey={diaryStamp} />
              )}
            </>
          )}
        </>
      )}
    </div>
  );
}
