import { useEffect, useRef, useState } from "react";
import {
  Landmark, Search, Loader2, Sparkles, WifiOff, ExternalLink, Bookmark,
  BookmarkCheck, BellPlus, Link2, FileText, X, RefreshCw, TrendingUp,
  Scale, ScrollText, Megaphone, BookOpen, ClipboardList, FileBadge, HandCoins,
  Star, Play, Calendar, Activity, BarChart3, Bell, Trash2, Save,
} from "lucide-react";
import * as API from "../../api";
import {
  govInsights, govSavedSearches, govAddSavedSearch, govRunSavedSearch,
  govRemoveSavedSearch,
} from "./govApi";
import { useAuth, isStaff, isLead } from "../../auth";
import { useT } from "../../i18n";

// Category → colour + icon, shared by chips and result badges.
const CATS = {
  GR: { color: "text-sky-300 bg-sky-400/15", icon: ScrollText },
  Notification: { color: "text-amber-300 bg-amber-400/15", icon: Megaphone },
  Circular: { color: "text-violet-300 bg-violet-400/15", icon: ClipboardList },
  Act: { color: "text-emerald-300 bg-emerald-400/15", icon: BookOpen },
  Rule: { color: "text-teal-300 bg-teal-400/15", icon: FileBadge },
  Judgment: { color: "text-rose-300 bg-rose-400/15", icon: Scale },
  Scheme: { color: "text-indigo-300 bg-indigo-400/15", icon: HandCoins },
};
const CAT_KEYS = Object.keys(CATS);

const LANGS = [
  { code: "en", label: "English" },
  { code: "hi", label: "हिन्दी" },
  { code: "gu", label: "ગુજરાતી" },
];

