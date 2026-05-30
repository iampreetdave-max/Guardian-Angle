import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { ShieldCheck, ScanSearch, Inbox, Loader2 } from "lucide-react";
import * as API from "./api";
import StatusBar from "./components/StatusBar";
import VideoManager from "./components/VideoManager";
import SearchPanel from "./components/SearchPanel";
import FrameCard from "./components/FrameCard";
import FrameDetail from "./components/FrameDetail";
import ReportTray from "./components/ReportTray";

export default function App() {
  const [health, setHealth] = useState(null);
  const [videos, setVideos] = useState([]);
  const [feeds, setFeeds] = useState([]);
  const [selectedVideo, setSelectedVideo] = useState(null);

  const [results, setResults] = useState(null); // SearchResponse
  const [searching, setSearching] = useState(false);
  const [error, setError] = useState(null);

  const [selectedIds, setSelectedIds] = useState(new Set());
  const [detailHit, setDetailHit] = useState(null);

  const lastQuery = useRef({ query: "", type: "text" });

  // ---- polling: health + videos (keeps processing status live) ----
  const refresh = useCallback(async () => {
    try {
      const [h, v] = await Promise.all([API.getHealth(), API.listVideos()]);
      setHealth(h);
      setVideos(v);
    } catch (e) {
      /* backend may still be warming up */
    }
  }, []);

  useEffect(() => {
    refresh();
    const id = setInterval(refresh, 3000);
    return () => clearInterval(id);
  }, [refresh]);

  // Public feed catalog is static — fetch once.
  useEffect(() => {
    API.getFeeds().then(setFeeds).catch(() => {});
  }, []);

  // ---- search ----
  const runSearch = async ({ mode, query, file }) => {
    setSearching(true);
    setError(null);
    try {
      const opts = { top_k: 40, video_id: selectedVideo || undefined };
      let res;
      if (mode === "text") {
        res = await API.searchText({ query, ...opts });
        lastQuery.current = { query, type: "text" };
      } else if (mode === "object") {
        res = await API.searchObject({ label: query, min_confidence: 0.35, ...opts });
        lastQuery.current = { query, type: "object" };
      } else if (mode === "image") {
        res = await API.searchImage(file, opts);
        lastQuery.current = { query: `[image] ${file.name}`, type: "image" };
      } else if (mode === "face") {
        res = await API.searchFace(file, opts);
        lastQuery.current = { query: `[face] ${file.name}`, type: "face" };
      }
      setResults(res);
    } catch (e) {
      setError(e?.response?.data?.detail || "Search failed. Is footage processed?");
      setResults(null);
    } finally {
      setSearching(false);
    }
  };

  // ---- upload / delete ----
  const handleUpload = async (file, cameraId, onProgress) => {
    await API.uploadVideo(file, cameraId, onProgress);
    await refresh();
  };
  const handleIngestStream = async (payload) => {
    await API.ingestStream(payload);
    await refresh();
  };
  const handleDelete = async (id) => {
    await API.deleteVideo(id);
    if (selectedVideo === id) setSelectedVideo(null);
    await refresh();
  };

  // ---- report selection ----
  const toggleSelect = (frameId) =>
    setSelectedIds((prev) => {
      const next = new Set(prev);
      next.has(frameId) ? next.delete(frameId) : next.add(frameId);
      return next;
    });

  const selectedHits = useMemo(() => {
    if (!results) return [];
    return results.hits.filter((h) => selectedIds.has(h.frame_id));
  }, [results, selectedIds]);

  const generateReport = async (payload) => {
    const blob = await API.generateReport(payload);
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = "visionscan_report.pdf";
    a.click();
    URL.revokeObjectURL(url);
  };

  const readyCount = videos.filter((v) => v.status === "ready").length;

  return (
    <div className="flex h-screen flex-col">
      {/* Header */}
      <header className="flex items-center gap-3 border-b border-ink-700 bg-ink-800/80 px-5 py-3 backdrop-blur">
        <div className="flex items-center gap-2">
          <div className="flex h-9 w-9 items-center justify-center rounded-lg bg-accent-600">
            <ScanSearch size={20} className="text-white" />
          </div>
          <div>
            <h1 className="text-lg font-bold leading-tight text-white">
              Vision<span className="text-accent">Scan</span>
            </h1>
            <p className="text-[10px] uppercase tracking-wider text-slate-500">
              Smart CCTV Analysis for Investigation
            </p>
          </div>
        </div>
        <div className="ml-auto">
          <StatusBar health={health} />
        </div>
      </header>

      <div className="flex min-h-0 flex-1">
        {/* Sidebar */}
        <aside className="w-72 shrink-0 border-r border-ink-700 bg-ink-800/40 p-4">
          <VideoManager
            videos={videos}
            feeds={feeds}
            selectedVideo={selectedVideo}
            onSelectVideo={setSelectedVideo}
            onUpload={handleUpload}
            onIngestStream={handleIngestStream}
            onDelete={handleDelete}
          />
        </aside>

        {/* Main */}
        <main className="flex min-w-0 flex-1 flex-col overflow-hidden p-5">
          <SearchPanel
            onSearch={runSearch}
            searching={searching}
            faceEnabled={health?.models?.face}
          />

          {selectedVideo && (
            <div className="mt-2 text-xs text-slate-400">
              Scoped to{" "}
              <span className="text-accent">
                {videos.find((v) => v.id === selectedVideo)?.camera_id}
              </span>
              {" · "}
              <button onClick={() => setSelectedVideo(null)} className="underline">
                search all feeds
              </button>
            </div>
          )}

          {/* Results */}
          <div className="-mr-2 mt-4 flex-1 overflow-y-auto pr-2">
            {error && (
              <div className="rounded-lg border border-signal-red/30 bg-signal-red/10 p-3 text-sm text-signal-red">
                {error}
              </div>
            )}

            {searching && (
              <div className="flex flex-col items-center justify-center py-20 text-slate-400">
                <Loader2 size={28} className="animate-spin text-accent" />
                <p className="mt-3 text-sm">Scanning footage…</p>
              </div>
            )}

            {!searching && results && (
              <>
                <div className="mb-3 flex items-center justify-between">
                  <p className="text-sm text-slate-300">
                    <span className="font-bold text-white">{results.count}</span>{" "}
                    matches for{" "}
                    <span className="text-accent">{results.query}</span>
                  </p>
                </div>
                {results.count === 0 ? (
                  <div className="flex flex-col items-center justify-center py-20 text-slate-500">
                    <Inbox size={28} />
                    <p className="mt-3 text-sm">No matching frames found.</p>
                  </div>
                ) : (
                  <div className="grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-4 xl:grid-cols-5">
                    {results.hits.map((hit) => (
                      <FrameCard
                        key={hit.frame_id}
                        hit={hit}
                        selected={selectedIds.has(hit.frame_id)}
                        onToggleSelect={toggleSelect}
                        onOpen={setDetailHit}
                      />
                    ))}
                  </div>
                )}
              </>
            )}

            {!searching && !results && !error && (
              <div className="flex flex-col items-center justify-center py-24 text-center text-slate-500">
                <ShieldCheck size={36} className="text-ink-500" />
                <p className="mt-4 max-w-sm text-sm">
                  {readyCount > 0
                    ? "Search your footage by natural language, object, reference image, or suspect face."
                    : "Upload CCTV footage, or open the Live Feed tab on the left to load a public feed in one click. Processing runs automatically."}
                </p>
              </div>
            )}
          </div>
        </main>
      </div>

      <FrameDetail
        hit={detailHit}
        selected={detailHit && selectedIds.has(detailHit.frame_id)}
        onToggleSelect={toggleSelect}
        onClose={() => setDetailHit(null)}
      />

      <ReportTray
        selectedHits={selectedHits}
        query={lastQuery.current.query}
        queryType={lastQuery.current.type}
        onClear={() => setSelectedIds(new Set())}
        onGenerate={generateReport}
      />
    </div>
  );
}
