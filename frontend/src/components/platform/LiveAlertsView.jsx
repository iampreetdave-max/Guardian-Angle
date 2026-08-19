import { useCallback, useEffect, useState } from "react";
import {
  Siren, Flame, Cloud, CarFront, Sword, Swords, Check, X, Inbox, Loader2,
  RadioTower, Layers, Briefcase, AlertTriangle,
} from "lucide-react";
import * as API from "../../api";
import { useT } from "../../i18n";

// Visual identity per anomaly type — icon + Tailwind badge classes + the CSS
// color used to draw the detection box overlay (YOLO signals only).
// Module-level constant, so it stores the i18n KEY; t() is called at render.
const TYPE_META = {
  fire: { icon: Flame, badge: "bg-signal-red/15 text-signal-red border-signal-red/40", labelKey: "alerts.typeFire", box: "#ef4444" },
  smoke: { icon: Cloud, badge: "bg-amber-500/15 text-amber-400 border-amber-500/40", labelKey: "alerts.typeSmoke", box: "#f59e0b" },
  accident: { icon: CarFront, badge: "bg-amber-500/15 text-amber-400 border-amber-500/40", labelKey: "alerts.typeAccident", box: "#f59e0b" },
  weapon: { icon: Sword, badge: "bg-accent/15 text-accent border-accent/40", labelKey: "alerts.typeWeapon", box: "#22d3ee" },
  violence: { icon: Swords, badge: "bg-signal-red/15 text-signal-red border-signal-red/40", labelKey: "alerts.typeViolence", box: "#ef4444" },
};

// A localized box exists only for YOLO signals (CLIP scores the whole frame).
// Coords are stored as 0..1 frame fractions, so we render them as percentages.
function DetectionBox({ alert, color, label }) {
  const { x1, y1, x2, y2 } = alert;
  if ([x1, y1, x2, y2].some((v) => v == null)) return null;
  const left = Math.min(x1, x2) * 100;
  const top = Math.min(y1, y2) * 100;
  const width = Math.abs(x2 - x1) * 100;
  const height = Math.abs(y2 - y1) * 100;
  if (width <= 0 || height <= 0) return null;
  return (
    <div
      className="pointer-events-none absolute rounded-sm"
      style={{
        left: `${left}%`, top: `${top}%`, width: `${width}%`, height: `${height}%`,
        border: `2px solid ${color}`, boxShadow: `0 0 0 1px rgba(0,0,0,0.5)`,
      }}>
      <span
        className="absolute -top-[1px] left-0 -translate-y-full rounded-t-sm px-1 text-[9px] font-bold uppercase leading-tight text-white"
        style={{ backgroundColor: color }}>
        {label}
      </span>
    </div>
  );
}

const TABS = [
  { key: "new", labelKey: "alerts.tabNew" },
  { key: "acknowledged", labelKey: "alerts.tabAcknowledged" },
  { key: "dismissed", labelKey: "alerts.tabDismissed" },
];

function timeAgo(iso, t) {
  if (!iso) return "";
  const sec = Math.max(0, (Date.now() - new Date(iso + "Z").getTime()) / 1000);
  if (sec < 60) return t("alerts.justNow");
  if (sec < 3600) return t("alerts.minsAgo", { n: Math.floor(sec / 60) });
  if (sec < 86400) return t("alerts.hoursAgo", { n: Math.floor(sec / 3600) });
  return t("alerts.daysAgo", { n: Math.floor(sec / 86400) });
}

