import { useCallback, useEffect, useMemo, useState } from "react";
import {
  MapContainer, TileLayer, CircleMarker, Polyline, Popup, Tooltip,
} from "react-leaflet";
import "leaflet/dist/leaflet.css";
import {
  Map as MapIcon, Loader2, Siren, TriangleAlert, Route, X,
  TrendingUp, TrendingDown, Minus, Building2, Brain, Layers,
} from "lucide-react";
import * as API from "../../api";
import { BarList } from "./charts";

/** City Map — GIS crime intelligence for Ahmedabad.
 *  Layers: Reports (logged complaint/case density) and Risk forecast (the
 *  predictive model's 0-100 hotspot scores + trend). Filters by category and
 *  time window; the patrol planner draws optimized unit routes over the
 *  current top-risk localities. */

const SEV_COLORS = { low: "#22c55e", medium: "#f4b23c", high: "#fb923c", critical: "#ef4444" };
const BAND_COLORS = { low: "#324468", guarded: "#f4b23c", elevated: "#fb923c", high: "#ef4444" };
const UNIT_COLORS = ["#f4b23c", "#38bdf8", "#22c55e", "#a855f7", "#fb7185", "#14b8a6"];
const WINDOWS = [
  { label: "7 days", days: 7 }, { label: "30 days", days: 30 },
  { label: "90 days", days: 90 }, { label: "All time", days: 0 },
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

function SeverityBar({ mix }) {
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
          <span key={sev}><span style={{ color: SEV_COLORS[sev] }}>●</span> {sev} {n}</span>
        ))}
      </div>
    </div>
  );
}

function HourBars({ data }) {
  const max = Math.max(...data.map((d) => d.count), 1);
  return (
    <div className="flex h-16 items-end gap-px">
      {data.map((d) => (
        <div key={d.hour} className="flex-1 rounded-t bg-accent"
          style={{ height: `${(d.count / max) * 100}%`, minHeight: d.count ? 3 : 1, opacity: d.count ? 1 : 0.25 }}
          title={`${String(d.hour).padStart(2, "0")}:00 — ${d.count} report${d.count === 1 ? "" : "s"}`} />
      ))}
    </div>
  );
}

