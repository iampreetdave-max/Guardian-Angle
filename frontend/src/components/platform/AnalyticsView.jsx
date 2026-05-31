import { useEffect, useState } from "react";
import {
  BarChart3, Loader2, Megaphone, FolderOpen, CheckCircle2, Clock,
  Star, FileVideo, Layers, ShieldAlert,
} from "lucide-react";
import * as API from "../../api";
import { BarList, Donut, TrendBars } from "./charts";

function Kpi({ icon: Icon, label, value, suffix, tint = "text-accent" }) {
  return (
    <div className="rounded-lg border border-ink-700 bg-ink-800/50 p-4">
      <div className="flex items-center gap-2 text-slate-400">
        <Icon size={15} className={tint} />
        <span className="text-[11px] uppercase tracking-wide">{label}</span>
      </div>
      <div className="mt-1.5 text-2xl font-bold tabular-nums text-white">
        {value}
        {suffix && <span className="ml-1 text-sm font-normal text-slate-500">{suffix}</span>}
      </div>
    </div>
  );
}

function Card({ title, icon: Icon, children }) {
  return (
    <div className="rounded-lg border border-ink-700 bg-ink-800/50 p-5">
      <div className="mb-4 flex items-center gap-2">
        {Icon && <Icon size={15} className="text-accent" />}
        <h3 className="text-sm font-semibold text-slate-200">{title}</h3>
      </div>
      {children}
    </div>
  );
}

export default function AnalyticsView() {
  const [data, setData] = useState(null);
  const [error, setError] = useState(null);

  useEffect(() => {
    let alive = true;
    const load = () =>
      API.getAnalytics()
        .then((d) => alive && setData(d))
        .catch((e) => alive && setError(e?.response?.data?.detail || "Failed to load analytics"));
    load();
    const id = setInterval(load, 15000); // keep the command view live
    return () => { alive = false; clearInterval(id); };
  }, []);

  if (error)
    return (
      <div className="mx-auto max-w-6xl p-5">
        <div className="rounded-lg border border-signal-red/30 bg-signal-red/10 p-4 text-sm text-signal-red">{error}</div>
      </div>
    );
  if (!data)
    return (
      <div className="flex items-center justify-center py-24 text-slate-400">
        <Loader2 className="animate-spin text-accent" size={26} />
      </div>
    );

  const k = data.kpis;
  return (
    <div className="mx-auto max-w-6xl p-4 sm:p-5">
      <div className="mb-4 flex items-center gap-3">
        <BarChart3 size={20} className="text-accent" />
        <h2 className="text-lg font-bold text-white">Command Dashboard</h2>
        <span className="ml-auto text-[11px] text-slate-500">live · refreshes every 15s</span>
      </div>

      {/* KPI grid */}
      <div className="grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-6">
        <Kpi icon={Megaphone} label="Complaints" value={k.total_complaints} />
        <Kpi icon={FolderOpen} label="Open cases" value={k.open_cases} tint="text-signal-amber" />
        <Kpi icon={CheckCircle2} label="Closed" value={k.closed_cases} tint="text-signal-green" />
        <Kpi icon={Clock} label="Avg resolve" value={k.avg_resolution_hours} suffix="h" tint="text-blue-400" />
        <Kpi icon={Star} label="Avg rating" value={k.avg_rating || "—"} suffix={k.n_ratings ? `/5 (${k.n_ratings})` : ""} />
        <Kpi icon={Layers} label="Evidence" value={k.total_evidence} tint="text-purple-400" />
      </div>

      {/* VisionScan footprint */}
      <div className="mt-3 grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-6">
        <Kpi icon={FileVideo} label="Feeds" value={k.total_videos} tint="text-slate-300" />
        <Kpi icon={Layers} label="Indexed frames" value={k.indexed_frames} tint="text-slate-300" />
        <Kpi icon={ShieldAlert} label="Total cases" value={k.total_cases} tint="text-slate-300" />
        <Kpi icon={Megaphone} label="Users" value={k.total_users} tint="text-slate-300" />
      </div>

      {/* Charts */}
      <div className="mt-4 grid grid-cols-1 gap-4 lg:grid-cols-2">
        <Card title="Complaints — last 14 days" icon={BarChart3}>
          <TrendBars data={data.complaints_over_time} />
        </Card>
        <Card title="Cases by status" icon={FolderOpen}>
          <Donut data={data.cases_by_status} />
        </Card>
        <Card title="Complaints by category" icon={Megaphone}>
          <BarList data={data.complaints_by_category} />
        </Card>
        <Card title="Complaints by status" icon={CheckCircle2}>
          <BarList data={data.complaints_by_status} accent="#3b82f6" />
        </Card>
        <Card title="Cases by severity" icon={ShieldAlert}>
          <BarList data={data.cases_by_severity} accent="#ef4444" />
        </Card>
        <Card title="Top complaint locations" icon={FolderOpen}>
          <BarList data={data.top_locations} accent="#22c55e" />
        </Card>
      </div>
    </div>
  );
}
