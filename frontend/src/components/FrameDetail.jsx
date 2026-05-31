import { useEffect, useState } from "react";
import { X, Clock, Camera, Film, Check, Layers } from "lucide-react";
import { scorePct, scoreColor } from "../utils";

export default function FrameDetail({ hit, selectedIds, onToggleSelect, onClose }) {
  // Which frame of the event is shown large. Reset whenever the opened hit changes.
  const [activeId, setActiveId] = useState(null);
  useEffect(() => {
    setActiveId(hit ? hit.frame_id : null);
  }, [hit]);

  if (!hit) return null;

  // A grouped event carries every frame; a single hit is its own one-frame event.
  const frames =
    hit.event_frames && hit.event_frames.length > 1
      ? hit.event_frames
      : [
          {
            frame_id: hit.frame_id,
            timestamp_hms: hit.timestamp_hms,
            thumbnail_url: hit.thumbnail_url,
            score: hit.score,
          },
        ];
  const isEvent = frames.length > 1;
  const active = frames.find((f) => f.frame_id === activeId) || frames[0];
  const isSel = (id) => selectedIds?.has(id);
  const allSelected = frames.every((f) => isSel(f.frame_id));

  const addAll = () => {
    // Select any not-yet-selected frame (don't toggle the ones already in).
    frames.forEach((f) => {
      if (!isSel(f.frame_id)) onToggleSelect(f.frame_id);
    });
  };

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/80 p-3 backdrop-blur-sm sm:p-6"
      onClick={onClose}
    >
      <div
        className="flex max-h-[92vh] w-full max-w-6xl flex-col overflow-hidden rounded-xl border border-ink-500 bg-ink-800 shadow-2xl"
        onClick={(e) => e.stopPropagation()}
      >
        {/* header */}
        <div className="flex items-center justify-between gap-3 border-b border-ink-600 px-4 py-3">
          <div className="flex flex-wrap items-center gap-x-3 gap-y-1 text-sm">
            <span className="inline-flex items-center gap-1.5 text-slate-200">
              <Camera size={15} className="text-accent" />
              {hit.camera_id}
            </span>
            <span className="inline-flex items-center gap-1.5 font-mono text-slate-400">
              <Clock size={15} />
              {active.timestamp_hms}
            </span>
            <span className={`font-bold ${scoreColor(active.score)}`}>
              match {scorePct(active.score)}
            </span>
            {isEvent && (
              <span className="inline-flex items-center gap-1 rounded bg-accent/15 px-2 py-0.5 text-[11px] font-semibold text-accent">
                <Layers size={12} /> {frames.length} instances ·{" "}
                {hit.event_start_hms}–{hit.event_end_hms}
              </span>
            )}
          </div>
          <button onClick={onClose} className="shrink-0 text-slate-400 hover:text-white">
            <X size={20} />
          </button>
        </div>

        {/* main image — fixed stage so even a low-res (≤480px) thumbnail fills
            the popup instead of sitting tiny in the middle. */}
        <div className="relative flex h-[58vh] min-h-0 flex-1 items-center justify-center bg-black">
          <img
            src={active.thumbnail_url}
            alt={`frame ${active.frame_id}`}
            className="h-full w-auto max-w-full object-contain"
          />
          <button
            onClick={() => onToggleSelect(active.frame_id)}
            className={`absolute right-3 top-3 inline-flex items-center gap-1.5 rounded-lg px-3 py-1.5 text-xs font-semibold shadow-lg transition ${
              isSel(active.frame_id)
                ? "bg-accent text-white"
                : "bg-ink-900/80 text-slate-200 hover:bg-ink-700"
            }`}
          >
            <Check size={14} />
            {isSel(active.frame_id) ? "In report" : "Add to report"}
          </button>
        </div>

        {/* event gallery — every frame in the moment */}
        {isEvent && (
          <div className="border-t border-ink-600 px-4 pb-3 pt-2.5">
            <div className="mb-2 flex items-center justify-between text-[11px] text-slate-400">
              <span>
                All {frames.length} frames in this event — click to view, check to add to report
              </span>
              <button
                onClick={addAll}
                disabled={allSelected}
                className="rounded-lg bg-ink-700 px-2.5 py-1 font-semibold text-slate-200 transition hover:bg-accent-600 hover:text-white disabled:opacity-40"
              >
                {allSelected ? "All in report" : "Add all to report"}
              </button>
            </div>
            <div className="flex gap-2 overflow-x-auto pb-1">
              {frames.map((f) => (
                <div
                  key={f.frame_id}
                  className={`group relative h-20 w-28 shrink-0 cursor-pointer overflow-hidden rounded-lg border transition ${
                    f.frame_id === active.frame_id
                      ? "border-accent ring-1 ring-accent"
                      : "border-ink-600 hover:border-ink-400"
                  }`}
                  onClick={() => setActiveId(f.frame_id)}
                >
                  <img
                    src={f.thumbnail_url}
                    alt={`frame ${f.frame_id}`}
                    loading="lazy"
                    className="h-full w-full object-cover"
                  />
                  <span className="absolute bottom-0.5 left-0.5 rounded bg-ink-900/80 px-1 font-mono text-[9px] text-slate-300">
                    {f.timestamp_hms}
                  </span>
                  <button
                    onClick={(e) => {
                      e.stopPropagation();
                      onToggleSelect(f.frame_id);
                    }}
                    className={`absolute right-0.5 top-0.5 flex h-5 w-5 items-center justify-center rounded border transition ${
                      isSel(f.frame_id)
                        ? "border-accent bg-accent text-white"
                        : "border-white/50 bg-ink-900/60 text-transparent group-hover:border-white"
                    }`}
                    title="Add to report"
                  >
                    <Check size={12} />
                  </button>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* footer: file + detections */}
        <div className="flex flex-wrap items-center gap-1.5 border-t border-ink-600 px-4 py-2.5 text-xs text-slate-400">
          <Film size={13} />
          <span>{hit.filename}</span>
          <span className="text-slate-600">·</span>
          <span>frame #{active.frame_id}</span>
          {hit.detections?.map((d, i) => (
            <span
              key={i}
              className="rounded bg-ink-700 px-1.5 py-0.5 text-[11px] text-slate-300"
            >
              {d.label} {Math.round(d.confidence * 100)}%
            </span>
          ))}
        </div>
      </div>
    </div>
  );
}
