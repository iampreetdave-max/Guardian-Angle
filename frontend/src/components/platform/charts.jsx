// Dependency-free chart primitives (SVG / CSS) styled with the CityShield
// palette. Kept tiny on purpose — no charting library, so the bundle stays lean
// and the dashboard works fully offline.

const PALETTE = ["#f4b23c", "#3b82f6", "#22c55e", "#ef4444", "#a855f7", "#14b8a6", "#f59e0b", "#64748b"];

// Horizontal labelled bars — good for category / status breakdowns.
export function BarList({ data, accent = "#f4b23c", empty = "No data yet" }) {
  if (!data || data.length === 0)
    return <p className="py-6 text-center text-xs text-slate-500">{empty}</p>;
  const max = Math.max(...data.map((d) => d.count), 1);
  return (
    <div className="space-y-2">
      {data.map((d) => (
        <div key={d.label} className="flex items-center gap-2">
          <span className="w-28 shrink-0 truncate text-xs capitalize text-slate-400" title={d.label}>
            {d.label}
          </span>
          <div className="h-4 flex-1 overflow-hidden rounded bg-ink-900/70">
            <div
              className="h-full rounded"
              style={{ width: `${(d.count / max) * 100}%`, backgroundColor: accent, minWidth: d.count ? "4px" : 0 }}
            />
          </div>
          <span className="w-8 shrink-0 text-right text-xs font-semibold tabular-nums text-slate-300">
            {d.count}
          </span>
        </div>
      ))}
    </div>
  );
}

// Donut with legend — good for case status / severity split.
export function Donut({ data, empty = "No data yet", size = 132 }) {
  const items = (data || []).filter((d) => d.count > 0);
  const total = items.reduce((s, d) => s + d.count, 0);
  if (total === 0)
    return <p className="py-6 text-center text-xs text-slate-500">{empty}</p>;

  const r = 54, c = 2 * Math.PI * r;
  let offset = 0;
  return (
    <div className="flex items-center gap-4">
      <svg width={size} height={size} viewBox="0 0 132 132" className="shrink-0 -rotate-90">
        {items.map((d, i) => {
          const frac = d.count / total;
          const seg = (
            <circle
              key={d.label}
              cx="66" cy="66" r={r} fill="none"
              stroke={PALETTE[i % PALETTE.length]} strokeWidth="16"
              strokeDasharray={`${frac * c} ${c}`} strokeDashoffset={-offset}
            />
          );
          offset += frac * c;
          return seg;
        })}
        <circle cx="66" cy="66" r="38" fill="#0a1124" />
      </svg>
      <div className="space-y-1.5">
        {items.map((d, i) => (
          <div key={d.label} className="flex items-center gap-2 text-xs">
            <span className="h-2.5 w-2.5 rounded-sm" style={{ backgroundColor: PALETTE[i % PALETTE.length] }} />
            <span className="capitalize text-slate-300">{d.label}</span>
            <span className="font-semibold tabular-nums text-slate-400">
              {d.count} ({Math.round((d.count / total) * 100)}%)
            </span>
          </div>
        ))}
      </div>
    </div>
  );
}

// Compact vertical bars for a time trend (e.g. last 14 days of complaints).
export function TrendBars({ data, accent = "#f4b23c", empty = "No data yet" }) {
  if (!data || data.length === 0)
    return <p className="py-6 text-center text-xs text-slate-500">{empty}</p>;
  const max = Math.max(...data.map((d) => d.count), 1);
  return (
    <div className="flex h-32 items-end gap-1">
      {data.map((d) => (
        <div key={d.date} className="group relative flex flex-1 flex-col items-center justify-end">
          <div
            className="w-full rounded-t transition-all"
            style={{ height: `${(d.count / max) * 100}%`, backgroundColor: accent, minHeight: d.count ? "3px" : "1px" }}
            title={`${d.date}: ${d.count}`}
          />
          <span className="mt-1 text-[8px] text-slate-600">{d.date.slice(8)}</span>
        </div>
      ))}
    </div>
  );
}
