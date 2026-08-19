import { useRef, useState } from "react";
import { Upload, Trash2, Video, Camera, Radio, Info, Loader2, Globe, Boxes, Scan } from "lucide-react";
import { statusBadge, fmtDuration } from "../utils";
import { useT } from "../i18n";
import SceneAnalytics from "./SceneAnalytics";

export default function VideoManager({
  videos,
  feeds = [],
  selectedVideo,
  onSelectVideo,
  onUpload,
  onIngestStream,
  onStartLive,
  onReindex,
  onDelete,
}) {
  const t = useT();
  const [reindexing, setReindexing] = useState(false);
  const [sceneVideo, setSceneVideo] = useState(null); // video row whose scene panel is open
  const fileRef = useRef(null);
  const [mode, setMode] = useState("upload"); // upload | live
  const [cameraId, setCameraId] = useState("CAM-1");
  const [progress, setProgress] = useState(null);

  // live-feed state
  const [streamUrl, setStreamUrl] = useState("");
  const [duration, setDuration] = useState(30);
  const [streaming, setStreaming] = useState(false);

  const handleFiles = async (files) => {
    for (const file of files) {
      setProgress({ name: file.name, pct: 0 });
      await onUpload(file, cameraId, (pct) =>
        setProgress({ name: file.name, pct })
      );
    }
    setProgress(null);
    if (fileRef.current) fileRef.current.value = "";
  };

  const handleStream = async () => {
    if (!streamUrl.trim()) return;
    setStreaming(true);
    try {
      await onIngestStream({
        url: streamUrl.trim(),
        camera_id: cameraId,
        duration_sec: Number(duration),
      });
      setStreamUrl("");
    } finally {
      setStreaming(false);
    }
  };

  // One-click load of a bundled public feed.
  const loadFeed = async (feed) => {
    setStreaming(true);
    try {
      await onIngestStream({
        url: feed.url,
        camera_id: feed.name,
        duration_sec: Number(duration),
      });
    } finally {
      setStreaming(false);
    }
  };

  // Start a continuous LIVE session (watch + index in real time).
  const goLive = async (url, camera_id) => {
    if (!url?.trim()) return;
    setStreaming(true);
    try {
      await onStartLive({ url: url.trim(), camera_id });
    } finally {
      setStreaming(false);
    }
  };

  return (
    <div className="flex h-full flex-col">
      <div className="mb-3 flex items-center gap-2 text-sm font-semibold text-slate-200">
        <Video size={16} className="text-accent" />
        {t("vision.cameraFeeds")}
        {onReindex && videos.length > 0 && (
          <button
            onClick={async () => {
              setReindexing(true);
              try { await onReindex(); } finally { setReindexing(false); }
            }}
            disabled={reindexing}
            className="ml-auto inline-flex items-center gap-1 rounded bg-ink-700 px-1.5 py-0.5 text-[10px] font-medium text-slate-400 hover:bg-ink-600 disabled:opacity-50"
            title={t("vision.reindexTitle")}
          >
            {reindexing ? <Loader2 size={11} className="animate-spin" /> : <Boxes size={11} />}
            {t("vision.reindex")}
          </button>
        )}
        <span className="rounded bg-ink-700 px-2 py-0.5 text-xs text-slate-400">
          {videos.length}
        </span>
      </div>

      {/* Ingest control */}
      <div className="mb-3 rounded-lg border border-dashed border-ink-500 bg-ink-800/60 p-3">
        {/* mode tabs */}
        <div className="mb-2 grid grid-cols-2 gap-1 rounded-lg bg-ink-900/60 p-1">
          <button
            onClick={() => setMode("upload")}
            className={`flex items-center justify-center gap-1.5 rounded py-1 text-xs font-medium transition ${
              mode === "upload" ? "bg-accent-600 text-white" : "text-slate-400"
            }`}
          >
            <Upload size={13} /> {t("vision.upload")}
          </button>
          <button
            onClick={() => setMode("live")}
            className={`flex items-center justify-center gap-1.5 rounded py-1 text-xs font-medium transition ${
              mode === "live" ? "bg-accent-600 text-white" : "text-slate-400"
            }`}
          >
            <Radio size={13} /> {t("vision.liveFeed")}
          </button>
        </div>

        <div className="mb-2 flex items-center gap-2">
          <Camera size={14} className="text-slate-400" />
          <input
            value={cameraId}
            onChange={(e) => setCameraId(e.target.value)}
            className="w-full rounded bg-ink-700 px-2 py-1 text-xs text-slate-200 outline-none focus:ring-1 focus:ring-accent"
            placeholder={t("vision.cameraIdPh")}
          />
        </div>

        {mode === "upload" ? (
          <>
            <button
              onClick={() => fileRef.current?.click()}
              className="flex w-full items-center justify-center gap-2 rounded bg-accent-600 px-3 py-2 text-xs font-semibold text-white transition hover:bg-accent-700"
            >
              <Upload size={14} />
              {t("vision.uploadFootage")}
            </button>
            <input
              ref={fileRef}
              type="file"
              accept="video/*"
              multiple
              className="hidden"
              onChange={(e) => handleFiles(Array.from(e.target.files || []))}
            />
            {progress && (
              <div className="mt-2">
                <div className="truncate text-[11px] text-slate-400">
                  {progress.name}
                </div>
                <div className="mt-1 h-1.5 overflow-hidden rounded bg-ink-700">
                  <div
                    className="h-full bg-accent transition-all"
                    style={{ width: `${progress.pct}%` }}
                  />
                </div>
              </div>
            )}
          </>
        ) : (
          <>
            <input
              value={streamUrl}
              onChange={(e) => setStreamUrl(e.target.value)}
              placeholder={t("vision.streamUrlPh")}
              className="mb-2 w-full rounded bg-ink-700 px-2 py-1.5 text-xs text-slate-200 outline-none focus:ring-1 focus:ring-accent"
            />
            <button
              onClick={() => goLive(streamUrl, "LIVE")}
              disabled={streaming || !streamUrl.trim()}
              className="mb-2 flex w-full items-center justify-center gap-2 rounded bg-signal-red/80 px-3 py-2 text-xs font-semibold text-white transition hover:bg-signal-red disabled:opacity-40"
            >
              {streaming ? (
                <Loader2 size={14} className="animate-spin" />
              ) : (
                <Radio size={14} />
              )}
              {t("vision.goLive")}
            </button>
            <div className="mb-2 flex items-center gap-2">
              <button
                onClick={handleStream}
                disabled={streaming || !streamUrl.trim()}
                className="flex flex-1 items-center justify-center gap-1.5 rounded bg-ink-700 px-2 py-1.5 text-[11px] font-medium text-slate-200 transition hover:bg-ink-600 disabled:opacity-40"
                title={t("vision.captureOnceTitle")}
              >
                {t("vision.captureOnce")}
              </button>
              <input
                type="number"
                min={5}
                max={600}
                value={duration}
                onChange={(e) => setDuration(e.target.value)}
                className="w-14 rounded bg-ink-700 px-2 py-1 text-xs text-slate-200 outline-none focus:ring-1 focus:ring-accent"
              />
              <span className="text-[11px] text-slate-400">{t("vision.sec")}</span>
            </div>
            <div className="mt-2 flex gap-1.5 rounded bg-signal-amber/10 p-2 text-[10px] leading-snug text-signal-amber/90">
              <Info size={20} className="shrink-0" />
              <span>{t("vision.legalNotice")}</span>
            </div>

            {feeds.length > 0 && (
              <div className="mt-3">
                <div className="mb-1.5 flex items-center gap-1.5 text-[11px] font-semibold text-slate-300">
                  <Globe size={12} className="text-accent" />
                  {t("vision.publicFeeds")}
                </div>
                <div className="space-y-1.5">
                  {feeds.map((f) => (
                    <button
                      key={f.id}
                      onClick={() => goLive(f.url, f.name)}
                      disabled={streaming}
                      className="group w-full rounded-lg border border-ink-600 bg-ink-900/40 p-2 text-left transition hover:border-signal-red disabled:opacity-50"
                    >
                      <div className="flex items-center justify-between gap-2">
                        <span className="truncate text-xs font-medium text-slate-200">
                          {f.name}
                        </span>
                        <span
                          className={`shrink-0 rounded px-1.5 py-0.5 text-[9px] font-semibold ${
                            f.category === "Live"
                              ? "bg-signal-green/15 text-signal-green"
                              : "bg-accent/15 text-accent"
                          }`}
                        >
                          {f.category}
                        </span>
                      </div>
                      <div className="mt-0.5 truncate text-[10px] text-slate-500">
                        {f.location}
                      </div>
                    </button>
                  ))}
                </div>
              </div>
            )}
          </>
        )}
      </div>

      {/* Feed list */}
      <div className="-mr-1 flex-1 space-y-1.5 overflow-y-auto pr-1">
        {videos.length === 0 && (
          <p className="px-1 py-6 text-center text-xs text-slate-500">
            {t("vision.noFootage")}
          </p>
        )}
        {videos.map((v) => {
          const badge = statusBadge(v.status);
          const active = selectedVideo === v.id;
          return (
            <div
              key={v.id}
              onClick={() => onSelectVideo(active ? null : v.id)}
              className={`group cursor-pointer rounded-lg border p-2.5 transition ${
                active
                  ? "border-accent bg-accent/10"
                  : "border-ink-600 bg-ink-800/40 hover:border-ink-500"
              }`}
            >
              <div className="flex items-center justify-between gap-2">
                <span className="truncate text-xs font-medium text-slate-200">
                  {v.camera_id}
                </span>
                <span className={`rounded px-1.5 py-0.5 text-[10px] ${badge.cls}`}>
                  {badge.label}
                </span>
              </div>
              <div className="mt-1 truncate text-[11px] text-slate-500">
                {v.filename}
              </div>
              <div className="mt-1 flex items-center justify-between text-[10px] text-slate-500">
                <span>
                  {t("vision.keyframes", { n: v.keyframe_count })} ·{" "}
                  {fmtDuration(v.duration_sec)}
                </span>
                <span className="flex items-center gap-2">
                  <button
                    onClick={(e) => {
                      e.stopPropagation();
                      setSceneVideo(v);
                    }}
                    className="inline-flex items-center gap-1 rounded bg-ink-700 px-1.5 py-0.5 text-[10px] font-medium text-slate-300 transition hover:bg-ink-600 hover:text-accent"
                    title={t("scene.open")}
                  >
                    <Scan size={11} /> {t("scene.open")}
                  </button>
                  <button
                    onClick={(e) => {
                      e.stopPropagation();
                      onDelete(v.id);
                    }}
                    className="opacity-0 transition group-hover:opacity-100 hover:text-signal-red"
                    title={t("vision.deleteFeed")}
                  >
                    <Trash2 size={13} />
                  </button>
                </span>
              </div>
            </div>
          );
        })}
      </div>

      {sceneVideo && (
        <SceneAnalytics
          videoId={sceneVideo.id}
          cameraId={sceneVideo.camera_id}
          onClose={() => setSceneVideo(null)}
        />
      )}
    </div>
  );
}
