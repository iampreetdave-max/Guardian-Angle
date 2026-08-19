import { useEffect, useMemo, useState } from "react";
import {
  X, Loader2, Boxes, Layers, Info, Pentagon, ArrowLeftRight,
  Undo2, Eraser, Play, Gauge,
} from "lucide-react";
import * as API from "../api";
import { fmtDuration } from "../utils";
import { useT } from "../i18n";

const QUALITY_STYLE = {
  good: "bg-signal-green/15 text-signal-green",
  degraded: "bg-signal-amber/15 text-signal-amber",
  poor: "bg-signal-red/15 text-signal-red",
};

// ponytail: hand-rolled sparkline instead of a chart lib — matches charts.jsx,
// which already refuses the dependency.
function Sparkline({ points, peakAt }) {
  if (!points || points.length === 0) return null;
  const W = 560, H = 72, PAD = 4;
  const maxC = Math.max(...points.map((p) => p.count), 1);
  const maxT = Math.max(...points.map((p) => p.t), 0.001);
  const xy = points.map((p) => [
    (p.t / maxT) * W,
    H - PAD - (p.count / maxC) * (H - 2 * PAD),
  ]);
  const line = xy.map(([x, y], i) => `${i ? "L" : "M"}${x.toFixed(1)},${y.toFixed(1)}`).join(" ");
  const peakX = peakAt != null ? (peakAt / maxT) * W : null;
  return (
    <svg viewBox={`0 0 ${W} ${H}`} preserveAspectRatio="none" className="h-20 w-full">
      <path d={`${line} L${W},${H} L0,${H} Z`} fill="#f4b23c" opacity="0.14" />
      <path d={line} fill="none" stroke="#f4b23c" strokeWidth="2" vectorEffect="non-scaling-stroke" />
      {peakX != null && (
        <line x1={peakX} y1="0" x2={peakX} y2={H} stroke="#f4b23c" strokeWidth="1"
          strokeDasharray="3 3" opacity="0.7" vectorEffect="non-scaling-stroke" />
      )}
    </svg>
  );
}

function Stat({ label, value, hint, tint = "text-white" }) {
  return (
    <div className="rounded-xl border border-ink-600 bg-ink-800/60 p-3">
      <div className="text-[10px] uppercase tracking-wide text-slate-400">{label}</div>
      <div className={`mt-1 text-2xl font-bold tabular-nums ${tint}`}>{value}</div>
      {hint && <div className="mt-0.5 text-[10px] text-slate-500">{hint}</div>}
    </div>
  );
}

