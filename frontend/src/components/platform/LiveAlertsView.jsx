import { useCallback, useEffect, useState } from "react";
import {
  Siren, Flame, Cloud, CarFront, Sword, Swords, Check, X, Inbox, Loader2,
  RadioTower, Layers, Briefcase,
} from "lucide-react";
import * as API from "../../api";

// Visual identity per anomaly type — icon + Tailwind badge classes.
const TYPE_META = {
  fire: { icon: Flame, badge: "bg-signal-red/15 text-signal-red border-signal-red/40", label: "Fire" },
  smoke: { icon: Cloud, badge: "bg-amber-500/15 text-amber-400 border-amber-500/40", label: "Smoke" },
  accident: { icon: CarFront, badge: "bg-amber-500/15 text-amber-400 border-amber-500/40", label: "Accident" },
  weapon: { icon: Sword, badge: "bg-accent/15 text-accent border-accent/40", label: "Weapon" },
  violence: { icon: Swords, badge: "bg-signal-red/15 text-signal-red border-signal-red/40", label: "Violence" },
};

const TABS = [
  { key: "new", label: "New" },
  { key: "acknowledged", label: "Acknowledged" },
  { key: "dismissed", label: "Dismissed" },
];

function timeAgo(iso) {
  if (!iso) return "";
  const sec = Math.max(0, (Date.now() - new Date(iso + "Z").getTime()) / 1000);
  if (sec < 60) return "just now";
  if (sec < 3600) return `${Math.floor(sec / 60)}m ago`;
  if (sec < 86400) return `${Math.floor(sec / 3600)}h ago`;
  return `${Math.floor(sec / 86400)}d ago`;
}

function AlertCard({ alert, onAck, onDismiss, busy }) {
  const meta = TYPE_META[alert.type] || {
    icon: Siren, badge: "bg-ink-700 text-slate-300 border-ink-600", label: alert.type,
  };
  const Icon = meta.icon;
  return (
    <div className="overflow-hidden rounded-xl border border-ink-600 bg-ink-800/70 shadow-lg">
      <div className="relative aspect-video bg-ink-900">
        {alert.thumbnail_url ? (
          <img src={alert.thumbnail_url} alt={`${alert.type} alert`}
            className="h-full w-full object-cover" />
        ) : (
          <div className="flex h-full items-center justify-center text-ink-500">
            <Siren size={28} />
          </div>
        )}
        <span className={`absolute left-2 top-2 inline-flex items-center gap-1 rounded-md border px-2 py-0.5 text-[11px] font-bold uppercase tracking-wide ${meta.badge}`}>
          <Icon size={12} /> {meta.label}
        </span>
        {alert.is_live && (
          <span className="absolute right-2 top-2 inline-flex items-center gap-1 rounded-md bg-signal-red px-2 py-0.5 text-[10px] font-bold text-white">
            <RadioTower size={10} /> LIVE
          </span>
        )}
      </div>
      <div className="space-y-1.5 p-3">
        <div className="flex items-center justify-between text-xs">
          <span className="font-semibold text-slate-200">{alert.camera}</span>
          <span className="font-bold text-accent">{Math.round(alert.confidence * 100)}%</span>
        </div>
        <div className="flex items-center gap-2 text-[10px] text-slate-500">
          <span>{timeAgo(alert.created_at)}</span>
          <span>· via {alert.source}</span>
          {alert.peak_count > 1 && (
            <span className="inline-flex items-center gap-0.5">
              <Layers size={10} /> {alert.peak_count} frames
            </span>
          )}
        </div>
        {alert.case_id && (
          <a href={`/?module=cases&case=${alert.case_id}`}
            className="inline-flex items-center gap-1 rounded-md border border-accent/40 bg-accent/15 px-2 py-0.5 text-[10px] font-bold uppercase tracking-wide text-accent transition hover:bg-accent/25">
            <Briefcase size={10} /> Case #{alert.case_id} auto-created
          </a>
        )}
        {alert.status === "new" && (
          <div className="flex gap-2 pt-1">
            <button onClick={() => onAck(alert.id)} disabled={busy}
              className="inline-flex flex-1 items-center justify-center gap-1 rounded-lg bg-accent-600 px-2 py-1.5 text-xs font-semibold text-white transition hover:bg-accent-700 disabled:opacity-50">
              <Check size={13} /> Acknowledge
            </button>
            <button onClick={() => onDismiss(alert.id)} disabled={busy}
              className="inline-flex flex-1 items-center justify-center gap-1 rounded-lg bg-ink-700 px-2 py-1.5 text-xs font-semibold text-slate-300 transition hover:bg-signal-red/20 hover:text-signal-red disabled:opacity-50">
              <X size={13} /> Dismiss
            </button>
          </div>
        )}
      </div>
    </div>
  );
}

