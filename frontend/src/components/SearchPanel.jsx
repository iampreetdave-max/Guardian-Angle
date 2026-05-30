import { useRef, useState } from "react";
import { Search, Type, Boxes, Image as ImageIcon, ScanFace, Loader2, Layers } from "lucide-react";

const MODES = [
  { key: "text", label: "Text", icon: Type, ph: 'e.g. "person in red jacket near the gate"' },
  { key: "object", label: "Object", icon: Boxes, ph: "e.g. car, person, truck, motorcycle" },
  { key: "image", label: "Reference Image", icon: ImageIcon },
  { key: "face", label: "Suspect Face", icon: ScanFace },
];

const COMMON_OBJECTS = ["person", "car", "truck", "motorcycle", "bicycle", "bus", "backpack", "handbag"];

export default function SearchPanel({ onSearch, searching, faceEnabled }) {
  const [mode, setMode] = useState("text");
  const [text, setText] = useState("");
  const [file, setFile] = useState(null);
  // Group nearby frames into events. Default ON, except Object search where
  // you usually want every individual instance (e.g. count all the cars).
  const [group, setGroup] = useState(true);
  const fileRef = useRef(null);

  const current = MODES.find((m) => m.key === mode);
  const isImageMode = mode === "image" || mode === "face";

  const switchMode = (key) => {
    setMode(key);
    setFile(null);
    setGroup(key !== "object"); // object: show all instances by default
  };

  const submit = () => {
    if (isImageMode) {
      if (file) onSearch({ mode, file, group });
    } else if (text.trim()) {
      onSearch({ mode, query: text.trim(), group });
    }
  };

  return (
    <div className="rounded-xl border border-ink-600 bg-ink-800/70 p-4 shadow-lg backdrop-blur">
      {/* Mode tabs */}
      <div className="mb-3 flex flex-wrap gap-1.5">
        {MODES.map((m) => {
          const disabled = m.key === "face" && !faceEnabled;
          const active = mode === m.key;
          return (
            <button
              key={m.key}
              disabled={disabled}
              onClick={() => switchMode(m.key)}
              title={disabled ? "ArcFace model not available" : ""}
              className={`inline-flex items-center gap-1.5 rounded-lg px-3 py-1.5 text-xs font-medium transition ${
                active
                  ? "bg-accent-600 text-white"
                  : disabled
                  ? "cursor-not-allowed bg-ink-800 text-slate-600"
                  : "bg-ink-700 text-slate-300 hover:bg-ink-600"
              }`}
            >
              <m.icon size={14} />
              {m.label}
            </button>
          );
        })}
      </div>

      {/* Input */}
      {isImageMode ? (
        <div className="flex items-center gap-3">
          <button
            onClick={() => fileRef.current?.click()}
            className="flex flex-1 items-center gap-3 rounded-lg border border-dashed border-ink-500 bg-ink-900/50 px-4 py-3 text-left transition hover:border-accent"
          >
            <current.icon size={20} className="text-accent" />
            <div className="min-w-0">
              <div className="text-sm text-slate-200">
                {file ? file.name : `Upload ${current.label.toLowerCase()}`}
              </div>
              <div className="text-[11px] text-slate-500">
                {mode === "face"
                  ? "Match this person across all footage (ArcFace)"
                  : "Find frames that look like this image (CLIP)"}
              </div>
            </div>
          </button>
          {file && (
            <img
              src={URL.createObjectURL(file)}
              alt="ref"
              className="h-14 w-14 rounded-lg object-cover ring-1 ring-ink-500"
            />
          )}
          <input
            ref={fileRef}
            type="file"
            accept="image/*"
            className="hidden"
            onChange={(e) => setFile(e.target.files?.[0] || null)}
          />
          <button
            onClick={submit}
            disabled={!file || searching}
            className="flex items-center gap-2 rounded-lg bg-accent-600 px-5 py-3 text-sm font-semibold text-white transition hover:bg-accent-700 disabled:opacity-40"
          >
            {searching ? <Loader2 size={16} className="animate-spin" /> : <Search size={16} />}
            Search
          </button>
        </div>
      ) : (
        <div className="flex items-center gap-3">
          <div className="relative flex-1">
            <Search
              size={16}
              className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-500"
            />
            <input
              value={text}
              onChange={(e) => setText(e.target.value)}
              onKeyDown={(e) => e.key === "Enter" && submit()}
              placeholder={current.ph}
              className="w-full rounded-lg bg-ink-900/60 py-3 pl-10 pr-4 text-sm text-slate-100 outline-none ring-1 ring-ink-600 focus:ring-2 focus:ring-accent"
            />
          </div>
          <button
            onClick={submit}
            disabled={!text.trim() || searching}
            className="flex items-center gap-2 rounded-lg bg-accent-600 px-5 py-3 text-sm font-semibold text-white transition hover:bg-accent-700 disabled:opacity-40"
          >
            {searching ? <Loader2 size={16} className="animate-spin" /> : <Search size={16} />}
            Search
          </button>
        </div>
      )}

      {mode === "object" && (
        <div className="mt-3 flex flex-wrap gap-1.5">
          {COMMON_OBJECTS.map((o) => (
            <button
              key={o}
              onClick={() => {
                setText(o);
                onSearch({ mode: "object", query: o, group });
              }}
              className="rounded-full bg-ink-700 px-2.5 py-1 text-[11px] text-slate-300 transition hover:bg-ink-600"
            >
              {o}
            </button>
          ))}
        </div>
      )}

      {/* Group-moments toggle */}
      <div className="mt-3 flex items-center gap-2">
        <button
          onClick={() => setGroup((g) => !g)}
          className={`inline-flex items-center gap-1.5 rounded-lg px-2.5 py-1 text-[11px] font-medium transition ${
            group
              ? "bg-accent/15 text-accent"
              : "bg-ink-700 text-slate-400 hover:bg-ink-600"
          }`}
          title="When on, frames from the same camera within a few seconds are collapsed into one event. Turn off to see every matching frame/instance."
        >
          <Layers size={13} />
          {group ? "Grouping moments: ON" : "Grouping moments: OFF"}
        </button>
        <span className="text-[10px] text-slate-500">
          {group
            ? "collapses near-duplicate frames into events"
            : "shows every matching frame (find all instances)"}
        </span>
      </div>
    </div>
  );
}
