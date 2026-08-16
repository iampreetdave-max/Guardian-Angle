import { Check, Clock, Camera, Layers } from "lucide-react";
import { scorePct, scoreColor } from "../utils";

export default function FrameCard({ hit, selected, onToggleSelect, onOpen }) {
  return (
    <div
      className={`group relative overflow-hidden rounded-lg border bg-ink-800 transition ${
        selected ? "border-accent ring-1 ring-accent" : "border-ink-600 hover:border-ink-500"
      }`}
    >
      <div className="relative aspect-video cursor-pointer" onClick={() => onOpen(hit)}>
        <img
          src={hit.thumbnail_url}
          alt={`frame ${hit.frame_id}`}
          loading="lazy"
          className="h-full w-full object-cover"
        />
        {/* score badge */}
        <span
          className={`absolute right-1.5 top-1.5 rounded bg-ink-900/85 px-1.5 py-0.5 text-[11px] font-bold ${scoreColor(
            hit.score
          )}`}
        >
          {scorePct(hit.score)}
        </span>
        {/* Instance search: box the specific object that matched, so "red car"
            points at the car instead of just returning the frame it is in.
            match_bbox arrives as fractions of the frame (see schemas.py), which
            map straight onto the thumbnail. Positioning assumes the source is
            16:9 like the aspect-video container — true for CCTV and for all the
            test footage; a 4:3 source would be cropped by object-cover and the
            box would sit slightly off. */}
        {hit.match_bbox && (
          <div
            className="pointer-events-none absolute rounded-[3px] border-2 border-signal-green shadow-[0_0_0_1px_rgba(0,0,0,0.55)]"
            style={{
              left: `${Math.min(hit.match_bbox.x1, hit.match_bbox.x2) * 100}%`,
              top: `${Math.min(hit.match_bbox.y1, hit.match_bbox.y2) * 100}%`,
              width: `${Math.abs(hit.match_bbox.x2 - hit.match_bbox.x1) * 100}%`,
              height: `${Math.abs(hit.match_bbox.y2 - hit.match_bbox.y1) * 100}%`,
            }}
          />
        )}
        {/* matched-object badge (region/instance search) */}
        {hit.match_label && (
          <span className="absolute bottom-1.5 right-1.5 rounded bg-signal-green/85 px-1.5 py-0.5 text-[10px] font-semibold text-ink-900">
            {hit.match_label}
          </span>
        )}
        {/* select checkbox */}
        <button
          onClick={(e) => {
            e.stopPropagation();
            onToggleSelect(hit.frame_id);
          }}
          className={`absolute left-1.5 top-1.5 flex h-5 w-5 items-center justify-center rounded border transition ${
            selected
              ? "border-accent bg-accent text-white"
              : "border-white/50 bg-ink-900/60 text-transparent group-hover:border-white"
          }`}
          title="Add to report"
        >
          <Check size={13} />
        </button>
        {/* event badge — multiple frames collapsed into one moment */}
        {hit.event_count > 1 && (
          <span
            className="absolute bottom-1.5 left-1.5 inline-flex items-center gap-1 rounded bg-ink-900/85 px-1.5 py-0.5 text-[10px] font-medium text-accent"
            title={`${hit.event_count} frames in this event (${hit.event_start_hms}–${hit.event_end_hms})`}
          >
            <Layers size={11} />
            {hit.event_count}
          </span>
        )}
      </div>

      <div className="space-y-1 p-2">
        <div className="flex items-center justify-between text-[11px] text-slate-300">
          <span className="inline-flex items-center gap-1">
            <Camera size={11} className="text-accent" />
            {hit.camera_id}
          </span>
          <span className="inline-flex items-center gap-1 font-mono text-slate-400">
            <Clock size={11} />
            {hit.event_count > 1
              ? `${hit.event_start_hms}–${hit.event_end_hms}`
              : hit.timestamp_hms}
          </span>
        </div>
        {hit.detections?.length > 0 && (
          <div className="flex flex-wrap gap-1">
            {hit.detections.slice(0, 3).map((d, i) => (
              <span
                key={i}
                className="rounded bg-ink-700 px-1.5 py-0.5 text-[10px] text-slate-400"
              >
                {d.label}
              </span>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
