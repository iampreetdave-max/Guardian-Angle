import { useEffect, useState } from "react";
import { Bell } from "lucide-react";
import * as API from "../../api";

export default function NotificationBell() {
  const [data, setData] = useState({ unread: 0, items: [] });
  const [open, setOpen] = useState(false);

  const refresh = () => API.getNotifications().then(setData).catch(() => {});
  useEffect(() => {
    refresh();
    const id = setInterval(refresh, 5000);
    return () => clearInterval(id);
  }, []);

  const openPanel = async () => {
    setOpen((o) => !o);
    if (!open && data.unread > 0) {
      await API.markNotificationsRead().catch(() => {});
      refresh();
    }
  };

  return (
    <div className="relative">
      <button onClick={openPanel} className="relative rounded-lg bg-ink-700 p-2 text-slate-300 hover:bg-ink-600">
        <Bell size={16} />
        {data.unread > 0 && (
          <span className="absolute -right-1 -top-1 flex h-4 min-w-4 items-center justify-center rounded-full bg-signal-red px-1 text-[10px] font-bold text-white">
            {data.unread}
          </span>
        )}
      </button>
      {open && (
        <div className="absolute right-0 z-50 mt-2 max-h-96 w-80 overflow-y-auto rounded-xl border border-ink-600 bg-ink-800 p-2 shadow-2xl">
          <div className="px-2 py-1 text-xs font-semibold text-slate-400">Notifications</div>
          {data.items.length === 0 && (
            <p className="px-2 py-4 text-center text-xs text-slate-500">No notifications</p>
          )}
          {data.items.map((n) => (
            <div key={n.id} className={`rounded-lg p-2 text-xs ${n.read ? "text-slate-400" : "bg-ink-700/50 text-slate-200"}`}>
              <div className="font-medium">{n.message}</div>
              <div className="mt-0.5 text-[10px] text-slate-500">{n.type} · {n.created_at}</div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