export default function GovIntelPanel() {
  const t = useT();
  const { user } = useAuth();
  const staff = isStaff(user);
  // POST /api/gov/refresh is require_role("lead") server-side (govintel/routes.py),
  // and require_role is a minimum-rank gate — so an officer seeing this button
  // only gets a 403. Match the server rank instead of showing a dead control.
  const canRefresh = isLead(user);

  const [health, setHealth] = useState(null);
  const [q, setQ] = useState("");
  const [docType, setDocType] = useState("");
  const [region, setRegion] = useState("");
  const [department, setDepartment] = useState("");
  const [dateFrom, setDateFrom] = useState("");
  const [dateTo, setDateTo] = useState("");
  const [departments, setDepartments] = useState([]);
  const [lang, setLang] = useState("en");

  const [tab, setTab] = useState("search"); // search | saved
  const [insights, setInsights] = useState(null);

  const [results, setResults] = useState(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState(null);

  const [suggests, setSuggests] = useState([]);
  const [showSug, setShowSug] = useState(false);
  const [trending, setTrending] = useState([]);

  const [bookmarks, setBookmarks] = useState(new Set());
  const [bookmarkDocs, setBookmarkDocs] = useState([]);
  const [subs, setSubs] = useState([]);
  const [saved, setSaved] = useState([]);
  const [saveAlert, setSaveAlert] = useState(false);
  const [savingSearch, setSavingSearch] = useState(false);
  const [refreshing, setRefreshing] = useState(false);
  const [refreshMsg, setRefreshMsg] = useState(null);

  const [detail, setDetail] = useState(null); // { doc, related, summary }
  const sugTimer = useRef(null);

  // ---- initial loads ----
  useEffect(() => {
    API.govHealth().then(setHealth).catch(() => {});
    API.govTrending().then((d) => setTrending(d.trending || [])).catch(() => {});
    API.govDepartments().then((d) => setDepartments(d.departments || [])).catch(() => {});
    govInsights().then(setInsights).catch(() => {});
    if (user) loadUserData();
    runSearch("");
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const loadUserData = () => {
    API.govBookmarks().then((d) => {
      setBookmarkDocs(d.items || []);
      setBookmarks(new Set((d.items || []).map((x) => x.id)));
    }).catch(() => {});
    API.govSubscriptions().then((d) => setSubs(d.items || [])).catch(() => {});
    govSavedSearches().then((d) => setSaved(d.items || [])).catch(() => {});
  };

  // re-run when filters change (keeps current query)
  useEffect(() => {
    runSearch(q);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [docType, region, department, dateFrom, dateTo]);

  const runSearch = async (query) => {
    setBusy(true);
    setError(null);
    try {
      const params = { q: query || "", k: 24 };
      if (docType) params.doc_type = docType;
      if (region) params.region = region;
      if (department) params.department = department;
      if (dateFrom) params.date_from = dateFrom;
      if (dateTo) params.date_to = dateTo;
      const res = await API.govSearch(params);
      setResults(res);
    } catch (e) {
      setError(e?.response?.data?.detail || t("govintel.searchFailed"));
      setResults(null);
    } finally {
      setBusy(false);
    }
  };

  const clearFilters = () => {
    setDocType(""); setRegion(""); setDepartment(""); setDateFrom(""); setDateTo("");
  };

  const saveCurrentSearch = async () => {
    setSavingSearch(true);
    try {
      await govAddSavedSearch({
        name: q || [docType, region, department].filter(Boolean).join(" · "),
        query: q, doc_type: docType, region, department,
        date_from: dateFrom, date_to: dateTo, alert: saveAlert,
      });
      const d = await govSavedSearches();
      setSaved(d.items || []);
      setSaveAlert(false);
    } catch (e) {
      setError(e?.response?.data?.detail || t("govintel.saveSearchFailed"));
    } finally {
      setSavingSearch(false);
    }
  };

  const runSaved = async (s) => {
    setTab("search");
    setQ(s.query || "");
    setDocType(s.filters?.doc_type || "");
    setRegion(s.filters?.region || "");
    setDepartment(s.filters?.department || "");
    setDateFrom(s.filters?.date_from || "");
    setDateTo(s.filters?.date_to || "");
    try {
      const res = await govRunSavedSearch(s.id);
      setResults(res);
    } catch {
      runSearch(s.query || "");
    }
  };

  const removeSaved = async (id) => {
    await govRemoveSavedSearch(id).catch(() => {});
    setSaved((prev) => prev.filter((s) => s.id !== id));
  };

  const onQueryChange = (val) => {
    setQ(val);
    setShowSug(true);
    clearTimeout(sugTimer.current);
    if (!val.trim()) { setSuggests([]); return; }
    sugTimer.current = setTimeout(() => {
      API.govSuggest(val).then((d) => setSuggests(d.suggestions || [])).catch(() => {});
    }, 180);
  };

  const submit = (query) => {
    const qq = query ?? q;
    setQ(qq);
    setShowSug(false);
    runSearch(qq);
  };

  const toggleBookmark = async (doc) => {
    const has = bookmarks.has(doc.id);
    setBookmarks((prev) => {
      const n = new Set(prev);
      has ? n.delete(doc.id) : n.add(doc.id);
      return n;
    });
    setBookmarkDocs((prev) =>
      has ? prev.filter((x) => x.id !== doc.id) : [doc, ...prev.filter((x) => x.id !== doc.id)]);
    try {
      has ? await API.govRemoveBookmark(doc.id) : await API.govAddBookmark(doc.id);
    } catch {
      /* revert handled on next load */
    }
  };

  const subscribe = async ({ query = "", doc_type = "", region: rg = "" }) => {
    try {
      await API.govAddSubscription({ query, doc_type, region: rg });
      const d = await API.govSubscriptions();
      setSubs(d.items || []);
    } catch (e) {
      setError(e?.response?.data?.detail || t("govintel.subscribeFailed"));
    }
  };

  const unsubscribe = async (id) => {
    await API.govRemoveSubscription(id).catch(() => {});
    setSubs((prev) => prev.filter((s) => s.id !== id));
  };

  const doRefresh = async () => {
    setRefreshing(true);
    setRefreshMsg(null);
    try {
      const r = await API.govRefresh();
      setRefreshMsg(t("govintel.refreshDone", { n: r.fetched, added: r.new, alerts: r.alerts }));
      runSearch(q);
      govInsights().then(setInsights).catch(() => {});
    } catch (e) {
      setRefreshMsg(e?.response?.data?.detail || t("govintel.refreshFailed"));
    } finally {
      setRefreshing(false);
    }
  };

  const openDetail = async (doc) => {
    setDetail({ doc, related: null, summary: null, summarizing: false });
    API.govRelated(doc.id).then((d) => setDetail((p) => p && p.doc.id === doc.id ? { ...p, related: d.related || [] } : p)).catch(() => {});
  };

  const summarizeDetail = async () => {
    if (!detail) return;
    setDetail((p) => ({ ...p, summarizing: true }));
    try {
      const s = await API.govSummarize({ id: detail.doc.id, language: lang });
      setDetail((p) => p ? { ...p, summary: s, summarizing: false } : p);
    } catch {
      setDetail((p) => p ? { ...p, summarizing: false } : p);
    }
  };

  const counts = results?.categories || {};

  return (
        <div className="mx-auto flex max-w-6xl flex-col p-5">
      {/* header */}
      <div className="mb-4 flex items-center gap-3">
        <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-accent-600">
          <Landmark size={22} className="text-white" />
        </div>
        <div>
          <h2 className="text-lg font-bold text-white">
            {t("govintel.titleMain")} <span className="text-accent">{t("govintel.titleAccent")}</span>
          </h2>
          <p className="text-[11px] text-slate-500">
            {t("govintel.subtitle")}
          </p>
        </div>
        {health && (
          <span
            className={`ml-auto inline-flex items-center gap-1.5 rounded-full px-2.5 py-1 text-xs font-medium ${
              health.llm_online ? "bg-signal-green/15 text-signal-green" : "bg-signal-amber/15 text-signal-amber"
            }`}
            title={`${health.search_mode} · ${health.mode}`}
          >
            {health.llm_online ? <Sparkles size={13} /> : <WifiOff size={13} />}
            {health.llm_online ? t("govintel.geminiSummaries") : t("govintel.offlineMode")}
            <span className="text-slate-500">· {t("govintel.docsCount", { n: health.corpus_documents })}</span>
          </span>
        )}
      </div>

      {/* insights / trending strip */}
      {insights && <InsightsStrip insights={insights} onPick={(rg) => { setTab("search"); setRegion(rg); }} />}

      {/* tabs */}
      <div className="mb-3 flex items-center gap-1.5 border-b border-ink-700">
        <TabButton active={tab === "search"} onClick={() => setTab("search")} icon={Search} label={t("common.search")} />
        {user && (
          <TabButton
            active={tab === "saved"} onClick={() => setTab("saved")} icon={Star}
            label={`${t("govintel.savedTab")}${bookmarkDocs.length + saved.length ? ` · ${bookmarkDocs.length + saved.length}` : ""}`}
          />
        )}
      </div>

      {tab === "saved" ? (
        <SavedTab
          bookmarkDocs={bookmarkDocs}
          saved={saved}
          onOpen={openDetail}
          onUnstar={(doc) => toggleBookmark(doc)}
          onRunSaved={runSaved}
          onRemoveSaved={removeSaved}
        />
      ) : (
      <>
      {/* search bar + suggest */}
      <div className="relative">
        <div className="flex items-center gap-2 rounded-xl border border-ink-600 bg-ink-800/70 px-3 py-2">
          <Search size={18} className="text-slate-500" />
          <input
            value={q}
            onChange={(e) => onQueryChange(e.target.value)}
            onKeyDown={(e) => e.key === "Enter" && submit()}
            onFocus={() => suggests.length && setShowSug(true)}
            onBlur={() => setTimeout(() => setShowSug(false), 150)}
            placeholder={t("govintel.searchPlaceholder")}
            className="flex-1 bg-transparent text-sm text-slate-100 outline-none placeholder:text-slate-500"
          />
          {q && (
            <button onClick={() => { setQ(""); submit(""); }} className="text-slate-500 hover:text-slate-300">
              <X size={15} />
            </button>
          )}
          <button
            onClick={() => submit()}
            className="rounded-lg bg-accent-600 px-3 py-1.5 text-xs font-semibold text-white hover:bg-accent-700"
          >
            {t("common.search")}
          </button>
        </div>
        {showSug && suggests.length > 0 && (
          <div className="absolute z-30 mt-1 w-full overflow-hidden rounded-lg border border-ink-600 bg-ink-800 shadow-2xl">
            {suggests.map((s) => (
              <button
                key={s}
                onMouseDown={() => submit(s)}
                className="block w-full px-3 py-2 text-left text-xs text-slate-300 hover:bg-ink-700"
              >
                {s}
              </button>
            ))}
          </div>
        )}
      </div>

      {/* trending */}
      {trending.length > 0 && !q && (
        <div className="mt-2 flex flex-wrap items-center gap-1.5 text-xs">
          <TrendingUp size={13} className="text-accent" />
          <span className="text-slate-500">{t("govintel.trending")}</span>
          {trending.slice(0, 7).map((term) => (
            <button key={term} onClick={() => submit(term)}
              className="rounded-full bg-ink-700 px-2 py-0.5 text-slate-300 hover:bg-accent-600 hover:text-white">
              {term}
            </button>
          ))}
        </div>
      )}

      {/* filters */}
      <div className="mt-3 flex flex-wrap items-center gap-1.5">
        <Chip active={!docType} onClick={() => setDocType("")} label={t("common.all")} />
        {CAT_KEYS.map((c) => (
          <Chip key={c} active={docType === c} onClick={() => setDocType(docType === c ? "" : c)}
            label={`${t(`govintel.cat.${c}`)}${counts[c] ? ` ·${counts[c]}` : ""}`} cls={CATS[c].color} />
        ))}
        <div className="mx-1 h-5 w-px bg-ink-600" />
        <Chip active={!region} onClick={() => setRegion("")} label={t("govintel.allRegions")} />
        <Chip active={region === "central"} onClick={() => setRegion(region === "central" ? "" : "central")} label={t("govintel.regionCentral")} />
        <Chip active={region === "gujarat"} onClick={() => setRegion(region === "gujarat" ? "" : "gujarat")} label={t("govintel.regionGujarat")} />
        <select
          value={department}
          onChange={(e) => setDepartment(e.target.value)}
          className="ml-auto rounded-lg bg-ink-700 px-2 py-1.5 text-xs text-slate-200 outline-none"
          title={t("govintel.filterByDept")}
        >
          <option value="">{t("govintel.allDepartments")}</option>
          {departments.map((d) => <option key={d} value={d}>{d}</option>)}
        </select>
        <select value={lang} onChange={(e) => setLang(e.target.value)}
          className="rounded-lg bg-ink-700 px-2 py-1.5 text-xs text-slate-200 outline-none" title={t("govintel.summaryLang")}>
          {LANGS.map((l) => <option key={l.code} value={l.code}>{l.label}</option>)}
        </select>
        {canRefresh && (
          <button onClick={doRefresh} disabled={refreshing}
            className="inline-flex items-center gap-1.5 rounded-lg bg-ink-700 px-2.5 py-1.5 text-xs font-semibold text-slate-200 hover:bg-accent-600 hover:text-white disabled:opacity-40"
            title={t("govintel.refreshTitle")}>
            {refreshing ? <Loader2 size={13} className="animate-spin" /> : <RefreshCw size={13} />} {t("govintel.refreshFeeds")}
          </button>
        )}
      </div>

      {/* advanced filters: date range + save search */}
      <div className="mt-2 flex flex-wrap items-center gap-1.5 text-[11px]">
        <Calendar size={13} className="text-slate-500" />
        <span className="text-slate-500">{t("govintel.from")}</span>
        <input type="date" value={dateFrom} onChange={(e) => setDateFrom(e.target.value)}
          className="rounded-lg bg-ink-700 px-2 py-1 text-slate-200 outline-none [color-scheme:dark]" />
        <span className="text-slate-500">{t("govintel.to")}</span>
        <input type="date" value={dateTo} onChange={(e) => setDateTo(e.target.value)}
          className="rounded-lg bg-ink-700 px-2 py-1 text-slate-200 outline-none [color-scheme:dark]" />
        {(docType || region || department || dateFrom || dateTo || q) && (
          <button onClick={() => { clearFilters(); setQ(""); submit(""); }}
            className="rounded-lg bg-ink-700 px-2 py-1 font-semibold text-slate-300 hover:bg-ink-600">
            {t("govintel.clearAll")}
          </button>
        )}
        {user && (
          <div className="ml-auto flex items-center gap-1.5">
            <label className="inline-flex items-center gap-1 text-slate-400" title={t("govintel.alertTitle")}>
              <input type="checkbox" checked={saveAlert} onChange={(e) => setSaveAlert(e.target.checked)}
                className="accent-accent-600" />
              <Bell size={11} /> {t("govintel.alert")}
            </label>
            <button onClick={saveCurrentSearch} disabled={savingSearch}
              className="inline-flex items-center gap-1 rounded-lg bg-accent-600 px-2.5 py-1 font-semibold text-white hover:bg-accent-700 disabled:opacity-40"
              title={t("govintel.saveSearchTitle")}>
              {savingSearch ? <Loader2 size={11} className="animate-spin" /> : <Save size={11} />} {t("govintel.saveSearch")}
            </button>
          </div>
        )}
      </div>

      {refreshMsg && (
        <div className="mt-2 rounded-lg bg-ink-700/60 px-3 py-1.5 text-[11px] text-slate-300">{refreshMsg}</div>
      )}

      {/* active subscriptions */}
      {subs.length > 0 && (
        <div className="mt-2 flex flex-wrap items-center gap-1.5 text-[11px]">
          <BellPlus size={12} className="text-accent" />
          <span className="text-slate-500">{t("govintel.watching")}</span>
          {subs.map((s) => (
            <span key={s.id} className="inline-flex items-center gap-1 rounded-full bg-accent/15 px-2 py-0.5 text-accent">
              {[s.query, s.doc_type, s.region].filter(Boolean).join(" · ") || t("govintel.allUpdates")}
              <button onClick={() => unsubscribe(s.id)} className="hover:text-white"><X size={11} /></button>
            </span>
          ))}
        </div>
      )}

      {/* results */}
      <div className="-mr-2 mt-4 flex-1 pr-2">
        {error && (
          <div className="rounded-lg border border-signal-red/30 bg-signal-red/10 p-3 text-sm text-signal-red">{error}</div>
        )}
        {busy && !results && (
          <div className="flex flex-col items-center justify-center py-20 text-slate-400">
            <Loader2 size={26} className="animate-spin text-accent" />
            <p className="mt-3 text-sm">{t("govintel.searching")}</p>
          </div>
        )}
        {results && (
          <>
            <p className="mb-3 text-sm text-slate-300">
              <span className="font-bold text-white">{results.count}</span> {t("govintel.documents")}
              {results.query ? <> {t("govintel.queryLabel")} <span className="text-accent">{results.query}</span></> : null}
            </p>
            {results.count === 0 ? (
              <div className="flex flex-col items-center justify-center py-20 text-slate-500">
                <FileText size={26} />
                <p className="mt-3 text-sm">{t("govintel.noMatch")}</p>
              </div>
            ) : (
              <div className="grid grid-cols-1 gap-3 lg:grid-cols-2">
                {results.results.map((d) => (
                  <ResultCard
                    key={d.id} doc={d}
                    bookmarked={bookmarks.has(d.id)}
                    canBookmark={!!user}
                    onBookmark={() => toggleBookmark(d)}
                    onOpen={() => openDetail(d)}
                    onSubscribe={() => subscribe({ query: (d.keywords || "").split(",")[0]?.trim() || d.title, doc_type: d.doc_type })}
                  />
                ))}
              </div>
            )}
          </>
        )}
      </div>
      </>
      )}

      {detail && (
        <DetailDrawer
          state={detail}
          lang={lang}
          onClose={() => setDetail(null)}
          onSummarize={summarizeDetail}
          onOpenRelated={openDetail}
        />
      )}
    </div>
  );
}

function TabButton({ active, onClick, icon: Icon, label }) {
  return (
    <button onClick={onClick}
      className={`-mb-px inline-flex items-center gap-1.5 border-b-2 px-3 py-2 text-xs font-semibold transition ${
        active ? "border-accent text-accent" : "border-transparent text-slate-400 hover:text-slate-200"
      }`}>
      <Icon size={14} /> {label}
    </button>
  );
}

const JUR_KEY = { central: "govintel.regionCentral", gujarat: "govintel.regionGujarat" };

function InsightsStrip({ insights, onPick }) {
  const t = useT();
  const byType = insights.by_type || {};
  const byJur = insights.by_jurisdiction || {};
  const feeds = insights.feeds || [];
  const okFeeds = feeds.filter((f) => f.ok).length;
  const latest = insights.latest_fetched
    ? new Date(insights.latest_fetched).toLocaleString()
    : "—";
  const topType = Object.entries(byType).sort((a, b) => b[1] - a[1]).slice(0, 4);
  return (
    <div className="mb-3 grid grid-cols-2 gap-2 lg:grid-cols-4">
      <Insight icon={BarChart3} label={t("govintel.insightDocs")}
        value={insights.total_documents}
        sub={t("govintel.insightDocsSub", { live: insights.live_documents || 0, saved: insights.total_saved_searches || 0 })} />
      <Insight icon={Landmark} label={t("govintel.insightJur")}
        value={Object.entries(byJur).map(([k, v]) => `${JUR_KEY[k] ? t(JUR_KEY[k]) : k} ${v}`).join(" · ") || "—"}
        sub={t("govintel.insightJurSub")} onClick={() => onPick && onPick("")} />
      <Insight icon={TrendingUp} label={t("govintel.insightTop")}
        value={topType.map(([k, v]) => `${CATS[k] ? t(`govintel.cat.${k}`) : k} ${v}`).join(" · ") || "—"}
        sub={t("govintel.insightTopSub", { n: insights.total_bookmarks || 0 })} />
      <Insight icon={Activity} label={t("govintel.insightHealth")}
        value={t("govintel.insightHealthValue", { ok: okFeeds, total: feeds.length })}
        sub={t("govintel.insightHealthSub", { at: latest })} />
    </div>
  );
}

function Insight({ icon: Icon, label, value, sub, onClick }) {
  return (
    <div onClick={onClick}
      className={`rounded-xl border border-ink-600 bg-ink-800/50 p-2.5 ${onClick ? "cursor-pointer hover:border-ink-500" : ""}`}>
      <div className="flex items-center gap-1.5 text-[10px] uppercase tracking-wide text-slate-500">
        <Icon size={12} className="text-accent" /> {label}
      </div>
      <div className="mt-1 truncate text-sm font-bold text-slate-100" title={String(value)}>{value}</div>
      {sub && <div className="mt-0.5 truncate text-[10px] text-slate-500">{sub}</div>}
    </div>
  );
}

function SavedTab({ bookmarkDocs, saved, onOpen, onUnstar, onRunSaved, onRemoveSaved }) {
  const t = useT();
  return (
    <div className="-mr-2 flex-1 pr-2">
      {/* saved searches */}
      <div className="mb-2 flex items-center gap-1.5 text-xs font-semibold text-slate-300">
        <Search size={13} className="text-accent" /> {t("govintel.savedSearches")}
      </div>
      {saved.length === 0 ? (
        <p className="mb-5 text-xs text-slate-500">
          {t("govintel.noSavedSearches")}
        </p>
      ) : (
        <div className="mb-5 space-y-1.5">
          {saved.map((s) => (
            <div key={s.id} className="flex items-center gap-2 rounded-lg border border-ink-700 bg-ink-800/50 p-2">
              <div className="min-w-0 flex-1">
                <div className="truncate text-xs font-semibold text-slate-200">
                  {s.name || s.query || t("govintel.allUpdates")}
                  {s.alert && (
                    <span className="ml-1.5 inline-flex items-center gap-0.5 rounded bg-accent/15 px-1 py-0.5 text-[9px] text-accent">
                      <Bell size={9} /> {t("govintel.alerting")}
                    </span>
                  )}
                </div>
                <div className="truncate text-[10px] text-slate-500">
                  {[s.query, s.filters?.doc_type, s.filters?.region, s.filters?.department,
                    s.filters?.date_from && t("govintel.fromDate", { d: s.filters.date_from }),
                    s.filters?.date_to && t("govintel.toDate", { d: s.filters.date_to })]
                    .filter(Boolean).join(" · ") || t("govintel.allDocuments")}
                </div>
              </div>
              <button onClick={() => onRunSaved(s)} title={t("govintel.rerun")}
                className="inline-flex items-center gap-1 rounded-md bg-accent-600 px-2 py-1 text-[11px] font-semibold text-white hover:bg-accent-700">
                <Play size={11} /> {t("govintel.run")}
              </button>
              <button onClick={() => onRemoveSaved(s.id)} title={t("common.delete")}
                className="rounded-md bg-ink-700 p-1 text-slate-400 hover:bg-ink-600 hover:text-signal-red">
                <Trash2 size={12} />
              </button>
            </div>
          ))}
        </div>
      )}

      {/* bookmarks */}
      <div className="mb-2 flex items-center gap-1.5 text-xs font-semibold text-slate-300">
        <Star size={13} className="text-accent" /> {t("govintel.bookmarkedDocs")}
      </div>
      {bookmarkDocs.length === 0 ? (
        <p className="text-xs text-slate-500">
          {t("govintel.noBookmarks")}
        </p>
      ) : (
        <div className="grid grid-cols-1 gap-3 lg:grid-cols-2">
          {bookmarkDocs.map((d) => (
            <div key={d.id} className="flex flex-col rounded-xl border border-ink-600 bg-ink-800/50 p-3">
              <div className="flex items-center justify-between gap-2">
                <CatBadge type={d.doc_type} />
                <button onClick={() => onUnstar(d)} title={t("govintel.removeBookmark")}
                  className="rounded-md bg-accent/20 px-2 py-1 text-[11px] font-semibold text-accent hover:bg-accent/30">
                  <BookmarkCheck size={12} />
                </button>
              </div>
              <button onClick={() => onOpen(d)} className="mt-1.5 text-left text-sm font-semibold text-slate-100 hover:text-accent">
                {d.title}
              </button>
              <div className="mt-0.5 text-[11px] text-slate-500">
                {[d.department, d.date].filter(Boolean).join(" · ")}
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

const LINK_KEY = {
  curated: "govintel.linkCurated", family: "govintel.linkFamily",
  keyword: "govintel.linkKeyword", semantic: "govintel.linkSemantic",
  category: "govintel.linkCategory", related: "govintel.linkRelated",
};

function LinkBadge({ linkType, score }) {
  const t = useT();
  const label = t(LINK_KEY[linkType] || "govintel.linkRelated");
  const cls = linkType === "curated" || linkType === "family"
    ? "text-accent" : "text-slate-500";
  return (
    <span className={`shrink-0 text-[9px] ${cls}`}>
      {label}{typeof score === "number" ? ` ${Math.round(score * 100)}%` : ""}
    </span>
  );
}

function Chip({ active, onClick, label, cls = "" }) {
  return (
    <button
      onClick={onClick}
      className={`rounded-lg px-2.5 py-1.5 text-xs font-medium transition ${
        active ? "bg-accent-600 text-white" : `bg-ink-700 text-slate-300 hover:bg-ink-600 ${cls}`
      }`}
    >
      {label}
    </button>
  );
}

function CatBadge({ type }) {
  const t = useT();
  const known = CATS[type];
  const c = known || { color: "text-slate-300 bg-slate-400/15", icon: FileText };
  const Icon = c.icon;
  return (
    <span className={`inline-flex items-center gap-1 rounded px-1.5 py-0.5 text-[10px] font-semibold ${c.color}`}>
      <Icon size={11} /> {known ? t(`govintel.cat.${type}`) : type}
    </span>
  );
}

function ResultCard({ doc, bookmarked, canBookmark, onBookmark, onOpen, onSubscribe }) {
  const t = useT();
  return (
    <div className="flex flex-col rounded-xl border border-ink-600 bg-ink-800/50 p-3 transition hover:border-ink-500">
      <div className="flex items-start justify-between gap-2">
        <div className="flex flex-wrap items-center gap-1.5">
          <CatBadge type={doc.doc_type} />
          {doc.region && (
            <span className="rounded bg-ink-700 px-1.5 py-0.5 text-[10px] uppercase tracking-wide text-slate-400">
              {doc.region}
            </span>
          )}
          {doc.origin === "live" && (
            <span className="rounded bg-signal-green/15 px-1.5 py-0.5 text-[10px] font-semibold text-signal-green">{t("govintel.live")}</span>
          )}
        </div>
        {typeof doc.score === "number" && (
          <span className="shrink-0 rounded bg-ink-700 px-1.5 py-0.5 text-[10px] text-slate-400">
            {Math.round(doc.score * 100)}%
          </span>
        )}
      </div>

      <button onClick={onOpen} className="mt-1.5 text-left text-sm font-semibold text-slate-100 hover:text-accent">
        {doc.title}
      </button>
      <div className="mt-0.5 text-[11px] text-slate-500">
        {[doc.department, doc.date].filter(Boolean).join(" · ")}
      </div>
      {doc.summary && (
        <p className="mt-1.5 line-clamp-3 text-xs leading-relaxed text-slate-400">{doc.summary}</p>
      )}

      <div className="mt-2.5 flex items-center gap-1.5 border-t border-ink-700 pt-2 text-[11px]">
        <button onClick={onOpen} className="inline-flex items-center gap-1 rounded-md bg-ink-700 px-2 py-1 font-semibold text-slate-200 hover:bg-accent-600 hover:text-white">
          <Link2 size={12} /> {t("common.details")}
        </button>
        {doc.source_url && (
          <a href={doc.source_url} target="_blank" rel="noreferrer"
            className="inline-flex items-center gap-1 rounded-md bg-ink-700 px-2 py-1 font-semibold text-slate-200 hover:bg-ink-600">
            <ExternalLink size={12} /> {t("govintel.source")}
          </a>
        )}
        {canBookmark && (
          <button onClick={onBookmark} title={bookmarked ? t("govintel.removeBookmark") : t("govintel.bookmark")}
            className={`inline-flex items-center gap-1 rounded-md px-2 py-1 font-semibold ${
              bookmarked ? "bg-accent/20 text-accent" : "bg-ink-700 text-slate-200 hover:bg-ink-600"
            }`}>
            {bookmarked ? <BookmarkCheck size={12} /> : <Bookmark size={12} />}
          </button>
        )}
        {canBookmark && (
          <button onClick={onSubscribe} title={t("govintel.subscribeTitle")}
            className="ml-auto inline-flex items-center gap-1 rounded-md bg-ink-700 px-2 py-1 font-semibold text-slate-200 hover:bg-accent-600 hover:text-white">
            <BellPlus size={12} /> {t("govintel.subscribe")}
          </button>
        )}
      </div>
    </div>
  );
}

function DetailDrawer({ state, lang, onClose, onSummarize, onOpenRelated }) {
  const t = useT();
  const { doc, related, summary, summarizing } = state;
  return (
    <div className="fixed inset-0 z-50 flex justify-end">
      <div className="absolute inset-0 bg-black/60" onClick={onClose} />
      <div className="relative flex h-full w-full max-w-lg flex-col overflow-y-auto border-l border-ink-600 bg-ink-900 p-5 shadow-2xl">
        <button onClick={onClose} className="absolute right-4 top-4 rounded-lg bg-ink-700 p-1.5 text-slate-300 hover:bg-ink-600">
          <X size={16} />
        </button>
        <div className="mb-2 flex flex-wrap items-center gap-1.5 pr-8">
          <CatBadge type={doc.doc_type} />
          {doc.region && <span className="rounded bg-ink-700 px-1.5 py-0.5 text-[10px] uppercase text-slate-400">{doc.region}</span>}
        </div>
        <h3 className="text-base font-bold text-white">{doc.title}</h3>
        <div className="mt-1 text-[11px] text-slate-500">
          {[doc.department, doc.ministry, doc.date].filter(Boolean).join(" · ")}
        </div>

        {doc.source_url && (
          <a href={doc.source_url} target="_blank" rel="noreferrer"
            className="mt-2 inline-flex w-fit items-center gap-1.5 rounded-lg bg-accent-600 px-3 py-1.5 text-xs font-semibold text-white hover:bg-accent-700">
            <ExternalLink size={13} /> {t("govintel.openSource")}
          </a>
        )}

        {doc.summary && (
          <p className="mt-3 text-sm leading-relaxed text-slate-300">{doc.summary}</p>
        )}
        {doc.body && doc.body !== doc.summary && (
          <p className="mt-2 text-xs leading-relaxed text-slate-400">{doc.body}</p>
        )}

        {/* AI summary */}
        <div className="mt-4 rounded-xl border border-ink-600 bg-ink-800/60 p-3">
          <div className="flex items-center justify-between">
            <span className="inline-flex items-center gap-1.5 text-xs font-semibold text-slate-200">
              <Sparkles size={13} className="text-accent" /> {t("govintel.aiSummary")}
            </span>
            <button onClick={onSummarize} disabled={summarizing}
              className="inline-flex items-center gap-1 rounded-md bg-accent-600 px-2.5 py-1 text-[11px] font-semibold text-white hover:bg-accent-700 disabled:opacity-40">
              {summarizing ? <Loader2 size={12} className="animate-spin" /> : <Sparkles size={12} />}
              {summary ? t("govintel.regenerate") : t("govintel.summarise")} ({lang})
            </button>
          </div>
          {summary && (
            <>
              <pre className="mt-2 whitespace-pre-wrap text-xs leading-relaxed text-slate-200">{summary.summary}</pre>
              {summary.disclaimer && <p className="mt-2 text-[10px] italic text-slate-500">{summary.disclaimer}</p>}
            </>
          )}
        </div>

        {/* related / cross-links */}
        <div className="mt-4">
          <div className="mb-1.5 text-xs font-semibold text-slate-300">{t("govintel.relatedDocs")}</div>
          {related === null ? (
            <div className="flex items-center gap-2 text-xs text-slate-500"><Loader2 size={13} className="animate-spin" /> {t("govintel.findingLinks")}</div>
          ) : related.length === 0 ? (
            <p className="text-xs text-slate-500">{t("govintel.noRelated")}</p>
          ) : (
            <div className="space-y-1.5">
              {related.map((r) => (
                <button key={r.id} onClick={() => onOpenRelated(r)}
                  className="flex w-full items-center gap-2 rounded-lg border border-ink-700 bg-ink-800/50 p-2 text-left hover:border-ink-500">
                  <CatBadge type={r.doc_type} />
                  <span className="flex-1 truncate text-xs text-slate-200">{r.title}</span>
                  <LinkBadge linkType={r.link_type} score={r.score} />
                </button>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
