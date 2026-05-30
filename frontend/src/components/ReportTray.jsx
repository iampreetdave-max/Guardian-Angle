import { useState } from "react";
import { FileText, X, Loader2 } from "lucide-react";

export default function ReportTray({ selectedHits, query, queryType, onClear, onGenerate }) {
  const [open, setOpen] = useState(false);
  const [busy, setBusy] = useState(false);
  const [caseTitle, setCaseTitle] = useState("VisionScan Investigation Report");
  const [investigator, setInvestigator] = useState("");

  if (selectedHits.length === 0) return null;

  const generate = async () => {
    setBusy(true);
    try {
      await onGenerate({
        case_title: caseTitle,
        investigator,
        query,
        query_type: queryType || "text",
        frame_ids: selectedHits.map((h) => h.frame_id),
      });
      setOpen(false);
    } finally {
      setBusy(false);
    }
  };

  return (
    <>
      <div className="fixed bottom-4 left-1/2 z-40 flex -translate-x-1/2 items-center gap-3 rounded-full border border-ink-500 bg-ink-800/95 px-4 py-2.5 shadow-2xl backdrop-blur">
        <span className="text-sm text-slate-300">
          <span className="font-bold text-accent">{selectedHits.length}</span> frame
          {selectedHits.length > 1 ? "s" : ""} selected
        </span>
        <button
          onClick={() => setOpen(true)}
          className="inline-flex items-center gap-1.5 rounded-full bg-accent-600 px-4 py-1.5 text-xs font-semibold text-white transition hover:bg-accent-700"
        >
          <FileText size={14} />
          Generate Report
        </button>
        <button onClick={onClear} className="text-slate-400 hover:text-white" title="Clear">
          <X size={16} />
        </button>
      </div>

      {open && (
        <div
          className="fixed inset-0 z-50 flex items-center justify-center bg-black/80 p-4"
          onClick={() => !busy && setOpen(false)}
        >
          <div
            className="w-full max-w-md rounded-xl border border-ink-500 bg-ink-800 p-5 shadow-2xl"
            onClick={(e) => e.stopPropagation()}
          >
            <div className="mb-4 flex items-center gap-2 text-base font-semibold text-slate-100">
              <FileText size={18} className="text-accent" />
              Forensic PDF Report
            </div>
            <label className="mb-1 block text-xs text-slate-400">Case title</label>
            <input
              value={caseTitle}
              onChange={(e) => setCaseTitle(e.target.value)}
              className="mb-3 w-full rounded-lg bg-ink-900/60 px-3 py-2 text-sm text-slate-100 outline-none ring-1 ring-ink-600 focus:ring-2 focus:ring-accent"
            />
            <label className="mb-1 block text-xs text-slate-400">Investigator</label>
            <input
              value={investigator}
              onChange={(e) => setInvestigator(e.target.value)}
              placeholder="Officer name / ID"
              className="mb-4 w-full rounded-lg bg-ink-900/60 px-3 py-2 text-sm text-slate-100 outline-none ring-1 ring-ink-600 focus:ring-2 focus:ring-accent"
            />
            <div className="mb-4 rounded-lg bg-ink-900/50 p-3 text-xs text-slate-400">
              {selectedHits.length} timestamped frames · query:{" "}
              <span className="text-slate-200">{query || "—"}</span>
            </div>
            <div className="flex justify-end gap-2">
              <button
                onClick={() => setOpen(false)}
                disabled={busy}
                className="rounded-lg bg-ink-700 px-4 py-2 text-sm text-slate-300 hover:bg-ink-600"
              >
                Cancel
              </button>
              <button
                onClick={generate}
                disabled={busy}
                className="inline-flex items-center gap-2 rounded-lg bg-accent-600 px-4 py-2 text-sm font-semibold text-white hover:bg-accent-700 disabled:opacity-50"
              >
                {busy ? <Loader2 size={15} className="animate-spin" /> : <FileText size={15} />}
                Download PDF
              </button>
            </div>
          </div>
        </div>
      )}
    </>
  );
}
