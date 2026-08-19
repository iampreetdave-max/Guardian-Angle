import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import {
  MapContainer, TileLayer, CircleMarker, Polyline, Popup, Tooltip, useMap,
} from "react-leaflet";
import "leaflet/dist/leaflet.css";
import {
  Map as MapIcon, Loader2, Siren, TriangleAlert, Route, X,
  TrendingUp, TrendingDown, Minus, Building2, Brain, Layers, ShieldAlert,
  Info, Target, ChevronDown, ChevronRight, Download, BarChart3, WifiOff,
} from "lucide-react";
import * as API from "../../api";
import { useT, useEnumLabel } from "../../i18n";
import { BarList } from "./charts";

/** City Map — GIS crime intelligence for Ahmedabad.
 *  Layers: Reports (logged complaint/case density) and Risk forecast (the
 *  predictive model's 0-100 hotspot scores + trend). Filters by category and
 *  time window; the patrol planner draws optimized unit routes over the
 *  current top-risk localities. */

// Leaflet sizes itself once at mount; if the flex/grid container is still
// growing to its final height at that moment, only the top strip of tiles
// paints and the rest shows the navy background. invalidateSize() on a
// ResizeObserver (plus a couple of delayed nudges) makes the map fill its box.
function AutoResize() {
  const map = useMap();
  useEffect(() => {
    const fix = () => map.invalidateSize();
    const t1 = setTimeout(fix, 150);
    const t2 = setTimeout(fix, 500);
    let ro;
    if (typeof ResizeObserver !== "undefined") {
      ro = new ResizeObserver(fix);
      ro.observe(map.getContainer());
    }
    window.addEventListener("resize", fix);
    return () => {
      clearTimeout(t1); clearTimeout(t2);
      if (ro) ro.disconnect();
      window.removeEventListener("resize", fix);
    };
  }, [map]);
  return null;
}

const SEV_COLORS = { low: "#22c55e", medium: "#f4b23c", high: "#fb923c", critical: "#ef4444" };
const BAND_COLORS = { low: "#324468", guarded: "#f4b23c", elevated: "#fb923c", high: "#ef4444" };
const UNIT_COLORS = ["#f4b23c", "#38bdf8", "#22c55e", "#a855f7", "#fb7185", "#14b8a6"];
// Distinct violet/purple family for the cyber-fraud layer so it never reads as
// the amber/red crime-density palette.
const CYBER_COLORS = ["#312e6b", "#7c3aed", "#a855f7", "#c084fc"];
// Module-level constant, so it stores i18n KEYS: hooks cannot be called here,
// t(w.key) runs at the render site instead.
const WINDOWS = [
  { key: "citymap.win7", days: 7 }, { key: "citymap.win30", days: 30 },
  { key: "citymap.win90", days: 90 }, { key: "citymap.winAll", days: 0 },
];

const TrendIcon = ({ trend, size = 12 }) =>
  trend === "rising" ? <TrendingUp size={size} className="text-signal-red" />
  : trend === "falling" ? <TrendingDown size={size} className="text-signal-green" />
  : <Minus size={size} className="text-slate-500" />;

function densityStyle(total, max) {
  const t = max > 0 ? Math.min(total / max, 1) : 0;
  const color = t === 0 ? "#324468" : t < 0.4 ? "#f4b23c" : t < 0.75 ? "#fb923c" : "#ef4444";
  return {
    color, fillColor: color,
    fillOpacity: total === 0 ? 0.12 : 0.25 + 0.4 * t,
    weight: total === 0 ? 1 : 2,
    radius: 9 + 16 * t,
  };
}

function riskStyle(score, band) {
  const color = BAND_COLORS[band] || "#324468";
  return {
    color, fillColor: color,
    fillOpacity: 0.15 + 0.5 * (score / 100),
    weight: band === "high" ? 2.5 : 1.5,
    radius: 8 + 18 * (score / 100),
  };
}

// Indian-style currency: ₹1.4 L (lakh) / ₹2.3 Cr (crore) — keeps the popups
// readable for the figures victims actually report.
function formatINR(n) {
  const v = Number(n) || 0;
  if (v >= 1e7) return `₹${(v / 1e7).toFixed(v >= 1e8 ? 0 : 1)} Cr`;
  if (v >= 1e5) return `₹${(v / 1e5).toFixed(v >= 1e6 ? 0 : 1)} L`;
  if (v >= 1e3) return `₹${(v / 1e3).toFixed(0)}K`;
  return `₹${Math.round(v)}`;
}

// Cyber-fraud circle styling. Radius is log-scaled by total ₹ lost; when the
// amounts are all null/0 (synthetic rows predate the column), it falls back to
// victim-count sizing so the layer still renders. `metric` is the chosen size
// driver for this area, `maxLog` the layer-wide max of log1p(metric).
function cyberStyle(metric, maxLog, hasAmount) {
  const t = maxLog > 0 ? Math.min(Math.log1p(Math.max(metric, 0)) / maxLog, 1) : 0;
  const idx = metric === 0 ? 0 : t < 0.4 ? 1 : t < 0.75 ? 2 : 3;
  const color = CYBER_COLORS[idx];
  return {
    color, fillColor: color,
    fillOpacity: metric === 0 ? 0.1 : 0.25 + 0.45 * t,
    weight: metric === 0 ? 1 : 2,
    radius: 8 + 18 * t,
    hasAmount,
  };
}

