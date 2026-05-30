export const fmtDuration = (sec) => {
  if (!sec && sec !== 0) return "—";
  const s = Math.floor(sec);
  const h = Math.floor(s / 3600);
  const m = Math.floor((s % 3600) / 60);
  const ss = s % 60;
  return [h, m, ss].map((v) => String(v).padStart(2, "0")).join(":");
};

export const scorePct = (score) => `${Math.round(score * 100)}%`;

export const scoreColor = (score) => {
  if (score >= 0.6) return "text-signal-green";
  if (score >= 0.4) return "text-signal-amber";
  return "text-slate-400";
};

export const statusBadge = (status) => {
  switch (status) {
    case "ready":
      return { label: "Ready", cls: "bg-signal-green/15 text-signal-green" };
    case "processing":
      return { label: "Processing", cls: "bg-accent/15 text-accent animate-pulse" };
    case "pending":
      return { label: "Queued", cls: "bg-signal-amber/15 text-signal-amber" };
    case "error":
      return { label: "Error", cls: "bg-signal-red/15 text-signal-red" };
    default:
      return { label: status, cls: "bg-ink-600 text-slate-300" };
  }
};
