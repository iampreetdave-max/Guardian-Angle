import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { ShieldCheck, ScanSearch, Inbox, Loader2, Scale, Megaphone, FolderOpen, Shield, LogOut, BarChart3, Menu, X, Lightbulb, Boxes } from "lucide-react";
import * as API from "./api";
import { useAuth, isStaff, isAdmin } from "./auth";
import StatusBar from "./components/StatusBar";
import VideoManager from "./components/VideoManager";
import SearchPanel from "./components/SearchPanel";
import FrameCard from "./components/FrameCard";
import FrameDetail from "./components/FrameDetail";
import ReportTray from "./components/ReportTray";
import LivePlayer from "./components/LivePlayer";
import ArbiterPanel from "./components/Arbiter/ArbiterPanel";
import LoginView from "./components/platform/LoginView";
import NotificationBell from "./components/platform/NotificationBell";
import ComplaintsView from "./components/platform/ComplaintsView";
import CasesView from "./components/platform/CasesView";
import AdminView from "./components/platform/AdminView";
import AnalyticsView from "./components/platform/AnalyticsView";
import Footer from "./components/platform/Footer";

// Top-level gate: show the login screen until authenticated, then the app shell.
export default function App() {
  const { user, loading } = useAuth();
  if (loading) {
    return (
      <div className="flex h-screen items-center justify-center">
        <Loader2 className="animate-spin text-accent" size={28} />
      </div>
    );
  }
  if (!user) return <LoginView />;
  return <Workbench />;
}

