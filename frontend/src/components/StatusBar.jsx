import { useEffect, useRef, useState } from "react";
import { Cpu, Database, ScanFace, Boxes, Sparkles, ChevronDown } from "lucide-react";

/* Five always-visible chips (device, frame count, CLIP, YOLOv8, ArcFace) used to
   sit in the header. On anything narrower than a very wide desktop they wrapped
   onto extra rows, pushed the header taller and crowded the alert bell and the
   user menu. The information is worth keeping — "running on CPU, all models
   loaded" is the offline-deployability argument — but it is reference detail,
   not something that needs to be on screen at all times.

   So it collapses to a single control that shows the one thing you glance at
   (are the models up?) and reveals the rest on demand. */

function Row({ ok, icon: Icon, label, value }) {
  return (
    <div className="flex items-center justify-between gap-6 px-3 py-2">
      <span className="inline-flex items-center gap-2 text-xs text-slate-300">
        <Icon size={14} className={ok === false ? "text-slate-500" : "text-accent"} />
        {label}
      </span>
      {value !== undefined ? (
        <span className="font-mono text-xs text-slate-200">{value}</span>
      ) : (
        <span
          className={`text-[11px] font-semibold ${
            ok ? "text-signal-green" : "text-slate-500"
          }`}
        >
          {ok ? "Loaded" : "Unavailable"}
        </span>
      )}
    </div>
  );
}

export default function StatusBar({ health }) {
  const [open, setOpen] = useState(false);
  const ref = useRef(null);

  useEffect(() => {
    if (!open) return;
    const onDown = (e) => {
      if (ref.current && !ref.current.contains(e.target)) setOpen(false);
    };
    const onKey = (e) => e.key === "Escape" && setOpen(false);
    document.addEventListener("mousedown", onDown);
    document.addEventListener("keydown", onKey);
    return () => {
      document.removeEventListener("mousedown", onDown);
      document.removeEventListener("keydown", onKey);
    };
  }, [open]);

  if (!health) return null;
  const m = health.models || {};
  const models = [m.clip, m.yolo, m.face];
  const up = models.filter(Boolean).length;
  const allUp = up === models.length;

  return (
    <div className="relative" ref={ref}>
      <button
        onClick={() => setOpen((v) => !v)}
        aria-label={`System status: ${up} of ${models.length} models loaded`}
        aria-expanded={open}
        title={`${up}/${models.length} models loaded · ${health.device?.toUpperCase()}`}
        className="inline-flex h-9 items-center gap-2 rounded-lg bg-ink-700 px-2.5 text-xs font-medium
                   text-slate-300 transition hover:bg-ink-600 hover:text-slate-100"
      >
        <span
          className={`h-2 w-2 shrink-0 rounded-full ${
            allUp ? "bg-signal-green" : "bg-amber-400"
          }`}
        />
        <span className="hidden whitespace-nowrap xl:inline">
          {allUp ? "Systems ready" : `${up}/${models.length} models`}
        </span>
        <ChevronDown size={13} className="hidden shrink-0 opacity-60 xl:inline" />
      </button>

      {open && (
        <div
          className="absolute right-0 top-full z-40 mt-2 w-60 overflow-hidden rounded-xl border
                     border-ink-600 bg-ink-800 py-1 shadow-2xl"
          role="dialog"
          aria-label="System status detail"
        >
          <p className="px-3 pb-1 pt-2 text-[10px] uppercase tracking-wider text-slate-500">
            Runtime
          </p>
          <Row icon={Cpu} label="Device" value={health.device?.toUpperCase()} />
          <Row
            icon={Database}
            label="Indexed frames"
            value={health.indexed_frames?.toLocaleString()}
          />
          <p className="border-t border-ink-700 px-3 pb-1 pt-2 text-[10px] uppercase tracking-wider text-slate-500">
            Models
          </p>
          <Row ok={m.clip} icon={Sparkles} label="CLIP" />
          <Row ok={m.yolo} icon={Boxes} label="YOLOv8" />
          <Row ok={m.face} icon={ScanFace} label="ArcFace" />
        </div>
      )}
    </div>
  );
}
