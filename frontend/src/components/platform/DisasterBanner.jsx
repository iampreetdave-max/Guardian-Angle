import { useEffect, useState } from "react";
import { TriangleAlert, X, ExternalLink, MapPin } from "lucide-react";
import * as API from "../../api";

const SEV_STYLES = {
  critical: "border-signal-red/50 bg-signal-red/15 text-signal-red",
  high: "border-orange-500/50 bg-orange-500/10 text-orange-400",
  medium: "border-accent/50 bg-accent/10 text-accent",
  low: "border-ink-600 bg-ink-800 text-slate-300",
};

/** City-wide alert banner (disaster broadcasts) — visible to every role.
 * Polls every 30s; locally dismissible except critical alerts, which stay
 * pinned until the admin deactivates the broadcast. */
export default function DisasterBanner() {
  const [broadcasts, setBroadcasts] = useState([]);
  const [hidden, setHidden] = useState(() => new Set());

  useEffect(() => {
    const refresh = () => API.getActiveBroadcasts().then(setBroadcasts).catch(() => {});
    refresh();
    const id = setInterval(refresh, 30000);
    return () => clearInterval(id);
  }, []);

  const visible = broadcasts.filter(
    (b) => b.severity === "critical" || !hidden.has(b.id)
  );
  if (visible.length === 0) return null;

  return (
    <div className="space-y-1 px-3 pt-2 sm:px-5">
      {visible.map((b) => (
        <div
          key={b.id}
          className={`flex items-start gap-2 rounded-lg border px-3 py-2 text-xs ${
            SEV_STYLES[b.severity] || SEV_STYLES.medium
          }`}
        >
          <TriangleAlert size={15} className="mt-0.5 shrink-0 animate-pulse" />
          <div className="min-w-0 flex-1">
            <span className="font-bold uppercase tracking-wide">
              {b.kind === "disaster" ? "Disaster alert" : "Advisory"} · {b.severity}
            </span>
            <span className="mx-1.5 font-semibold">{b.title}</span>
            <span className="text-slate-300">{b.message}</span>
            <span className="ml-2 inline-flex flex-wrap items-center gap-2 text-[10px] opacity-80">
              {b.area && (
                <span className="inline-flex items-center gap-0.5">
                  <MapPin size={10} /> {b.area}
                </span>
              )}
              {b.link && (
                <a href={b.link} target="_blank" rel="noreferrer"
                  className="inline-flex items-center gap-0.5 underline">
                  <ExternalLink size={10} /> details
                </a>
              )}
            </span>
          </div>
          {b.severity !== "critical" && (
            <button
              onClick={() => setHidden((prev) => new Set(prev).add(b.id))}
              className="shrink-0 rounded p-0.5 opacity-70 hover:opacity-100"
              title="Hide"
            >
              <X size={13} />
            </button>
          )}
        </div>
      ))}
    </div>
  );
}