function SeverityBar({ mix }) {
  const t = useT();
  const total = Object.values(mix).reduce((a, b) => a + b, 0);
  if (!total) return null;
  return (
    <div className="mt-1.5">
      <div className="flex h-1.5 w-full overflow-hidden rounded-full bg-ink-700">
        {Object.entries(SEV_COLORS).map(([sev, color]) =>
          mix[sev] ? <div key={sev} style={{ width: `${(mix[sev] / total) * 100}%`, background: color }} /> : null
        )}
      </div>
      <div className="mt-1 flex flex-wrap gap-x-2 text-[10px] text-slate-400">
        {Object.entries(mix).map(([sev, n]) => (
          <span key={sev}><span style={{ color: SEV_COLORS[sev] }}>●</span> {t(`common.${sev}`)} {n}</span>
        ))}
      </div>
    </div>
  );
}

function HourBars({ data }) {
  const t = useT();
  const max = Math.max(...data.map((d) => d.count), 1);
  return (
    <div className="flex h-16 items-end gap-px">
      {data.map((d) => (
        <div key={d.hour} className="flex-1 rounded-t bg-accent"
          style={{ height: `${(d.count / max) * 100}%`, minHeight: d.count ? 3 : 1, opacity: d.count ? 1 : 0.25 }}
          title={`${String(d.hour).padStart(2, "0")}:00 — ${d.count} ${
            t(d.count === 1 ? "citymap.report" : "citymap.reports")}`} />
      ))}
    </div>
  );
}

// Palette for the score-decomposition stacked bar. Prior = steel, anomaly =
// red; categories cycle through a distinct ramp so each term is legible.
const CONTRIB_PRIOR = "#64748b";
const CONTRIB_ANOMALY = "#ef4444";
const CONTRIB_CATS = ["#f4b23c", "#38bdf8", "#22c55e", "#a855f7", "#fb7185", "#14b8a6", "#f59e0b"];

function prettyCat(c) {
  return String(c || "").replace(/_/g, " ");
}

// Flatten an area's `contributions` object into ordered, colored segments that
// sum to (approximately) the displayed risk_score.
function contributionSegments(contrib, t) {
  if (!contrib) return [];
  const segs = [];
  if (contrib.prior > 0)
    segs.push({ key: "prior", label: t("citymap.segPrior"), value: contrib.prior, color: CONTRIB_PRIOR });
  const cats = Object.entries(contrib.recent_by_category || {})
    .filter(([, v]) => v > 0)
    .sort((a, b) => b[1] - a[1]);
  cats.forEach(([cat, v], i) =>
    segs.push({ key: cat, label: t("citymap.segRecent", { cat: prettyCat(cat) }), value: v, color: CONTRIB_CATS[i % CONTRIB_CATS.length] })
  );
  if (contrib.anomaly_boost > 0)
    segs.push({ key: "anomaly", label: t("citymap.segAnomaly"), value: contrib.anomaly_boost, color: CONTRIB_ANOMALY });
  return segs;
}

// "Why this hotspot?" — a mini stacked bar + plain-English sentence. Used in
// both the map popup and the side-panel row expander.
function WhyHotspot({ area, light = false }) {
  const t = useT();
  const segs = contributionSegments(area.contributions, t);
  const total = segs.reduce((s, x) => s + x.value, 0) || 1;
  // Plain-English: lead with the biggest recent-category driver if present.
  const cats = Object.entries(area.contributions?.recent_by_category || {})
    .filter(([, v]) => v > 0)
    .sort((a, b) => b[1] - a[1]);
  const prior = Math.round(area.contributions?.prior || 0);
  const anomaly = Math.round(area.contributions?.anomaly_boost || 0);
  const topCat = cats[0];
  const sentence =
    t("citymap.whyLead", { score: area.risk_score, prior }) +
    (topCat ? t("citymap.whyCat", { v: Math.round(topCat[1]), cat: prettyCat(topCat[0]) }) : "") +
    (cats.length > 1 ? t("citymap.whyMore", { n: cats.length - 1 }) : "") +
    (anomaly > 0 ? t("citymap.whyAnomaly", { v: anomaly }) : "") +
    t("citymap.whyOver", {
      n: area.n_reports_used || 0,
      noun: t(area.n_reports_used === 1 ? "citymap.report" : "citymap.reports"),
    });
  const muted = light ? "text-slate-600" : "text-slate-400";
  const head = light ? "text-slate-700" : "text-slate-300";
  return (
    <div className="mt-1.5">
      <div className={`mb-1 flex items-center gap-1 text-[10px] font-semibold ${head}`}>
        <Info size={10} /> {t("citymap.whyTitle")}
      </div>
      <div className="flex h-2 w-full overflow-hidden rounded-full bg-ink-700/60">
        {segs.map((s) => (
          <div key={s.key} title={`${s.label}: +${s.value.toFixed(1)}`}
            style={{ width: `${(s.value / total) * 100}%`, background: s.color }} />
        ))}
      </div>
      <div className="mt-1 flex flex-wrap gap-x-2 gap-y-0.5">
        {segs.slice(0, 5).map((s) => (
          <span key={s.key} className={`text-[9px] ${muted}`}>
            <span style={{ color: s.color }}>●</span> {s.label} {Math.round(s.value)}
          </span>
        ))}
      </div>
      <p className={`mt-1 text-[10px] leading-snug ${muted}`}>{sentence}</p>
    </div>
  );
}

