import { X, Clock, Camera, Film, Check } from "lucide-react";
import { scorePct, scoreColor } from "../utils";

export default function FrameDetail({ hit, selected, onToggleSelect, onClose }) {
  if (!hit) return null;
  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/80 p-4 backdrop-blur-sm"
      onClick={onClose}
    >
      <div
        className="max-h-[90vh] w-full max-w-4xl overflow-hidden rounded-xl border border-ink-500 bg-ink-800 shadow-2xl"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="flex items-center justify-between border-b border-ink-600 px-4 py-3">
          <div className="flex items-center gap-3 text-sm">
            <span className="inline-flex items-center gap-1.5 text-slate-200">
              <Camera size={15} className="text-accent" />
              {hit.camera_id}
            </span>
            <span className="inline-flex items-center gap-1.5 font-mono text-slate-400">
              <Clock size={15} />
              {hit.timestamp_hms}
            </span>
            <span className={`font-bold ${scoreColor(hit.score)}`}>
              match {scorePct(hit.score)}
            </span>
          </div>
          <button onClick={onClose} className="text-slate-400 hover:text-white">
            <X size={20} />
          </button>
        </div>

        <div className="relative bg-black">
          <img
            src={hit.thumbnail_url}
            alt="frame"
            className="mx-auto max-h-[60vh] object-contain"
          />
        </div>

        <div className="flex items-center justify-between gap-4 px-4 py-3">
          <div className="flex flex-wrap items-center gap-1.5 text-xs text-slate-400">
            <Film size={13} />
            <span>{hit.filename}</span>
            <span className="text-slate-600">·</span>
            <span>frame #{hit.frame_id}</span>
            {hit.detections?.map((d, i) => (
              <span
                key={i}
                className="rounded bg-ink-700 px-1.5 py-0.5 text-[11px] text-slate-300"
              >
                {d.label} {Math.round(d.confidence * 100)}%
              </span>
            ))}
          </div>
          <button
            onClick={() => onToggleSelect(hit.frame_id)}
            className={`inline-flex items-center gap-1.5 whitespace-nowrap rounded-lg px-3 py-1.5 text-xs font-semibold transition ${
              selected
                ? "bg-accent text-white"
                : "bg-ink-700 text-slate-200 hover:bg-ink-600"
            }`}
          >
            <Check size={14} />
            {selected ? "In report" : "Add to report"}
          </button>
        </div>
      </div>
    </div>
  );
}
