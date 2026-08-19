import { useCallback, useEffect, useState } from "react";
import {
  Download, Loader2, Stethoscope, Gavel, Receipt, Building2,
  UserSquare, ScanFace, FileSignature, Globe, History,
} from "lucide-react";
import * as API from "../../api";
import { useT } from "../../i18n";

// The 7 statutory documents, with the icon + one-liner for each card. doc_type
// keys must match backend service.DOC_TYPES exactly.
const DOC_CARDS = [
  { key: "purvani_chargesheet", icon: FileSignature },
  { key: "medical_letter", icon: Stethoscope },
  { key: "remand_request", icon: Gavel },
  { key: "seizure_receipt", icon: Receipt },
  { key: "court_custody_letter", icon: Building2 },
  { key: "accused_panchanama", icon: UserSquare },
  { key: "face_identification", icon: ScanFace },
];

const LANGS = [
  { code: "en", label: "English" },
  { code: "hi", label: "हिन्दी" },
  { code: "gu", label: "ગુજરાતી" },
];

export default function DocumentGrid({ caseId, refreshKey, onGenerated }) {
  const t = useT();
  const [language, setLanguage] = useState("en");
  const [busy, setBusy] = useState(null); // doc_type currently generating
  const [history, setHistory] = useState([]);

  const loadHistory = useCallback(() => {
    if (!caseId) return;
    API.crimegptDocuments(caseId)
      .then((d) => setHistory(d.items || []))
      .catch(() => {});
  }, [caseId]);

  useEffect(() => {
    loadHistory();
  }, [loadHistory, refreshKey]);

  const generate = async (docType) => {
    setBusy(docType);
    try {
      const { blob, version } = await API.crimegptGenerateDocument(
        caseId, docType, language
      );
      // trigger the browser download
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `${docType}_case${caseId}_v${version}_${language}.pdf`;
      a.click();
      URL.revokeObjectURL(url);
      loadHistory();
      onGenerated && onGenerated();
    } catch (e) {
      /* surfaced via empty history; keep the grid resilient */
    } finally {
      setBusy(null);
    }
  };

  // latest version per doc_type for the badge
  const latest = {};
  for (const d of history) {
    if (!(d.doc_type in latest) || d.version > latest[d.doc_type]) {
      latest[d.doc_type] = d.version;
    }
  }

  return (
    <div>
      <div className="mb-3 flex flex-wrap items-center gap-2">
        <Globe size={15} className="text-slate-400" />
        <span className="text-xs text-slate-400">{t("common.language")}:</span>
        <div className="flex items-center gap-1 rounded-lg bg-ink-900/60 p-1">
          {LANGS.map((l) => (
            <button
              key={l.code}
              onClick={() => setLanguage(l.code)}
              className={`rounded px-2.5 py-1 text-xs font-semibold ${
                language === l.code ? "bg-accent-600 text-white" : "text-slate-400"
              }`}
            >
              {l.label}
            </button>
          ))}
        </div>
        {language !== "en" && (
          <span className="text-[10px] text-slate-500">
            {t("crimegpt.langNote")}
          </span>
        )}
      </div>

      <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-3">
        {DOC_CARDS.map((d) => (
          <div key={d.key} className="flex flex-col rounded-xl border border-ink-600 bg-ink-800/60 p-4">
            <div className="mb-2 flex items-center gap-2">
              <d.icon size={18} className="text-accent" />
              <span className="font-semibold text-slate-100">
                {t(`crimegpt.doc.${d.key}`)}
              </span>
              {latest[d.key] != null && (
                <span className="ml-auto rounded-full bg-ink-900/80 px-2 py-0.5 text-[10px] text-slate-400">
                  v{latest[d.key]}
                </span>
              )}
            </div>
            <p className="mb-3 flex-1 text-xs text-slate-500">
              {t(`crimegpt.doc.${d.key}_desc`)}
            </p>
            <button
              onClick={() => generate(d.key)}
              disabled={busy === d.key}
              className="inline-flex items-center justify-center gap-1.5 rounded-lg bg-accent-600 px-3 py-1.5 text-xs font-semibold text-white hover:bg-accent-700 disabled:opacity-50"
            >
              {busy === d.key ? (
                <Loader2 size={14} className="animate-spin" />
              ) : (
                <Download size={14} />
              )}
              {t("crimegpt.generatePdf")}
            </button>
          </div>
        ))}
      </div>

      {/* version history */}
      <div className="mt-5">
        <div className="mb-2 flex items-center gap-2">
          <History size={15} className="text-slate-400" />
          <h3 className="text-sm font-semibold text-slate-200">{t("crimegpt.versionHistory")}</h3>
        </div>
        {history.length === 0 ? (
          <p className="text-xs text-slate-500">{t("crimegpt.noDocs")}</p>
        ) : (
          <div className="space-y-1">
            {history.map((h) => (
              <div key={h.id} className="flex items-center justify-between rounded-lg border border-ink-600 bg-ink-800/50 px-3 py-1.5 text-xs">
                <div className="min-w-0">
                  <span className="font-semibold text-slate-200">{h.doc_title}</span>
                  <span className="ml-2 text-accent">v{h.version}</span>
                  <span className="ml-2 uppercase text-slate-500">{h.language}</span>
                </div>
                <div className="flex items-center gap-3 text-slate-500">
                  {h.generated_by_name && <span>{h.generated_by_name}</span>}
                  <span>{(h.generated_at || "").replace("T", " ").slice(0, 16)}</span>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