// Small ⓘ model-card popover: published weights, half-life, last computed_at,
// reports used. Toggled inline so it works inside the (non-portaled) side panel.
function ModelCard({ model }) {
  const [open, setOpen] = useState(false);
  const t = useT();
  if (!model) return null;
  const fmtTime = (t) => {
    if (!t) return "—";
    const d = new Date(t);
    return Number.isNaN(d.getTime()) ? t : d.toLocaleString();
  };
  const sevTop = Object.entries(model.category_weights || {})
    .sort((a, b) => b[1] - a[1]).slice(0, 5);
  return (
    <span className="relative">
      <button onClick={() => setOpen((v) => !v)} title={t("citymap.modelCard")}
        className="inline-flex items-center text-slate-500 hover:text-accent">
        <Info size={12} />
      </button>
      {open && (
        <div className="absolute right-0 z-[1000] mt-1 w-64 rounded-lg border border-ink-600 bg-ink-900 p-3 text-[10px] leading-relaxed text-slate-300 shadow-xl">
          <div className="mb-1 font-semibold text-slate-100">{t("citymap.modelCardTitle")}</div>
          <div className="text-slate-500">{model.formula}</div>
          <div className="mt-2 grid grid-cols-2 gap-x-2 gap-y-0.5">
            <span className="text-slate-500">{t("citymap.halfLife")}</span>
            <span className="text-right tabular-nums">{t("citymap.days", { n: model.half_life_days })}</span>
            <span className="text-slate-500">{t("citymap.trendWindow")}</span>
            <span className="text-right tabular-nums">{t("citymap.days", { n: model.trend_window_days })}</span>
            <span className="text-slate-500">{t("citymap.anomalyBoost")}</span>
            <span className="text-right tabular-nums">×{model.anomaly_boost}</span>
            <span className="text-slate-500">{t("citymap.reportsUsed")}</span>
            <span className="text-right tabular-nums">
              {(model.n_reports_used ?? 0).toLocaleString()}
            </span>
          </div>
          {sevTop.length > 0 && (
            <div className="mt-2">
              <div className="text-slate-500">{t("citymap.topWeights")}</div>
              <div className="mt-0.5 flex flex-wrap gap-x-2">
                {sevTop.map(([c, w]) => (
                  <span key={c}>{prettyCat(c)} ×{w}</span>
                ))}
              </div>
            </div>
          )}
          <div className="mt-2 border-t border-ink-700 pt-1 text-slate-500">
            {t("citymap.recomputed", { n: (model.n_reports_used ?? 0).toLocaleString() })}{" "}
            {fmtTime(model.computed_at)}
          </div>
        </div>
      )}
    </span>
  );
}

// Tiny labelled horizontal bar for the capture curve / comparison rows.
function MiniBar({ label, pct, value, color = "#f4b23c", sub }) {
  return (
    <div className="flex items-center gap-2">
      <span className="w-14 shrink-0 truncate text-[10px] text-slate-400" title={label}>{label}</span>
      <div className="h-3 flex-1 overflow-hidden rounded bg-ink-900/70">
        <div className="h-full rounded" style={{ width: `${Math.max(0, Math.min(pct, 100))}%`, background: color, minWidth: pct ? "3px" : 0 }} />
      </div>
      <span className="w-10 shrink-0 text-right text-[10px] font-semibold tabular-nums text-slate-300">{value}</span>
      {sub && <span className="w-8 shrink-0 text-right text-[9px] text-slate-600">{sub}</span>}
    </div>
  );
}