function AlertCard({ alert, onAck, onDismiss, busy }) {
  const t = useT();
  const meta = TYPE_META[alert.type] || {
    icon: Siren, badge: "bg-ink-700 text-slate-300 border-ink-600",
  };
  const label = meta.labelKey ? t(meta.labelKey) : alert.type;
  const Icon = meta.icon;
  return (
    <div className="overflow-hidden rounded-xl border border-ink-600 bg-ink-800/70 shadow-lg">
      <div className="relative aspect-video bg-ink-900">
        {alert.thumbnail_url ? (
          <img src={alert.thumbnail_url} alt={t("alerts.thumbAlt")}
            className="h-full w-full object-cover" />
        ) : (
          <div className="flex h-full items-center justify-center text-ink-500">
            <Siren size={28} />
          </div>
        )}
        <DetectionBox alert={alert} color={meta.box || "#22d3ee"} label={label} />
        <span className={`absolute left-2 top-2 inline-flex items-center gap-1 rounded-md border px-2 py-0.5 text-[11px] font-bold uppercase tracking-wide ${meta.badge}`}>
          <Icon size={12} /> {label}
        </span>
        {alert.is_live && (
          <span className="absolute right-2 top-2 inline-flex items-center gap-1 rounded-md bg-signal-red px-2 py-0.5 text-[10px] font-bold text-white">
            <RadioTower size={10} /> {t("alerts.live")}
          </span>
        )}
      </div>
      <div className="space-y-1.5 p-3">
        <div className="flex items-center justify-between text-xs">
          <span className="font-semibold text-slate-200">{alert.camera}</span>
          <span className="font-bold text-accent">{Math.round(alert.confidence * 100)}%</span>
        </div>
        <div className="flex items-center gap-2 text-[10px] text-slate-500">
          <span>{timeAgo(alert.created_at, t)}</span>
          <span>· {t("alerts.via")} {alert.source}</span>
          {alert.peak_count > 1 && (
            <span className="inline-flex items-center gap-0.5">
              <Layers size={10} /> {t("alerts.frames", { n: alert.peak_count })}
            </span>
          )}
        </div>
        {alert.case_id && (
          <a href={`/?module=cases&case=${alert.case_id}`}
            className="inline-flex items-center gap-1 rounded-md border border-accent/40 bg-accent/15 px-2 py-0.5 text-[10px] font-bold uppercase tracking-wide text-accent transition hover:bg-accent/25">
            <Briefcase size={10} /> {t("alerts.caseAuto", { id: alert.case_id })}
          </a>
        )}
        {alert.status === "new" && (
          <div className="flex gap-2 pt-1">
            <button onClick={() => onAck(alert.id)} disabled={busy}
              className="inline-flex flex-1 items-center justify-center gap-1 rounded-lg bg-accent-600 px-2 py-1.5 text-xs font-semibold text-white transition hover:bg-accent-700 disabled:opacity-50">
              <Check size={13} /> {t("alerts.acknowledge")}
            </button>
            <button onClick={() => onDismiss(alert.id)} disabled={busy}
              className="inline-flex flex-1 items-center justify-center gap-1 rounded-lg bg-ink-700 px-2 py-1.5 text-xs font-semibold text-slate-300 transition hover:bg-signal-red/20 hover:text-signal-red disabled:opacity-50">
              <X size={13} /> {t("alerts.dismiss")}
            </button>
          </div>
        )}
      </div>
    </div>
  );
}

export default function LiveAlertsView() {
  const t = useT();
  const [tab, setTab] = useState("new");
  const [typeFilter, setTypeFilter] = useState("");
  const [alerts, setAlerts] = useState(null);
  const [error, setError] = useState(null);
  const [busyId, setBusyId] = useState(null);

  const refresh = useCallback(() => {
    API.listAnomalies({
      status_filter: tab,
      ...(typeFilter ? { type: typeFilter } : {}),
    })
      .then((data) => { setAlerts(data); setError(null); })
      // Swallowing this used to leave `alerts` null forever, so a 403, a 500 and
      // a backend still warming up all rendered as the same endless spinner.
      .catch((e) => setError(
        e?.response?.status === 403
          ? t("alerts.errForbidden")
          : t("alerts.errLoad")
      ));
  }, [tab, typeFilter, t]);

  useEffect(() => {
    setAlerts(null);
    setError(null);
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
        <h2 className="font-serif text-xl font-bold text-white">{t("alerts.heading")}</h2>
      </div>
      <p className="mb-4 text-xs text-slate-500">{t("alerts.intro")}</p>

      <div className="mb-4 flex flex-wrap items-center gap-2">
        <div className="flex rounded-lg bg-ink-800 p-1">
          {TABS.map((tb) => (
            <button key={tb.key} onClick={() => setTab(tb.key)}
              className={`rounded-md px-3 py-1.5 text-xs font-semibold transition ${
                tab === tb.key ? "bg-accent-600 text-white" : "text-slate-400 hover:text-slate-200"
              }`}>
              {t(tb.labelKey)}
            </button>
          ))}
        </div>
        <select value={typeFilter} onChange={(e) => setTypeFilter(e.target.value)}
          className="rounded-lg border border-ink-600 bg-ink-800 px-2 py-1.5 text-xs text-slate-300">
          <option value="">{t("alerts.allTypes")}</option>
          {Object.entries(TYPE_META).map(([k, m]) => (
            <option key={k} value={k}>{t(m.labelKey)}</option>
          ))}
        </select>
      </div>

      {alerts === null && error ? (
        <div className="flex flex-col items-center py-20 text-amber-400">
          <AlertTriangle size={28} />
          <p className="mt-3 text-sm">{error}</p>
        </div>
      ) : alerts === null ? (
        <div className="flex flex-col items-center py-20 text-slate-400">
          <Loader2 size={26} className="animate-spin text-accent" />
        </div>
      ) : alerts.length === 0 ? (
        <div className="flex flex-col items-center py-20 text-slate-500">
          <Inbox size={28} />
          <p className="mt-3 text-sm">
            {tab === "new"
              ? t("alerts.emptyNew")
              : t("alerts.emptyOther", {
                  tab: t(TABS.find((tb) => tb.key === tab)?.labelKey || "alerts.tabNew"),
                })}
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
