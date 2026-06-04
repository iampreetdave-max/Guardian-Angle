import { useEffect, useState } from "react";
import { Siren } from "lucide-react";
import * as API from "../../api";

/** Compact header badge: pulses while there are unacknowledged anomaly
 * alerts; clicking jumps to the Live Alerts module. Staff-only (mounted
 * conditionally by the caller). */
export default function AlertTicker({ onOpen }) {
  const [summary, setSummary] = useState({ new: 0, by_type: {} });

  useEffect(() => {
    const refresh = () => API.anomalySummary().then(setSummary).catch(() => {});
    refresh();
    const id = setInterval(refresh, 5000);
    return () => clearInterval(id);
  }, []);

  const active = summary.new > 0;
  return (
    <button
      onClick={onOpen}
      title={
        active
          ? Object.entries(summary.by_type).map(([t, n]) => `${t}: ${n}`).join(" · ")
          : "Anomaly watch — no active alerts"
      }
      className={`relative rounded-lg p-2 transition ${
        active
          ? "bg-signal-red/20 text-signal-red hover:bg-signal-red/30"
          : "bg-ink-700 text-slate-300 hover:bg-ink-600"
      }`}
    >
      <Siren size={16} className={active ? "animate-pulse" : ""} />
      {active && (
        <span className="absolute -right-1 -top-1 flex h-4 min-w-4 items-center justify-center rounded-full bg-signal-red px-1 text-[10px] font-bold text-white">
          {summary.new}
        </span>
      )}
    </button>
  );
}