export default function LiveAlertsView() {
  const [tab, setTab] = useState("new");
  const [typeFilter, setTypeFilter] = useState("");
  const [alerts, setAlerts] = useState(null);
  const [busyId, setBusyId] = useState(null);

  const refresh = useCallback(() => {
    API.listAnomalies({
      status_filter: tab,
      ...(typeFilter ? { type: typeFilter } : {}),
    })
      .then(setAlerts)
      .catch(() => {});
  }, [tab, typeFilter]);

  useEffect(() => {
    setAlerts(null);
    refresh();
    const id = setInterval(refresh, 5000);
    return () => clearInterval(id);
  }, [refresh]);

  const act = async (fn, id) => {
    setBusyId(id);
    try {
      await fn(id);
      refresh();
    } finally {
      setBusyId(null);
    }
  };

  return (
    <div className="mx-auto max-w-6xl p-4 sm:p-6">
      <div className="mb-1 flex items-center gap-2">
        <Siren className="text-accent" size={20} />
        <h2 className="font-serif text-xl font-bold text-white">Live Alerts</h2>
      </div>
      <p className="mb-4 text-xs text-slate-500">
        The anomaly watch scans every feed for fire, smoke, accidents, weapons
        and violence — incidents are pinned here the moment they are seen.
      </p>

      <div className="mb-4 flex flex-wrap items-center gap-2">
        <div className="flex rounded-lg bg-ink-800 p-1">
          {TABS.map((t) => (
            <button key={t.key} onClick={() => setTab(t.key)}
              className={`rounded-md px-3 py-1.5 text-xs font-semibold transition ${
                tab === t.key ? "bg-accent-600 text-white" : "text-slate-400 hover:text-slate-200"
              }`}>
              {t.label}
            </button>
          ))}
        </div>
        <select value={typeFilter} onChange={(e) => setTypeFilter(e.target.value)}
          className="rounded-lg border border-ink-600 bg-ink-800 px-2 py-1.5 text-xs text-slate-300">
          <option value="">All types</option>
          {Object.entries(TYPE_META).map(([k, m]) => (
            <option key={k} value={k}>{m.label}</option>
          ))}
        </select>
      </div>

      {alerts === null ? (
        <div className="flex flex-col items-center py-20 text-slate-400">
          <Loader2 size={26} className="animate-spin text-accent" />
        </div>
      ) : alerts.length === 0 ? (
        <div className="flex flex-col items-center py-20 text-slate-500">
          <Inbox size={28} />
          <p className="mt-3 text-sm">
            {tab === "new" ? "All clear — no active alerts." : `No ${tab} alerts.`}
          </p>
        </div>
      ) : (
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4">
          {alerts.map((a) => (
            <AlertCard key={a.id} alert={a} busy={busyId === a.id}
              onAck={(id) => act(API.ackAnomaly, id)}
              onDismiss={(id) => act(API.dismissAnomaly, id)} />
          ))}
        </div>
      )}
    </div>
  );
}
