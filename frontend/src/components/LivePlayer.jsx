import { useEffect, useRef, useState } from "react";
import Hls from "hls.js";
import { Radio, Square, AlertTriangle, ChevronUp, ChevronDown } from "lucide-react";

/**
 * Live preview of a feed using hls.js (for .m3u8 streams). While this plays,
 * the backend is continuously indexing the same feed so it can be searched.
 */
export default function LivePlayer({ video, indexedCount, onStop, stopping }) {
  const videoRef = useRef(null);
  const [err, setErr] = useState(null);
  // Collapsing the preview frees the screen for search + results — the player
  // keeps indexing in the background, so collapse loses nothing.
  const [collapsed, setCollapsed] = useState(false);

  const url = video?.stream_url;
  const isHls = url && /\.m3u8(\?|$)/i.test(url);

  useEffect(() => {
    setErr(null);
    const el = videoRef.current;
    if (!el || !url) return;

    if (!isHls) {
      // Non-HLS (e.g. YouTube/RTSP) can't play directly in a <video>; the feed
      // is still being captured + indexed on the backend.
      setErr("preview-unsupported");
      return;
    }

    let hls;
    if (el.canPlayType("application/vnd.apple.mpegurl")) {
      el.src = url; // native HLS (Safari)
    } else if (Hls.isSupported()) {
      hls = new Hls({ liveDurationInfinity: true, lowLatencyMode: true });
      hls.loadSource(url);
      hls.attachMedia(el);
      hls.on(Hls.Events.ERROR, (_e, data) => {
        if (data.fatal) setErr("playback-failed");
      });
    } else {
      setErr("playback-failed");
    }
    el.play?.().catch(() => {});

    return () => {
      if (hls) hls.destroy();
    };
  }, [url, isHls]);

  return (
    <div className="mb-4 overflow-hidden rounded-xl border border-signal-red/40 bg-ink-800/70">
      <div className="flex items-center justify-between border-b border-ink-600 px-3 py-2">
        <div className="flex items-center gap-2 text-sm">
          <span className="inline-flex items-center gap-1.5 rounded-full bg-signal-red/15 px-2 py-0.5 text-xs font-semibold text-signal-red">
            <Radio size={12} className="animate-pulse" /> LIVE
          </span>
          <span className="font-medium text-slate-200">{video.camera_id}</span>
          <span className="text-xs text-slate-500">
            indexing in real time · {indexedCount ?? video.keyframe_count} frames captured
          </span>
        </div>
        <div className="flex items-center gap-2">
          <button
            onClick={() => setCollapsed((c) => !c)}
            className="inline-flex items-center gap-1.5 rounded-lg bg-ink-700 px-2.5 py-1.5 text-xs font-semibold text-slate-300 transition hover:bg-ink-600"
            title={collapsed ? "Show preview" : "Hide preview (keeps indexing)"}
          >
            {collapsed ? <ChevronDown size={13} /> : <ChevronUp size={13} />}
            {collapsed ? "Show" : "Hide"}
          </button>
          <button
            onClick={onStop}
            disabled={stopping}
            className="inline-flex items-center gap-1.5 rounded-lg bg-ink-700 px-3 py-1.5 text-xs font-semibold text-slate-200 transition hover:bg-signal-red/20 hover:text-signal-red disabled:opacity-50"
          >
            <Square size={13} /> Stop
          </button>
        </div>
      </div>

      <div className={`relative bg-black ${collapsed ? "hidden" : ""}`}>
        {err ? (
          <div className="flex flex-col items-center justify-center gap-2 px-4 py-10 text-center text-sm text-slate-400">
            <AlertTriangle size={22} className="text-signal-amber" />
            {err === "preview-unsupported" ? (
              <span>
                This feed can't preview in-browser, but it's being captured and
                indexed live — search results below update in real time.
              </span>
            ) : (
              <span>
                Live preview unavailable (the stream blocked playback), but
                capture + indexing continue on the server.
              </span>
            )}
          </div>
        ) : (
          <video
            ref={videoRef}
            muted
            playsInline
            controls
            className="mx-auto max-h-[34vh] w-full bg-black object-contain"
          />
        )}
      </div>
    </div>
  );
}