export default function CityMapView() {
  const [layer, setLayer] = useState("reports"); // reports | risk
  const [category, setCategory] = useState("");
  const [days, setDays] = useState(0);
  const [data, setData] = useState(null);        // /analytics/map
  const [risk, setRisk] = useState(null);        // /predict/risk
  const [temporal, setTemporal] = useState(null);
  const [routes, setRoutes] = useState(null);    // patrol plan, null = hidden
  const [units, setUnits] = useState(2);
  const [planning, setPlanning] = useState(false);

  const refresh = useCallback(() => {
    const params = {};
    if (category) params.category = category;
    if (days) params.days = days;
    API.getMapData(params).then(setData).catch(() => {});
    API.getRiskScores().then(setRisk).catch(() => {});
    API.getTemporal().then(setTemporal).catch(() => {});
  }, [category, days]);

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
        <p className="mt-3 text-sm">Loading city intelligence…</p>
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

  return (
    <div className="flex h-full flex-col p-4 sm:p-6">
      <div className="mb-1 flex items-center gap-2">
        <MapIcon className="text-accent" size={20} />
        <h2 className="font-serif text-xl font-bold text-white">City Map · Ahmedabad</h2>
      </div>
      <p className="mb-3 text-xs text-slate-500">
        {layer === "reports"
          ? `Area-wise load from ${totals.complaints} complaints, ${totals.cases} linked cases and ${totals.anomalies} anomaly detections.`
          : "Hotspot forecast — recency-weighted risk model over reports, severity, category and live anomaly signals."}
      </p>

      {/* control bar */}
      <div className="mb-3 flex flex-wrap items-center gap-2 text-xs">
        <div className="flex rounded-lg bg-ink-800 p-1">
          <button onClick={() => setLayer("reports")}
            className={`inline-flex items-center gap-1.5 rounded-md px-3 py-1.5 font-semibold transition ${
              layer === "reports" ? "bg-accent-600 text-white" : "text-slate-400 hover:text-slate-200"}`}>
            <Layers size={13} /> Reports
          </button>
          <button onClick={() => setLayer("risk")}
            className={`inline-flex items-center gap-1.5 rounded-md px-3 py-1.5 font-semibold transition ${
              layer === "risk" ? "bg-accent-600 text-white" : "text-slate-400 hover:text-slate-200"}`}>
            <Brain size={13} /> Risk forecast
          </button>
        </div>

        {layer === "reports" && (
          <>
            <select value={category} onChange={(e) => setCategory(e.target.value)}
              className="rounded-lg border border-ink-600 bg-ink-800 px-2 py-1.5 text-slate-300">
              <option value="">All categories</option>
              {(data.categories || []).map((c) => (
                <option key={c} value={c}>{c.replace(/_/g, " ")}</option>
              ))}
            </select>
            <select value={days} onChange={(e) => setDays(Number(e.target.value))}
              className="rounded-lg border border-ink-600 bg-ink-800 px-2 py-1.5 text-slate-300">
              {WINDOWS.map((w) => <option key={w.days} value={w.days}>{w.label}</option>)}
            </select>
          </>
        )}

        <div className="ml-auto flex items-center gap-2">
          {routes ? (
            <button onClick={() => setRoutes(null)}
              className="inline-flex items-center gap-1.5 rounded-lg bg-ink-700 px-3 py-1.5 font-semibold text-slate-300 hover:text-white">
              <X size={13} /> Clear routes
            </button>
          ) : (
            <>
              <select value={units} onChange={(e) => setUnits(Number(e.target.value))}
                title="Patrol units available"
                className="rounded-lg border border-ink-600 bg-ink-800 px-2 py-1.5 text-slate-300">
                {[1, 2, 3, 4].map((n) => <option key={n} value={n}>{n} unit{n > 1 ? "s" : ""}</option>)}
              </select>
              <button onClick={planRoutes} disabled={planning}
                className="inline-flex items-center gap-1.5 rounded-lg bg-accent-600 px-3 py-1.5 font-semibold text-white hover:bg-accent-700 disabled:opacity-50">
                {planning ? <Loader2 size={13} className="animate-spin" /> : <Route size={13} />} Plan patrol routes
              </button>
            </>
          )}
        </div>
      </div>

      <div className="grid min-h-0 flex-1 gap-3 lg:grid-cols-[1fr_280px]">
        {/* map */}
        <div className="min-h-[460px] overflow-hidden rounded-xl border border-ink-600">
          <MapContainer center={[data.center.lat, data.center.lng]} zoom={12} scrollWheelZoom
            style={{ height: "100%", width: "100%", minHeight: 460, background: "#0a1124" }}>
            <TileLayer
              attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
              url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
            />

            {layer === "reports" && data.areas.map((a) => {
              const total = a.complaints + a.cases;
              const style = densityStyle(total, maxLoad);
              const r = riskByArea.get(a.area);
              return (
                <CircleMarker key={a.area} center={[a.lat, a.lng]} pathOptions={style} radius={style.radius}>
                  <Tooltip direction="top" opacity={0.9}>
                    <span className="text-xs font-semibold">
                      {a.area}: {total} report{total === 1 ? "" : "s"}{a.anomalies > 0 ? " · ⚠" : ""}
                    </span>
                  </Tooltip>
                  <Popup>
                    <div className="min-w-[190px] text-xs">
                      <div className="mb-1 text-sm font-bold">{a.area}</div>
                      <div className="space-y-0.5">
                        <div>Complaints: <b>{a.complaints}</b> · Cases: <b>{a.cases}</b></div>
                        {a.top_category && <div>Top category: <b>{a.top_category.replace(/_/g, " ")}</b></div>}
                        {r && (
                          <div className="flex items-center gap-1">
                            Risk: <b style={{ color: BAND_COLORS[r.risk_band] }}>{r.risk_score}</b>
                            <TrendIcon trend={r.trend} />
                          </div>
                        )}
                        {a.anomalies > 0 && (
                          <div className="flex items-center gap-1 font-semibold text-red-600">
                            <Siren size={12} /> {a.anomalies} anomaly alert{a.anomalies === 1 ? "" : "s"}
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
                    <span className="text-xs font-semibold">{a.area}: risk {a.risk_score} ({a.risk_band})</span>
                  </Tooltip>
                  <Popup>
                    <div className="min-w-[190px] text-xs">
                      <div className="mb-1 text-sm font-bold">{a.area}</div>
                      <div className="space-y-0.5">
                        <div>Risk score: <b style={{ color: BAND_COLORS[a.risk_band] }}>{a.risk_score} ({a.risk_band})</b></div>
                        <div className="flex items-center gap-1">
                          Forecast: <b style={{ color: BAND_COLORS[a.predicted_band] }}>{a.predicted_score}</b>
                          <TrendIcon trend={a.trend} /> {a.trend}
                        </div>
                        {a.active_anomalies > 0 && (
                          <div className="flex items-center gap-1 font-semibold text-red-600">
                            <Siren size={12} /> {a.active_anomalies} live anomaly signal{a.active_anomalies === 1 ? "" : "s"}
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
                      Unit {rt.unit}: {rt.distance_km} km · ~{rt.eta_min} min
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
          <div className="rounded-xl border border-ink-600 bg-ink-800/70 p-3">
            <div className="mb-2 flex items-center gap-1.5 text-xs font-semibold text-slate-200">
              <Brain size={13} className="text-accent" /> Top predicted hotspots
            </div>
            <div className="space-y-1">
              {top5.map((a, i) => (
                <div key={a.area} className="flex items-center gap-2 rounded-md bg-ink-900/40 px-2 py-1.5 text-xs">
                  <span className="w-4 text-slate-600">{i + 1}</span>
                  <span className="flex-1 truncate font-medium text-slate-200">{a.area}</span>
                  <TrendIcon trend={a.trend} />
                  <span className="rounded px-1.5 py-0.5 text-[10px] font-bold"
                    style={{ color: BAND_COLORS[a.risk_band], background: `${BAND_COLORS[a.risk_band]}22` }}>
                    {a.risk_score}
                  </span>
                </div>
              ))}
            </div>
          </div>

          {routes?.routes?.length > 0 && (
            <div className="rounded-xl border border-ink-600 bg-ink-800/70 p-3">
              <div className="mb-2 flex items-center gap-1.5 text-xs font-semibold text-slate-200">
                <Route size={13} className="text-accent" /> Patrol plan
                <span className="ml-auto inline-flex items-center gap-1 text-[10px] text-slate-500">
                  <Building2 size={10} /> {routes.station.name}
                </span>
              </div>
              {routes.routes.map((rt) => {
                const color = UNIT_COLORS[(rt.unit - 1) % UNIT_COLORS.length];
                return (
                  <div key={rt.unit} className="mb-2 rounded-md bg-ink-900/40 p-2 text-xs">
                    <div className="mb-1 flex items-center gap-1.5 font-semibold" style={{ color }}>
                      Unit {rt.unit}
                      <span className="ml-auto font-normal text-slate-500">
                        {rt.distance_km} km · ~{rt.eta_min} min
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
              <div className="mb-2 text-xs font-semibold text-slate-200">Reports by hour of day</div>
              <HourBars data={temporal.by_hour} />
              <div className="mt-1 flex justify-between text-[9px] text-slate-600">
                <span>00:00</span><span>12:00</span><span>23:00</span>
              </div>
              <div className="mb-2 mt-3 text-xs font-semibold text-slate-200">By day of week</div>
              <BarList data={temporal.by_day.map((d) => ({ label: d.day, count: d.count }))} />
            </div>
          )}
        </div>
      </div>

      <div className="mt-2 flex items-center gap-2 text-[10px] text-slate-500">
        <TriangleAlert size={12} className="text-accent" />
        <span>
          Risk scores are recency-weighted model estimates over locality-level
          approximations — decision support for patrol planning, not evidence.
        </span>
      </div>
    </div>
  );
}
