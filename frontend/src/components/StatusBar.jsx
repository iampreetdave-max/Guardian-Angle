import { Cpu, Database, ScanFace, Boxes, Sparkles } from "lucide-react";

function Pill({ ok, icon: Icon, label }) {
  return (
    <span
      className={`inline-flex items-center gap-1.5 rounded-full px-2.5 py-1 text-xs font-medium ${
        ok ? "bg-signal-green/15 text-signal-green" : "bg-ink-600 text-slate-500"
      }`}
      title={ok ? `${label} online` : `${label} unavailable`}
    >
      <Icon size={13} />
      {label}
    </span>
  );
}

export default function StatusBar({ health }) {
  if (!health) return null;
  const m = health.models || {};
  return (
    <div className="flex flex-wrap items-center gap-2">
      <span className="inline-flex items-center gap-1.5 rounded-full bg-ink-700 px-2.5 py-1 text-xs font-medium text-slate-300">
        <Cpu size={13} className="text-accent" />
        {health.device?.toUpperCase()}
      </span>
      <span className="inline-flex items-center gap-1.5 rounded-full bg-ink-700 px-2.5 py-1 text-xs font-medium text-slate-300">
        <Database size={13} className="text-accent" />
        {health.indexed_frames?.toLocaleString()} frames
      </span>
      <Pill ok={m.clip} icon={Sparkles} label="CLIP" />
      <Pill ok={m.yolo} icon={Boxes} label="YOLOv8" />
      <Pill ok={m.face} icon={ScanFace} label="ArcFace" />
    </div>
  );
}