// Collapsible accuracy panel — LEADS with surge detection (the strongest,
// judge-friendly result), then capture curve, then HR@10/PAI@10 vs the oracle
// ceiling, plus the API's own disclaimer string.
function AccuracyPanel({ data, loading }) {
  const [open, setOpen] = useState(false);
  const t = useT();
  const model = data?.model;
  const summary = model?.summary || {};
  const surges = data?.surge_detection || [];
  const caught = surges.filter((s) => s.in_top10_during);
  // Best single surge story (largest rank improvement) for the headline line.
  const bestSurge = [...surges]
    .filter((s) => s.rank_improvement != null)
    .sort((a, b) => (b.rank_improvement || 0) - (a.rank_improvement || 0))[0];
  const curve = model?.capture_curve || [];
  const cap10 = curve.length >= 10 ? Math.round(curve[9] * 100) : null;
  const hr10 = summary["hit_rate@10"];
  const pai10 = summary["pai@10"];
  const oracle10 = (data?.oracle_pai || {})["10"] ?? (data?.oracle_pai || {})[10];
  const pctOfCeiling =
    pai10 && oracle10 ? Math.round((pai10 / oracle10) * 100) : null;
  const compare = data?.comparison || [];

  return (
    <div className="rounded-xl border border-accent/30 bg-ink-800/70 p-3">
      <button onClick={() => setOpen((v) => !v)}
        className="flex w-full items-center gap-1.5 text-xs font-semibold text-slate-200">
        <Target size={13} className="text-accent" /> {t("citymap.accuracy")}
        {open ? <ChevronDown size={13} className="ml-auto text-slate-500" />
              : <ChevronRight size={13} className="ml-auto text-slate-500" />}
      </button>

      {!open && surges.length > 0 && (
        <div className="mt-1.5 text-[10px] text-slate-400">
          {t("citymap.caughtPre")}
          <b className="text-signal-green">{caught.length}/{surges.length}</b>
          {t("citymap.caughtPost")}
        </div>
      )}

      {open && (
        <div className="mt-2 space-y-3">
          {loading && !data && (
            <div className="flex items-center gap-2 py-3 text-[11px] text-slate-500">
              <Loader2 size={13} className="animate-spin text-accent" /> {t("citymap.backtesting")}
            </div>
          )}

          {data && (
            <>
              {/* 1. Surge detection — lead with the strongest result */}
              <div className="rounded-lg bg-signal-green/10 p-2 ring-1 ring-signal-green/20">
                <div className="flex items-center gap-1.5 text-[11px] font-semibold text-signal-green">
                  <Siren size={12} /> {t("citymap.caughtWaves", { n: caught.length, m: surges.length })}
                </div>
                {bestSurge && bestSurge.rank_before_surge && bestSurge.rank_during_surge && (
                  <p className="mt-1 text-[10px] leading-snug text-slate-300">
                    {t("citymap.surgePre", { area: bestSurge.area })}{" "}
                    <b>{bestSurge.rank_before_surge}→{bestSurge.rank_during_surge}</b>{" "}
                    {t("citymap.surgePost", { cat: prettyCat(bestSurge.category) })}
                  </p>
                )}
              </div>

              {/* 2. Capture curve */}
              {curve.length > 0 && (
                <div>
                  <div className="mb-1 flex items-center gap-1 text-[10px] font-semibold text-slate-300">
                    <BarChart3 size={11} className="text-accent" /> {t("citymap.captureCurve")}
                  </div>
                  {cap10 != null && (
                    <p className="mb-1 text-[10px] text-slate-400">
                      {t("citymap.top10Pre")} <b className="text-accent">{cap10}%</b>{" "}
                      {t("citymap.top10Post")}
                    </p>
                  )}
                  <div className="space-y-1">
                    {[3, 5, 10].filter((k) => curve.length >= k).map((k) => (
                      <MiniBar key={k} label={t("citymap.topK", { k })}
                        pct={curve[k - 1] * 100}
                        value={`${Math.round(curve[k - 1] * 100)}%`} />
                    ))}
                  </div>
                </div>
              )}

              {/* 3. HR@10 + PAI@10 vs oracle ceiling */}
              <div className="grid grid-cols-2 gap-2 text-center">
                <div className="rounded-lg bg-ink-900/50 p-2">
                  <div className="text-base font-bold tabular-nums text-white">
                    {hr10 != null ? hr10.toFixed(2) : "—"}
                  </div>
                  <div className="text-[9px] text-slate-500">Hit-Rate@10</div>
                </div>
                <div className="rounded-lg bg-ink-900/50 p-2">
                  <div className="text-base font-bold tabular-nums text-white">
                    {pai10 != null ? `${pai10.toFixed(2)}×` : "—"}
                  </div>
                  <div className="text-[9px] text-slate-500">
                    PAI@10{oracle10 ? t("citymap.ofCeiling", { x: oracle10.toFixed(2) }) : ""}
                  </div>
                </div>
              </div>
              {pctOfCeiling != null && (
                <div>
                  <MiniBar label={t("citymap.vsOracle")} pct={pctOfCeiling}
                    value={`${pctOfCeiling}%`} color="#22c55e" />
                  <p className="mt-1 text-[9px] leading-snug text-slate-500">
                    {t("citymap.ceilingNote", {
                      pai: pai10.toFixed(2),
                      oracle: oracle10.toFixed(2),
                      pct: pctOfCeiling,
                    })}
                  </p>
                </div>
              )}

              {/* baseline comparison */}
              {compare.length > 0 && (
                <div>
                  <div className="mb-1 text-[10px] font-semibold text-slate-300">{t("citymap.vsBaselines")}</div>
                  <div className="space-y-1">
                    {compare.map((row) => (
                      <MiniBar key={row.strategy} label={row.strategy}
                        pct={(row["pai@10"] || 0) / Math.max(oracle10 || 1, 1) * 100}
                        value={`${(row["pai@10"] || 0).toFixed(2)}×`}
                        color={row.strategy === "model" ? "#f4b23c" : "#475569"} />
                    ))}
                  </div>
                </div>
              )}

              {data.disclaimer && (
                <p className="border-t border-ink-700 pt-2 text-[9px] leading-snug text-slate-500">
                  {data.disclaimer}
                </p>
              )}
            </>
          )}
        </div>
      )}
    </div>
  );
}