function Workbench() {
  const [health, setHealth] = useState(null);
  const [videos, setVideos] = useState([]);
  const [feeds, setFeeds] = useState([]);
  const [selectedVideo, setSelectedVideo] = useState(null);

  const [results, setResults] = useState(null); // SearchResponse
  const [searching, setSearching] = useState(false);
  const [error, setError] = useState(null);

  const [selectedIds, setSelectedIds] = useState(new Set());
  const [detailHit, setDetailHit] = useState(null);

  const [liveId, setLiveId] = useState(null); // video_id of the active live feed
  const [stopping, setStopping] = useState(false);

  const { user, logout } = useAuth();
  const staff = isStaff(user);
  // citizens land on complaints; staff land on the command dashboard
  const [module, setModule] = useState(staff ? "dashboard" : "complaints");
  const [arbiterSeed, setArbiterSeed] = useState(""); // cross-module: prefill incident
  const [openCaseId, setOpenCaseId] = useState(null); // deep-link from complaint -> case
  const [feedsOpen, setFeedsOpen] = useState(false); // mobile: VisionScan sidebar drawer

  // Role-based navigation, shared by the desktop top-nav and the mobile bottom bar.
  const navItems = [
    staff && { key: "dashboard", label: "Dashboard", icon: BarChart3 },
    staff && { key: "vision", label: "VisionScan", icon: ScanSearch },
    staff && { key: "arbiter", label: "Arbiter", icon: Scale },
    { key: "cases", label: "Cases", icon: FolderOpen },
    { key: "complaints", label: "Complaints", icon: Megaphone },
    isAdmin(user) && { key: "admin", label: "Admin", icon: Shield },
  ].filter(Boolean);

  const lastQuery = useRef({ query: "", type: "text" });
  const lastSearchArgs = useRef(null); // for live auto-refresh

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

  const liveVideo = useMemo(
    () => videos.find((v) => v.id === liveId) || null,
    [videos, liveId]
  );

  // While a live feed runs, re-run the last text/object search periodically so
  // results reflect newly-indexed frames in near real time.
  useEffect(() => {
    if (!liveId || !lastSearchArgs.current) return;
    const id = setInterval(() => {
      runSearch(lastSearchArgs.current, true);
    }, 5000);
    return () => clearInterval(id);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [liveId, results]);

  // ---- search ----
  const runSearch = async ({ mode, query, file, group = true }, silent = false) => {
    if (!silent) setSearching(true);
    setError(null);
    // remember text/object/region searches so a live feed can auto-refresh them
    if (mode === "text" || mode === "object" || mode === "region") {
      lastSearchArgs.current = { mode, query, group };
    }
    try {
      const opts = {
        top_k: 40,
        video_id: selectedVideo || undefined,
        group_events: group,
      };
      let res;
      if (mode === "text") {
        res = await API.searchText({ query, ...opts });
        lastQuery.current = { query, type: "text" };
      } else if (mode === "region") {
        res = await API.searchRegion({
          query,
          top_k: 60,
          video_id: selectedVideo || undefined,
        });
        lastQuery.current = { query, type: "object" };
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
      if (!silent) {
        setError(e?.response?.data?.detail || "Search failed. Is footage processed?");
        setResults(null);
      }
    } finally {
      if (!silent) setSearching(false);
    }
  };

  // ---- upload / delete / live ----
  const handleUpload = async (file, cameraId, onProgress) => {
    await API.uploadVideo(file, cameraId, onProgress);
    await refresh();
  };
  const handleIngestStream = async (payload) => {
    await API.ingestStream(payload);
    await refresh();
  };
  const handleStartLive = async (payload) => {
    const v = await API.startLive(payload);
    setLiveId(v.id);
    setSelectedVideo(v.id); // scope searches to the live feed
    await refresh();
  };
  const handleStopLive = async () => {
    if (!liveId) return;
    setStopping(true);
    try {
      await API.stopLive(liveId);
      setLiveId(null);
      await refresh();
    } finally {
      setStopping(false);
    }
  };
  const handleReindex = async () => {
    const r = await API.reindexObjects();
    await refresh();
    return r;
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

  // All selectable frames keyed by id — both top-level hits and the individual
  // frames inside a grouped event. Event frames inherit camera/file info from
  // their representative hit so a report can include any of them.
  const frameIndex = useMemo(() => {
    const map = new Map();
    if (results) {
      for (const h of results.hits) {
        map.set(h.frame_id, h);
        for (const f of h.event_frames || []) {
          if (!map.has(f.frame_id)) {
            map.set(f.frame_id, {
              ...f,
              camera_id: h.camera_id,
              video_id: h.video_id,
              filename: h.filename,
              query_type: h.query_type,
            });
          }
        }
      }
    }
    return map;
  }, [results]);

  const selectedHits = useMemo(
    () => [...selectedIds].map((id) => frameIndex.get(id)).filter(Boolean),
    [selectedIds, frameIndex]
  );

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
      <header className="flex items-center gap-3 border-b border-ink-700 bg-ink-800/80 px-3 py-3 backdrop-blur sm:px-5">
        <div className="flex items-center gap-2 sm:gap-3">
          <img
            src="/logo.jpeg"
            alt="Cyber Crime Branch, Ahmedabad City Police"
            className="h-12 w-12 rounded-lg object-contain bg-white/5 p-0.5 ring-1 ring-ink-600 sm:h-16 sm:w-16"
          />
          <div>
            <h1 className="font-serif text-lg font-bold leading-tight text-white sm:text-xl">
              City<span className="text-accent">Shield</span>
            </h1>
            <p className="hidden text-[10px] uppercase tracking-wider text-slate-500 sm:block">
              Unified AI Policing · Cyber Crime Branch, Ahmedabad City Police
            </p>
          </div>
        </div>

        {/* role-based module nav — desktop only; mobile uses the bottom bar */}
        <nav className="ml-4 hidden items-center gap-1 rounded-lg bg-ink-900/60 p-1 md:flex">
          {navItems.map((m) => (
            <button
              key={m.key}
              onClick={() => setModule(m.key)}
              className={`inline-flex items-center gap-1.5 rounded-md px-3 py-1.5 text-xs font-semibold transition ${
                module === m.key ? "bg-accent-600 text-white" : "text-slate-400 hover:text-slate-200"
              }`}
            >
              <m.icon size={14} /> {m.label}
            </button>
          ))}
        </nav>

        <div className="ml-auto flex items-center gap-2 sm:gap-3">
          {module === "vision" && <div className="hidden lg:block"><StatusBar health={health} /></div>}
          <NotificationBell />
          <div className="flex items-center gap-2 border-l border-ink-700 pl-2 sm:pl-3">
            <div className="hidden text-right sm:block">
              <div className="text-xs font-semibold text-slate-200">{user.name}</div>
              <div className="text-[10px] uppercase tracking-wide text-slate-500">{user.role}</div>
            </div>
            <button onClick={logout} title="Sign out"
              className="rounded-lg bg-ink-700 p-2 text-slate-300 hover:bg-signal-red/20 hover:text-signal-red">
              <LogOut size={15} />
            </button>
          </div>
        </div>
      </header>

      <div className="tricolor-bar" />

      {module === "arbiter" ? (
        <div className="min-h-0 flex-1 overflow-y-auto pb-16 md:pb-0">
          <ArbiterPanel seedText={arbiterSeed} />
        </div>
      ) : module === "dashboard" || module === "complaints" || module === "cases" || module === "admin" ? (
        <div className="flex min-h-0 flex-1 flex-col overflow-y-auto pb-16 md:pb-0">
          <div className="flex-1">
            {module === "dashboard" && <AnalyticsView />}
            {module === "complaints" && (
              <ComplaintsView onOpenCase={(id) => { setOpenCaseId(id); setModule("cases"); }} />
            )}
            {module === "cases" && (
              <CasesView openCaseId={openCaseId} onClearOpen={() => setOpenCaseId(null)} />
            )}
            {module === "admin" && <AdminView />}
          </div>
          <Footer />
        </div>
      ) : (
      <div className="flex min-h-0 flex-1">
        {/* Sidebar — desktop */}
        <aside className="hidden w-72 shrink-0 border-r border-ink-700 bg-ink-800/40 p-4 md:block">
          <VideoManager
            videos={videos}
            feeds={feeds}
            selectedVideo={selectedVideo}
            onSelectVideo={setSelectedVideo}
            onUpload={handleUpload}
            onIngestStream={handleIngestStream}
            onStartLive={handleStartLive}
            onReindex={handleReindex}
            onDelete={handleDelete}
          />
        </aside>

        {/* Sidebar — mobile slide-over drawer */}
        {feedsOpen && (
          <div className="fixed inset-0 z-40 flex md:hidden">
            <div className="absolute inset-0 bg-black/60" onClick={() => setFeedsOpen(false)} />
            <aside className="relative w-72 max-w-[85%] overflow-y-auto border-r border-ink-700 bg-ink-800 p-4 pb-20">
              <button
                onClick={() => setFeedsOpen(false)}
                className="mb-3 inline-flex items-center gap-1.5 rounded-lg bg-ink-700 px-3 py-1.5 text-xs font-semibold text-slate-200"
              >
                <X size={14} /> Close
              </button>
              <VideoManager
                videos={videos}
                feeds={feeds}
                selectedVideo={selectedVideo}
                onSelectVideo={(id) => { setSelectedVideo(id); setFeedsOpen(false); }}
                onUpload={handleUpload}
                onIngestStream={handleIngestStream}
                onStartLive={handleStartLive}
                onReindex={handleReindex}
                onDelete={handleDelete}
              />
            </aside>
          </div>
        )}

        {/* Main */}
        <main className="flex min-w-0 flex-1 flex-col overflow-hidden p-3 pb-16 sm:p-5 md:pb-5">
          <button
            onClick={() => setFeedsOpen(true)}
            className="mb-3 inline-flex w-fit items-center gap-1.5 rounded-lg bg-ink-700 px-3 py-1.5 text-xs font-semibold text-slate-200 md:hidden"
          >
            <Menu size={14} /> Feeds &amp; Upload
          </button>
          {liveVideo && (
            <LivePlayer
              video={liveVideo}
              indexedCount={liveVideo.keyframe_count}
              onStop={handleStopLive}
              stopping={stopping}
            />
          )}

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
                  {results.count > 0 && (
                    <button
                      onClick={() => {
                        const top = results.hits[0];
                        setArbiterSeed(
                          `CCTV evidence: "${results.query}" observed on camera ` +
                          `${top?.camera_id || ""} at ${top?.timestamp_hms || ""}. ` +
                          `Investigated via VisionScan; ${results.count} matching ` +
                          `frame(s) found. Draft an FIR for this incident.`
                        );
                        setModule("arbiter");
                      }}
                      className="inline-flex items-center gap-1.5 rounded-lg bg-ink-700 px-3 py-1.5 text-xs font-semibold text-slate-200 transition hover:bg-accent-600 hover:text-white"
                      title="Send this evidence to Arbiter to draft an FIR"
                    >
                      <Scale size={14} /> Draft FIR in Arbiter
                    </button>
                  )}
                </div>
                {/* Reactive nudge: a text search that returned little is usually the
                    wrong tool for a specific object — offer the precise region mode. */}
                {results.query_type === "text" && results.count <= 6 && (
                  <div className="mb-3 flex flex-wrap items-center gap-2 rounded-lg border border-accent/30 bg-accent/10 px-3 py-2 text-xs text-slate-300">
                    <Lightbulb size={14} className="text-accent" />
                    <span>
                      {results.count === 0 ? "No strong text matches." : "Few text matches."}{" "}
                      Looking for a specific object? <span className="font-semibold text-accent">Find every object</span> scores each detected object and is far more precise.
                    </span>
                    <button
                      onClick={() => runSearch({ mode: "region", query: results.query })}
                      className="ml-auto inline-flex items-center gap-1.5 rounded-md bg-accent-600 px-2.5 py-1 font-semibold text-white transition hover:bg-accent-700"
                    >
                      <Boxes size={13} /> Find every object
                    </button>
                  </div>
                )}
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
      )}

      {/* Mobile bottom tab bar — mirrors the desktop top nav */}
      <nav className="fixed inset-x-0 bottom-0 z-30 flex border-t border-ink-700 bg-ink-900/95 backdrop-blur md:hidden">
        {navItems.map((m) => (
          <button
            key={m.key}
            onClick={() => setModule(m.key)}
            className={`flex flex-1 flex-col items-center gap-0.5 py-2 text-[10px] font-semibold transition ${
              module === m.key ? "text-accent" : "text-slate-500"
            }`}
          >
            <m.icon size={18} /> {m.label}
          </button>
        ))}
      </nav>

      <FrameDetail
        hit={detailHit}
        selectedIds={selectedIds}
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