export default function SceneAnalytics({ videoId, cameraId, onClose }) {
  const t = useT();
  const [data, setData] = useState(null);
  const [frameUrl, setFrameUrl] = useState(null);
  const [error, setError] = useState(null);

  const [tool, setTool] = useState("zone"); // zone | line
  const [points, setPoints] = useState([]); // [[x,y], ...] normalised 0..1
  const [labels, setLabels] = useState([]); // empty = all types
  const [busy, setBusy] = useState(false);
  const [result, setResult] = useState(null);
  const [runError, setRunError] = useState(null);

  const load = () => {
    setError(null);
    setData(null);
    API.getTracks(videoId)
      .then((d) => {
        setData(d);
        // Reuse the existing object search purely as a "give me one keyframe of
        // this video" call — it is a plain DB lookup, no model runs.
        const top = Object.keys(d.by_label || {})[0];
        if (!top) return;
        return API.searchObject({
          label: top, video_id: videoId, top_k: 1,
          min_confidence: 0, group_events: false,
        })
          .then((r) => setFrameUrl(r.hits?.[0]?.thumbnail_url || null))
          .catch(() => {});
      })
      .catch((e) => setError(e?.response?.data?.detail || t("scene.loadFailed")));
  };

  useEffect(load, [videoId]);

  // Reset the canvas when switching tool — a 5-point polygon is not a line.
  useEffect(() => { setPoints([]); setResult(null); setRunError(null); }, [tool]);

  const rawByLabel = useMemo(() => {
    const out = {};
    for (const tr of data?.tracks || []) out[tr.label] = (out[tr.label] || 0) + tr.n_frames;
    return out;
  }, [data]);

  const addPoint = (e) => {
    const r = e.currentTarget.getBoundingClientRect();
    const x = Math.min(1, Math.max(0, (e.clientX - r.left) / r.width));
    const y = Math.min(1, Math.max(0, (e.clientY - r.top) / r.height));
    setPoints((p) => (tool === "line" && p.length >= 2 ? [[x, y]] : [...p, [x, y]]));
    setResult(null);
  };

  const enough = tool === "zone" ? points.length >= 3 : points.length === 2;

  const run = async () => {
    if (!enough) return;
    setBusy(true);
    setRunError(null);
    try {
      const body = labels.length ? { labels } : {};
      const res =
        tool === "zone"
          ? await API.zoneAnalytics(videoId, { polygon: points, ...body })
          : await API.lineCrossings(videoId, { line: points, ...body });
      setResult(res);
    } catch (e) {
      setRunError(e?.response?.data?.detail || t("scene.analyseFailed"));
    } finally {
      setBusy(false);
    }
  };

  const secs = (v) => `${Number(v || 0).toFixed(1)}${t("scene.secShort")}`;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/80 p-3 backdrop-blur-sm sm:p-6"
      onClick={onClose}>
      <div className="flex max-h-[92vh] w-full max-w-5xl flex-col overflow-hidden rounded-xl border border-ink-500 bg-ink-800 shadow-2xl"
        onClick={(e) => e.stopPropagation()}>

        <div className="flex items-center gap-3 border-b border-ink-600 px-4 py-3">
          <Boxes size={17} className="text-accent" />
          <h2 className="text-sm font-bold text-white">{t("scene.title")}</h2>
          <span className="rounded bg-ink-700 px-2 py-0.5 text-[11px] text-slate-300">{cameraId}</span>
          <button onClick={onClose} title={t("scene.close")}
            className="ml-auto rounded p-1 text-slate-400 transition hover:bg-ink-700 hover:text-white">
            <X size={17} />
          </button>
        </div>

        <div className="flex-1 space-y-4 overflow-y-auto p-4">
          {error && (
            <div className="rounded-xl border border-signal-red/30 bg-signal-red/10 p-4 text-sm text-signal-red">
              {error}
              <button onClick={load} className="ml-3 rounded bg-ink-700 px-2 py-0.5 text-xs text-slate-200 hover:bg-ink-600">
                {t("scene.retry")}
              </button>
            </div>
          )}

          {!data && !error && (
            <div className="flex items-center justify-center gap-2 py-20 text-sm text-slate-400">
              <Loader2 size={20} className="animate-spin text-accent" /> {t("scene.loading")}
            </div>
          )}

          {data && (
            <>
              {/* ---- counts: the whole point of tracking ---- */}
              <div className="rounded-xl border border-ink-600 bg-ink-800/60 p-4">
                <div className="flex flex-wrap items-end gap-x-8 gap-y-3">
                  <div>
                    <div className="text-4xl font-bold tabular-nums text-accent">{data.distinct_objects}</div>
                    <div className="text-xs text-slate-300">{t("scene.distinctObjects")}</div>
                  </div>
                  <div>
                    <div className="text-2xl font-bold tabular-nums text-slate-500 line-through decoration-slate-600">
                      {data.total_detections}
                    </div>
                    <div className="text-xs text-slate-500">{t("scene.rawDetections")}</div>
                  </div>
                  {data.distinct_objects > 0 && (
                    <span className="rounded-full bg-signal-green/15 px-2.5 py-1 text-[11px] font-semibold text-signal-green">
                      {t("scene.inflation", {
                        x: (data.total_detections / data.distinct_objects).toFixed(1),
                      })}
                    </span>
                  )}
                  <div className="ml-auto flex items-center gap-2">
                    <span className="text-[10px] uppercase tracking-wide text-slate-400">
                      {t("scene.quality")}
                    </span>
                    <span
                      title={t("scene.qualityTip", {
                        fps: Number(data.fps_estimate || 0).toFixed(1),
                        frag: Math.round((data.fragmentation || 0) * 100),
                      })}
                      className={`inline-flex cursor-help items-center gap-1 rounded-full px-2 py-0.5 text-[11px] font-semibold ${
                        QUALITY_STYLE[data.tracking_quality] || "bg-ink-600 text-slate-300"
                      }`}
                    >
                      <Gauge size={12} />
                      {t(`scene.quality${(data.tracking_quality || "")
                        .replace(/^./, (c) => c.toUpperCase())}`)}
                      <Info size={11} className="opacity-70" />
                    </span>
                    <span className="text-[10px] text-slate-500">
                      {t("scene.fpsEstimate", { fps: Number(data.fps_estimate || 0).toFixed(1) })}
                    </span>
                  </div>
                </div>
                <p className="mt-3 text-[11px] leading-snug text-slate-400">{t("scene.countsLead")}</p>

                {/* per-label breakdown */}
                {Object.keys(data.by_label || {}).length > 0 ? (
                  <div className="mt-3 border-t border-ink-600 pt-3">
                    <div className="mb-2 flex items-center gap-1.5 text-[11px] font-semibold text-slate-300">
                      <Layers size={12} className="text-accent" /> {t("scene.byLabel")}
                    </div>
                    <div className="grid grid-cols-[1fr_auto_auto] gap-x-4 gap-y-1 text-xs">
                      <span className="text-[10px] uppercase text-slate-500">{t("scene.colLabel")}</span>
                      <span className="text-right text-[10px] uppercase text-slate-500">{t("scene.colDistinct")}</span>
                      <span className="text-right text-[10px] uppercase text-slate-500">{t("scene.colRaw")}</span>
                      {Object.entries(data.by_label)
                        .sort((a, b) => b[1] - a[1])
                        .map(([label, n]) => (
                          <LabelRow key={label} label={label} n={n} raw={rawByLabel[label]} />
                        ))}
                    </div>
                  </div>
                ) : (
                  <p className="mt-3 border-t border-ink-600 pt-3 text-xs text-slate-500">
                    {t("scene.noTracks")}
                  </p>
                )}
              </div>

              {/* ---- drawing tools ---- */}
              <div className="rounded-xl border border-ink-600 bg-ink-800/60 p-4">
                <div className="mb-3 flex flex-wrap items-center gap-2">
                  {[
                    { id: "zone", icon: Pentagon, label: t("scene.zoneTool") },
                    { id: "line", icon: ArrowLeftRight, label: t("scene.lineTool") },
                  ].map(({ id, icon: Icon, label }) => (
                    <button key={id} onClick={() => setTool(id)}
                      className={`inline-flex items-center gap-1.5 rounded-lg px-3 py-1.5 text-xs font-medium transition ${
                        tool === id ? "bg-accent-600 text-white" : "bg-ink-700 text-slate-300 hover:bg-ink-600"
                      }`}>
                      <Icon size={13} /> {label}
                    </button>
                  ))}
                  <span className="ml-auto text-[11px] text-slate-500">
                    {t("scene.pointsPlaced", { n: points.length })}
                  </span>
                </div>

                <p className="mb-2 text-[11px] text-slate-400">
                  {tool === "zone" ? t("scene.drawZoneHint") : t("scene.drawLineHint")}
                </p>

                {frameUrl ? (
                  <div className="relative select-none overflow-hidden rounded-xl border border-ink-600"
                    onClick={addPoint} style={{ cursor: "crosshair" }}>
                    <img src={frameUrl} alt={cameraId} className="block w-full" draggable={false} />
                    <svg viewBox="0 0 100 100" preserveAspectRatio="none"
                      className="pointer-events-none absolute inset-0 h-full w-full">
                      {tool === "zone" && points.length >= 2 && (
                        <polygon
                          points={points.map(([x, y]) => `${x * 100},${y * 100}`).join(" ")}
                          fill="#f4b23c" fillOpacity="0.22" stroke="#f4b23c" strokeWidth="2"
                          vectorEffect="non-scaling-stroke"
                        />
                      )}
                      {tool === "line" && points.length === 2 && (
                        <line
                          x1={points[0][0] * 100} y1={points[0][1] * 100}
                          x2={points[1][0] * 100} y2={points[1][1] * 100}
                          stroke="#f4b23c" strokeWidth="3" vectorEffect="non-scaling-stroke"
                        />
                      )}
                    </svg>
                    {/* Handles as DOM dots so they stay round under the stretched viewBox. */}
                    {points.map(([x, y], i) => (
                      <span key={i}
                        className="pointer-events-none absolute h-2.5 w-2.5 -translate-x-1/2 -translate-y-1/2 rounded-full border border-ink-900 bg-accent"
                        style={{ left: `${x * 100}%`, top: `${y * 100}%` }} />
                    ))}
                  </div>
                ) : (
                  <div className="rounded-xl border border-dashed border-ink-500 p-8 text-center text-xs text-slate-500">
                    {t("scene.frameUnavailable")}
                  </div>
                )}

                {/* label filter */}
                {Object.keys(data.by_label || {}).length > 0 && (
                  <div className="mt-3 flex flex-wrap items-center gap-1.5">
                    <span className="mr-1 text-[10px] uppercase tracking-wide text-slate-500">
                      {t("scene.filterLabels")}
                    </span>
                    <button onClick={() => setLabels([])}
                      className={`rounded-full px-2 py-0.5 text-[11px] ${
                        labels.length === 0 ? "bg-accent-600 text-white" : "bg-ink-700 text-slate-300 hover:bg-ink-600"
                      }`}>
                      {t("scene.filterAll")}
                    </button>
                    {Object.keys(data.by_label).map((label) => (
                      <button key={label}
                        onClick={() =>
                          setLabels((L) => (L.includes(label) ? L.filter((x) => x !== label) : [...L, label]))
                        }
                        className={`rounded-full px-2 py-0.5 text-[11px] capitalize ${
                          labels.includes(label) ? "bg-accent-600 text-white" : "bg-ink-700 text-slate-300 hover:bg-ink-600"
                        }`}>
                        {label}
                      </button>
                    ))}
                  </div>
                )}

                <div className="mt-3 flex flex-wrap items-center gap-2">
                  <button onClick={() => { setPoints((p) => p.slice(0, -1)); setResult(null); }}
                    disabled={points.length === 0}
                    className="inline-flex items-center gap-1.5 rounded-lg bg-ink-700 px-2.5 py-1.5 text-xs text-slate-200 hover:bg-ink-600 disabled:opacity-40">
                    <Undo2 size={13} /> {t("scene.undo")}
                  </button>
                  <button onClick={() => { setPoints([]); setResult(null); }}
                    disabled={points.length === 0}
                    className="inline-flex items-center gap-1.5 rounded-lg bg-ink-700 px-2.5 py-1.5 text-xs text-slate-200 hover:bg-ink-600 disabled:opacity-40">
                    <Eraser size={13} /> {t("scene.clear")}
                  </button>
                  <button onClick={run} disabled={!enough || busy}
                    className="inline-flex items-center gap-1.5 rounded-lg bg-accent-600 px-3 py-1.5 text-xs font-semibold text-white hover:bg-accent-700 disabled:opacity-40">
                    {busy ? <Loader2 size={13} className="animate-spin" /> : <Play size={13} />}
                    {busy ? t("scene.analysing") : tool === "zone" ? t("scene.analyseZone") : t("scene.analyseLine")}
                  </button>
                  {!enough && (
                    <span className="text-[11px] text-slate-500">
                      {tool === "zone" ? t("scene.needPoints") : t("scene.needLine")}
                    </span>
                  )}
                </div>

                {runError && (
                  <div className="mt-3 rounded-lg border border-signal-red/30 bg-signal-red/10 p-2.5 text-xs text-signal-red">
                    {runError}
                  </div>
                )}

                {/* ---- results ---- */}
                {result && tool === "zone" && (
                  <div className="mt-4 border-t border-ink-600 pt-4">
                    <div className="grid grid-cols-2 gap-3 sm:grid-cols-3">
                      <Stat label={t("scene.peakOccupancy")} value={result.peak_occupancy ?? 0}
                        tint="text-accent"
                        hint={result.peak_at_sec != null ? t("scene.peakAt", { t: secs(result.peak_at_sec) }) : null} />
                      <Stat label={t("scene.meanOccupancy")} value={Number(result.mean_occupancy || 0).toFixed(1)} />
                      <Stat label={t("scene.distinctEntered")}
                        value={result.distinct_objects_entered ?? t("scene.distinctEnteredNA")}
                        hint={result.distinct_objects_entered == null ? t("scene.distinctEnteredTip") : null} />
                    </div>
                    {result.timeline?.length ? (
                      <div className="mt-3">
                        <div className="mb-1 text-[10px] uppercase tracking-wide text-slate-400">
                          {t("scene.timeline")}
                        </div>
                        <Sparkline points={result.timeline} peakAt={result.peak_at_sec} />
                        <div className="flex justify-between text-[10px] tabular-nums text-slate-500">
                          <span>{secs(result.timeline[0].t)}</span>
                          <span>{secs(result.timeline[result.timeline.length - 1].t)}</span>
                        </div>
                      </div>
                    ) : (
                      <p className="mt-3 text-xs text-slate-500">{t("scene.zoneEmpty")}</p>
                    )}
                  </div>
                )}

                {result && tool === "line" && (
                  <div className="mt-4 border-t border-ink-600 pt-4">
                    <div className="grid grid-cols-3 gap-3">
                      <Stat label={t("scene.crossingsIn")} value={result.crossings_in ?? 0} tint="text-signal-green" />
                      <Stat label={t("scene.crossingsOut")} value={result.crossings_out ?? 0} tint="text-signal-red" />
                      <Stat label={t("scene.net")} value={result.net ?? 0} tint="text-accent" />
                    </div>
                    {result.events?.length ? (
                      <div className="mt-3">
                        <div className="mb-1 text-[10px] uppercase tracking-wide text-slate-400">
                          {t("scene.events")}
                        </div>
                        <div className="max-h-40 space-y-1 overflow-y-auto pr-1">
                          {result.events.slice(0, 40).map((ev, i) => (
                            <div key={`${ev.track_id}-${ev.t}-${i}`}
                              className="flex items-center gap-2 rounded-lg bg-ink-900/50 px-2 py-1 text-[11px]">
                              <span className={`rounded px-1.5 py-0.5 font-semibold ${
                                ev.direction === "in"
                                  ? "bg-signal-green/15 text-signal-green"
                                  : "bg-signal-red/15 text-signal-red"
                              }`}>
                                {ev.direction === "in" ? t("scene.dirIn") : t("scene.dirOut")}
                              </span>
                              <span className="capitalize text-slate-300">{ev.label}</span>
                              <span className="font-mono text-slate-500">#{ev.track_id}</span>
                              <span className="ml-auto font-mono tabular-nums text-slate-400">
                                {fmtDuration(ev.t)}
                              </span>
                            </div>
                          ))}
                          {result.events.length > 40 && (
                            <div className="px-2 text-[10px] text-slate-500">
                              {t("scene.moreEvents", { n: result.events.length - 40 })}
                            </div>
                          )}
                        </div>
                      </div>
                    ) : (
                      <p className="mt-3 text-xs text-slate-500">{t("scene.noCrossings")}</p>
                    )}
                  </div>
                )}
              </div>
            </>
          )}
        </div>
      </div>
    </div>
  );
}

// One row of the per-label table (three grid cells, so it needs a fragment).
function LabelRow({ label, n, raw }) {
  return (
    <>
      <span className="capitalize text-slate-300">{label}</span>
      <span className="text-right font-semibold tabular-nums text-accent">{n}</span>
      <span className="text-right tabular-nums text-slate-500">{raw ?? "—"}</span>
    </>
  );
}