export default function CityMapView() {
  const enumLabel = useEnumLabel();
  const t = useT();
  const [layer, setLayer] = useState("reports"); // reports | risk | cyber
  const [category, setCategory] = useState("");
  const [days, setDays] = useState(0);
  const [data, setData] = useState(null);        // /analytics/map
  const [cyber, setCyber] = useState(null);      // /analytics/map/cyber
  const [risk, setRisk] = useState(null);        // /predict/risk
  const [temporal, setTemporal] = useState(null);
  const [routes, setRoutes] = useState(null);    // patrol plan, null = hidden
  const [units, setUnits] = useState(2);
  const [planning, setPlanning] = useState(false);
  const [validation, setValidation] = useState(null); // /predict/validation
  const [valLoading, setValLoading] = useState(false);
  const [expanded, setExpanded] = useState(null);  // area name with open "why"
  const [exporting, setExporting] = useState(null); // export kind in flight
  const [tilesOffline, setTilesOffline] = useState(false); // OSM tiles failing

  // Tile-resilience: count tile loads vs errors (refs so counting never
  // re-renders the map). When >25% of attempted tiles error, surface a small
  // offline notice — the data layers (circles/routes) keep rendering over the
  // navy MapContainer background regardless of basemap availability.
  const tileStats = useRef({ ok: 0, err: 0 });
  const onTileLoad = useCallback(() => {
    tileStats.current.ok += 1;
  }, []);
  const onTileError = useCallback(() => {
    const s = tileStats.current;
    s.err += 1;
    const attempted = s.ok + s.err;
    if (attempted >= 8 && s.err / attempted > 0.25) setTilesOffline(true);
  }, []);

  const refresh = useCallback(() => {
    const params = {};
    if (category) params.category = category;
    if (days) params.days = days;
    API.getMapData(params).then(setData).catch(() => {});
    API.getRiskScores().then(setRisk).catch(() => {});
    API.getTemporal().then(setTemporal).catch(() => {});
    // Cyber layer has its own lookback (defaults to 90 days when the shared
    // selector is on "All time", so the headline always reads a window).
    API.getCyberMapData({ days: days || 90 }).then(setCyber).catch(() => {});
  }, [category, days]);

  // Backtest accuracy is expensive (a few seconds, server-cached ~10 min) and
  // independent of the filters, so fetch it once on mount, not on every refresh.
  useEffect(() => {
    setValLoading(true);
    API.getValidation({ compare: true, folds: 8 })
      .then(setValidation)
      .catch(() => {})
      .finally(() => setValLoading(false));
  }, []);

  // Download a CSV export (officer-gated) via the shared blob pattern.
  const exportCsv = async (kind, filename) => {
    setExporting(kind);
    try {
      const blob = await API.fetchExportBlob(kind);
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = filename;
      document.body.appendChild(a);
      a.click();
      a.remove();
      URL.revokeObjectURL(url);
    } catch {
      /* permission / backend hiccup — silently no-op, button re-enables */
    } finally {
      setExporting(null);
    }
  };

  useEffect(() => {
    refresh();
    const id = setInterval(refresh, 30000);
    return () => clearInterval(id);
  }, [refresh]);

  const maxLoad = useMemo(
    () => (data ? Math.max(1, ...data.areas.map((a) => a.complaints + a.cases)) : 1),
    [data]
  );
  const riskByArea = useMemo(() => {
    const m = new Map();
    risk?.areas?.forEach((a) => m.set(a.area, a));
    return m;
  }, [risk]);

  // Cyber sizing: drive the circle radius by ₹ lost when any amounts exist,
  // otherwise fall back to victim count (synthetic rows have NULL amounts).
  const cyberSizing = useMemo(() => {
    const areas = cyber?.areas || [];
    const hasAmount = areas.some((a) => (a.total_amount_lost || 0) > 0);
    const metricOf = (a) =>
      hasAmount ? a.total_amount_lost || 0 : a.victim_count || 0;
    const maxLog = Math.max(
      0.0001,
      ...areas.map((a) => Math.log1p(Math.max(metricOf(a), 0)))
    );
    return { hasAmount, metricOf, maxLog };
  }, [cyber]);

  const planRoutes = async () => {
    setPlanning(true);
    try {
      setRoutes(await API.getPatrolRoutes({ units }));
    } catch {
      /* permissions / backend hiccup — leave planner closed */
    } finally {
      setPlanning(false);
    }
  };

  if (!data || !risk) {
    return (
      <div className="flex flex-col items-center py-24 text-slate-400">
        <Loader2 size={26} className="animate-spin text-accent" />
        <p className="mt-3 text-sm">{t("citymap.loading")}</p>
      </div>
    );
  }

  const totals = data.areas.reduce(
    (acc, a) => ({
      complaints: acc.complaints + a.complaints,
      cases: acc.cases + a.cases,
      anomalies: acc.anomalies + a.anomalies,
    }),
    { complaints: 0, cases: 0, anomalies: 0 }
  );
  const top5 = risk.areas.slice(0, 5);
  // Effective cyber lookback (mirrors the getCyberMapData call: 90 when the
  // shared selector is on "All time").
  const cyberWindowDays = days || 90;

  return (
    <div className="flex h-full flex-col p-4 sm:p-6">
      <div className="mb-1 flex items-center gap-2">
        <MapIcon className="text-accent" size={20} />
        <h2 className="font-serif text-xl font-bold text-white">{t("citymap.title")}</h2>
      </div>
      <p className="mb-3 text-xs text-slate-500">
        {layer === "reports"
          ? t("citymap.subReports", {
              c: totals.complaints, k: totals.cases, a: totals.anomalies,
            })
          : layer === "cyber"
          ? t("citymap.subCyber")
          : t("citymap.subRisk")}
      </p>

      {/* control bar */}
      <div className="mb-3 flex flex-wrap items-center gap-2 text-xs">
        <div className="flex rounded-lg bg-ink-800 p-1">
          <button onClick={() => setLayer("reports")}
            className={`inline-flex items-center gap-1.5 rounded-md px-3 py-1.5 font-semibold transition ${
              layer === "reports" ? "bg-accent-600 text-white" : "text-slate-400 hover:text-slate-200"}`}>
            <Layers size={13} /> {t("citymap.layerReports")}
          </button>
          <button onClick={() => setLayer("risk")}
            className={`inline-flex items-center gap-1.5 rounded-md px-3 py-1.5 font-semibold transition ${
              layer === "risk" ? "bg-accent-600 text-white" : "text-slate-400 hover:text-slate-200"}`}>
            <Brain size={13} /> {t("citymap.layerRisk")}
          </button>
          <button onClick={() => setLayer("cyber")}
            className={`inline-flex items-center gap-1.5 rounded-md px-3 py-1.5 font-semibold transition ${
              layer === "cyber" ? "bg-violet-600 text-white" : "text-slate-400 hover:text-slate-200"}`}>
            <ShieldAlert size={13} /> {t("citymap.layerCyber")}
          </button>
        </div>

        {layer === "reports" && (
          <>
            <select value={category} onChange={(e) => setCategory(e.target.value)}
              className="rounded-lg border border-ink-600 bg-ink-800 px-2 py-1.5 text-slate-300">
              <option value="">{t("citymap.allCategories")}</option>
              {(data.categories || []).map((c) => (
                <option key={c} value={c}>{enumLabel("category", c)}</option>
              ))}
            </select>
            <select value={days} onChange={(e) => setDays(Number(e.target.value))}
              className="rounded-lg border border-ink-600 bg-ink-800 px-2 py-1.5 text-slate-300">
              {WINDOWS.map((w) => <option key={w.days} value={w.days}>{t(w.key)}</option>)}
            </select>
          </>
        )}

        {layer === "cyber" && cyber && (
          <>
            <select value={days} onChange={(e) => setDays(Number(e.target.value))}
              className="rounded-lg border border-ink-600 bg-ink-800 px-2 py-1.5 text-slate-300">
              {WINDOWS.filter((w) => w.days > 0).map((w) => (
                <option key={w.days} value={w.days}>{t(w.key)}</option>
              ))}
            </select>
            <span className="inline-flex items-center gap-1.5 rounded-lg bg-violet-600/15 px-3 py-1.5 font-semibold text-violet-200 ring-1 ring-violet-500/30">
              <ShieldAlert size={13} className="text-violet-300" />
              {t("citymap.cyberChip", {
                amount: formatINR(cyber.citywide.total_amount_lost),
                victims: cyber.citywide.total_victims,
                days: cyberWindowDays,
              })}
            </span>
          </>
        )}

        <div className="ml-auto flex items-center gap-2">
          {routes ? (
            <button onClick={() => setRoutes(null)}
              className="inline-flex items-center gap-1.5 rounded-lg bg-ink-700 px-3 py-1.5 font-semibold text-slate-300 hover:text-white">
              <X size={13} /> {t("citymap.clearRoutes")}
            </button>
          ) : (
            <>
              <select value={units} onChange={(e) => setUnits(Number(e.target.value))}
                title={t("citymap.unitsAvailable")}
                className="rounded-lg border border-ink-600 bg-ink-800 px-2 py-1.5 text-slate-300">
                {[1, 2, 3, 4].map((n) => (
                  <option key={n} value={n}>
                    {n} {t(n > 1 ? "citymap.unitWords" : "citymap.unitWord")}
                  </option>
                ))}
              </select>
              <button onClick={planRoutes} disabled={planning}
                className="inline-flex items-center gap-1.5 rounded-lg bg-accent-600 px-3 py-1.5 font-semibold text-white hover:bg-accent-700 disabled:opacity-50">
                {planning ? <Loader2 size={13} className="animate-spin" /> : <Route size={13} />}{" "}
                {t("citymap.planRoutes")}
              </button>
            </>
          )}
        </div>
      </div>

      <div className="grid min-h-0 flex-1 gap-3 lg:grid-cols-[1fr_280px]">
        {/* map */}
        <div className="relative min-h-[460px] overflow-hidden rounded-xl border border-ink-600">
          {tilesOffline && (
            <div className="pointer-events-none absolute left-1/2 top-3 z-[1000] -translate-x-1/2">
              <span className="inline-flex items-center gap-1.5 rounded-full bg-ink-900/90 px-3 py-1.5 text-[11px] font-semibold text-amber-200 shadow-lg ring-1 ring-amber-500/40">
                <WifiOff size={12} className="text-amber-300" />
                {t("citymap.tilesOffline")}
              </span>
            </div>
          )}
          <MapContainer center={[data.center.lat, data.center.lng]} zoom={12} scrollWheelZoom
            // Tame zoom sensitivity: half-step zoom + far more scroll needed per
            // level, so a small trackpad scroll nudges instead of leaping levels.
            zoomSnap={0.5} zoomDelta={0.5} wheelPxPerZoomLevel={220} wheelDebounceTime={80}
            minZoom={10} maxZoom={17}
            style={{ height: "100%", width: "100%", minHeight: 460, background: "#0a1124" }}>
            <AutoResize />
            <TileLayer
              attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
              url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
              // A transparent 1x1 PNG for failed tiles -> the navy MapContainer
              // background shows through instead of broken-image gray. The data
              // layers (circles/routes) stay fully visible offline.
              errorTileUrl="data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNkYPhfDwAChwGA60e6kgAAAABJRU5ErkJggg=="
              eventHandlers={{ tileload: onTileLoad, tileerror: onTileError }}
            />

            {layer === "reports" && data.areas.map((a) => {
              const total = a.complaints + a.cases;
              const style = densityStyle(total, maxLoad);
              const r = riskByArea.get(a.area);
              return (
                <CircleMarker key={a.area} center={[a.lat, a.lng]} pathOptions={style} radius={style.radius}>
                  <Tooltip direction="top" opacity={0.9}>
                    <span className="text-xs font-semibold">
                      {a.area}: {total}{" "}
                      {t(total === 1 ? "citymap.report" : "citymap.reports")}
                      {a.anomalies > 0 ? " · ⚠" : ""}
                    </span>
                  </Tooltip>
                  <Popup>
                    <div className="min-w-[190px] text-xs">
                      <div className="mb-1 text-sm font-bold">{a.area}</div>
                      <div className="space-y-0.5">
                        <div>{t("citymap.complaints")}: <b>{a.complaints}</b> · {t("citymap.cases")}: <b>{a.cases}</b></div>
                        {a.top_category && <div>{t("citymap.topCategory")}: <b>{enumLabel("category", a.top_category)}</b></div>}
                        {r && (
                          <div className="flex items-center gap-1">
                            {t("citymap.risk")}: <b style={{ color: BAND_COLORS[r.risk_band] }}>{r.risk_score}</b>
                            <TrendIcon trend={r.trend} />
                          </div>
                        )}
                        {a.anomalies > 0 && (
                          <div className="flex items-center gap-1 font-semibold text-red-600">
                            <Siren size={12} /> {a.anomalies}{" "}
                            {t(a.anomalies === 1 ? "citymap.anomalyAlert" : "citymap.anomalyAlerts")}
                          </div>
                        )}
                      </div>
                      <SeverityBar mix={a.by_severity} />
                    </div>
                  </Popup>
                </CircleMarker>
              );
            })}

            {layer === "risk" && risk.areas.map((a) => {
              const style = riskStyle(a.risk_score, a.risk_band);
              return (
                <CircleMarker key={a.area} center={[a.lat, a.lng]} pathOptions={style} radius={style.radius}>
                  <Tooltip direction="top" opacity={0.9}>
                    <span className="text-xs font-semibold">
                      {t("citymap.riskTooltip", {
                        area: a.area, score: a.risk_score,
                        band: t(`citymap.band.${a.risk_band}`),
                      })}
                    </span>
                  </Tooltip>
                  <Popup>
                    <div className="min-w-[190px] text-xs">
                      <div className="mb-1 text-sm font-bold">{a.area}</div>
                      <div className="space-y-0.5">
                        <div>{t("citymap.riskScore")}: <b style={{ color: BAND_COLORS[a.risk_band] }}>{a.risk_score} ({t(`citymap.band.${a.risk_band}`)})</b></div>
                        <div className="flex items-center gap-1">
                          {t("citymap.forecast")}: <b style={{ color: BAND_COLORS[a.predicted_band] }}>{a.predicted_score}</b>
                          <TrendIcon trend={a.trend} /> {t(`citymap.trend.${a.trend}`)}
                        </div>
                        {a.active_anomalies > 0 && (
                          <div className="flex items-center gap-1 font-semibold text-red-600">
                            <Siren size={12} /> {a.active_anomalies}{" "}
                            {t(a.active_anomalies === 1 ? "citymap.anomalySignal" : "citymap.anomalySignals")}
                          </div>
                        )}
                      </div>
                      <WhyHotspot area={a} light />
                    </div>
                  </Popup>
                </CircleMarker>
              );
            })}

            {layer === "cyber" && cyber?.areas?.map((a) => {
              const metric = cyberSizing.metricOf(a);
              const style = cyberStyle(metric, cyberSizing.maxLog, cyberSizing.hasAmount);
              if (a.victim_count === 0) return null;
              return (
                <CircleMarker key={a.area} center={[a.lat, a.lng]} pathOptions={style} radius={style.radius}>
                  <Tooltip direction="top" opacity={0.9}>
                    <span className="text-xs font-semibold">
                      {a.area}: {a.victim_count}{" "}
                      {t(a.victim_count === 1 ? "citymap.victim" : "citymap.victims")}
                      {style.hasAmount ? ` · ${formatINR(a.total_amount_lost)}` : ""}
                    </span>
                  </Tooltip>
                  <Popup>
                    <div className="min-w-[200px] text-xs">
                      <div className="mb-1 flex items-center gap-1 text-sm font-bold">
                        <span style={{ color: "#7c3aed" }}>◆</span> {a.area}
                      </div>
                      <div className="space-y-0.5">
                        {a.top_category_label && (
                          <div>{t("citymap.topFraudType")}: <b>{a.top_category_label}</b></div>
                        )}
                        <div>{t("citymap.victimsLabel")}: <b>{a.victim_count}</b></div>
                        <div>
                          {t("citymap.totalAmount")}: <b style={{ color: "#7c3aed" }}>
                            {style.hasAmount ? formatINR(a.total_amount_lost) : "—"}
                          </b>
                        </div>
                        {Object.keys(a.fraud_channels || {}).length > 0 && (
                          <div className="text-slate-600">
                            {t("citymap.via")} {Object.entries(a.fraud_channels)
                              .sort((x, y) => y[1] - x[1])
                              .map(([ch, n]) => `${ch.replace(/_/g, " ")} (${n})`)
                              .join(", ")}
                          </div>
                        )}
                      </div>
                    </div>
                  </Popup>
                </CircleMarker>
              );
            })}

            {/* patrol plan overlay */}
            {routes?.routes?.map((rt) => {
              const color = UNIT_COLORS[(rt.unit - 1) % UNIT_COLORS.length];
              const path = [
                [routes.station.lat, routes.station.lng],
                ...rt.waypoints.map((w) => [w.lat, w.lng]),
              ];
              return (
                <Polyline key={rt.unit} positions={path}
                  pathOptions={{ color, weight: 3, opacity: 0.85, dashArray: "6 6" }}>
                  <Tooltip sticky>
                    <span className="text-xs font-semibold">
                      {t("citymap.unitTooltip", {
                        n: rt.unit, km: rt.distance_km, min: rt.eta_min,
                      })}
                    </span>
                  </Tooltip>
                </Polyline>
              );
            })}
            {routes && (
              <CircleMarker center={[routes.station.lat, routes.station.lng]}
                pathOptions={{ color: "#ffffff", fillColor: "#0a1124", fillOpacity: 1, weight: 2 }} radius={7}>
                <Tooltip direction="top"><span className="text-xs font-semibold">{routes.station.name}</span></Tooltip>
              </CircleMarker>
            )}
          </MapContainer>
        </div>

        {/* intelligence side panel */}
        <div className="space-y-3 overflow-y-auto">
          {layer === "cyber" && cyber && (
            <div className="rounded-xl border border-violet-500/30 bg-violet-950/30 p-3">
              <div className="mb-2 flex items-center gap-1.5 text-xs font-semibold text-violet-100">
                <ShieldAlert size={13} className="text-violet-300" /> {t("citymap.topChannels")}
              </div>
              {(() => {
                const ch = cyber.citywide.top_channels || [];
                const max = Math.max(...ch.map((c) => c.count), 1);
                if (!ch.length)
                  return <p className="py-3 text-center text-xs text-slate-500">{t("citymap.noChannelData")}</p>;
                return (
                  <div className="space-y-2">
                    {ch.map((c) => (
                      <div key={c.label} className="flex items-center gap-2">
                        <span className="w-20 shrink-0 truncate text-xs capitalize text-slate-400" title={c.label}>
                          {enumLabel("category", c.label)}
                        </span>
                        <div className="h-4 flex-1 overflow-hidden rounded bg-ink-900/70">
                          <div className="h-full rounded"
                            style={{ width: `${(c.count / max) * 100}%`, backgroundColor: "#a855f7", minWidth: c.count ? "4px" : 0 }} />
                        </div>
                        <span className="w-8 shrink-0 text-right text-xs font-semibold tabular-nums text-slate-300">
                          {c.count}
                        </span>
                      </div>
                    ))}
                  </div>
                );
              })()}
              <div className="mt-3 border-t border-violet-500/20 pt-2 text-[10px] leading-snug text-violet-300/80">
                {t("citymap.subCyber")}
              </div>
            </div>
          )}

          <AccuracyPanel data={validation} loading={valLoading} />

          <div className="rounded-xl border border-ink-600 bg-ink-800/70 p-3">
            <div className="mb-2 flex items-center gap-1.5 text-xs font-semibold text-slate-200">
              <Brain size={13} className="text-accent" /> {t("citymap.topHotspots")}
              <ModelCard model={risk.model} />
              <button onClick={() => exportCsv("risk.csv", "risk-table.csv")}
                disabled={exporting === "risk.csv"}
                title={t("citymap.exportRiskCsv")}
                className="ml-auto inline-flex items-center gap-1 rounded bg-ink-700 px-1.5 py-1 text-[10px] font-semibold text-slate-300 hover:text-white disabled:opacity-50">
                {exporting === "risk.csv"
                  ? <Loader2 size={11} className="animate-spin" />
                  : <Download size={11} />}{" "}
                {t("citymap.exportCsv")}
              </button>
            </div>
            <div className="space-y-1">
              {top5.map((a, i) => {
                const isOpen = expanded === a.area;
                return (
                  <div key={a.area} className="rounded-md bg-ink-900/40 px-2 py-1.5 text-xs">
                    <button
                      onClick={() => setExpanded(isOpen ? null : a.area)}
                      className="flex w-full items-center gap-2 text-left">
                      {isOpen ? <ChevronDown size={12} className="text-slate-500" />
                              : <ChevronRight size={12} className="text-slate-600" />}
                      <span className="w-3 text-slate-600">{i + 1}</span>
                      <span className="flex-1 truncate font-medium text-slate-200">{a.area}</span>
                      <TrendIcon trend={a.trend} />
                      <span className="rounded px-1.5 py-0.5 text-[10px] font-bold"
                        style={{ color: BAND_COLORS[a.risk_band], background: `${BAND_COLORS[a.risk_band]}22` }}>
                        {a.risk_score}
                      </span>
                    </button>
                    {isOpen && <WhyHotspot area={a} />}
                  </div>
                );
              })}
            </div>
          </div>

          {routes?.routes?.length > 0 && (
            <div className="rounded-xl border border-ink-600 bg-ink-800/70 p-3">
              <div className="mb-2 flex items-center gap-1.5 text-xs font-semibold text-slate-200">
                <Route size={13} className="text-accent" /> {t("citymap.patrolPlan")}
                <button onClick={() => exportCsv(`patrol-plan.csv?units=${units}`, "patrol-plan.csv")}
                  disabled={exporting === `patrol-plan.csv?units=${units}`}
                  title={t("citymap.exportPatrolCsv")}
                  className="ml-auto inline-flex items-center gap-1 rounded bg-ink-700 px-1.5 py-1 text-[10px] font-semibold text-slate-300 hover:text-white disabled:opacity-50">
                  {exporting === `patrol-plan.csv?units=${units}`
                    ? <Loader2 size={11} className="animate-spin" />
                    : <Download size={11} />}{" "}
                  {t("citymap.exportCsv")}
                </button>
                <span className="inline-flex items-center gap-1 text-[10px] text-slate-500">
                  <Building2 size={10} /> {routes.station.name}
                </span>
              </div>
              {routes.routes.map((rt) => {
                const color = UNIT_COLORS[(rt.unit - 1) % UNIT_COLORS.length];
                return (
                  <div key={rt.unit} className="mb-2 rounded-md bg-ink-900/40 p-2 text-xs">
                    <div className="mb-1 flex items-center gap-1.5 font-semibold" style={{ color }}>
                      {t("citymap.unitLabel", { n: rt.unit })}
                      <span className="ml-auto font-normal text-slate-500">
                        {t("citymap.routeStats", { km: rt.distance_km, min: rt.eta_min })}
                      </span>
                    </div>
                    <div className="text-slate-400">
                      {rt.waypoints.map((w, i) => (
                        <span key={w.area}>
                          {i > 0 && <span className="text-slate-600"> → </span>}
                          {w.area}
                        </span>
                      ))}
                    </div>
                  </div>
                );
              })}
            </div>
          )}

          {temporal && (
            <div className="rounded-xl border border-ink-600 bg-ink-800/70 p-3">
              <div className="mb-2 text-xs font-semibold text-slate-200">{t("citymap.byHour")}</div>
              <HourBars data={temporal.by_hour} />
              <div className="mt-1 flex justify-between text-[9px] text-slate-600">
                <span>00:00</span><span>12:00</span><span>23:00</span>
              </div>
              <div className="mb-2 mt-3 text-xs font-semibold text-slate-200">{t("citymap.byDay")}</div>
              <BarList data={temporal.by_day.map((d) => ({ label: d.day, count: d.count }))} />
            </div>
          )}
        </div>
      </div>

      <div className="mt-2 flex items-start gap-2 text-[10px] leading-snug text-slate-500">
        <TriangleAlert size={12} className="mt-0.5 shrink-0 text-accent" />
        <span>
          {t("citymap.disclaimer")}{" "}
          <code className="text-slate-400">docs/AHMEDABAD_CRIME_DATA.md</code>).
        </span>
      </div>
    </div>
  );
}
