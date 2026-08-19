import { useRef, useState } from "react";
import { Search, Type, Boxes, Image as ImageIcon, ScanFace, Loader2, Layers, Lightbulb } from "lucide-react";
import { useT } from "../i18n";

// Module-level, so labels/placeholders are stored as i18n KEYS and resolved with
// t() at the render site — a hook can't be called out here.
const MODES = [
  { key: "text", label: "vision.modeText", icon: Type, ph: "vision.phText" },
  { key: "object", label: "vision.modeObject", icon: Boxes, ph: "vision.phObject" },
  { key: "image", label: "vision.modeImage", icon: ImageIcon },
  { key: "face", label: "vision.modeFace", icon: ScanFace },
];

// Query values, not display text: CLIP/YOLO only understand English labels, so
// these stay untranslated in every language.
const COMMON_OBJECTS = ["person", "car", "truck", "motorcycle", "bicycle", "bus", "backpack", "handbag"];

// Object-ish nouns that hint the operator really wants per-object (region)
// search rather than mushy whole-frame text matching.
const OBJECT_WORDS = [
  "car", "cars", "truck", "van", "bus", "vehicle", "motorcycle", "motorbike",
  "bike", "bicycle", "scooter", "rickshaw", "auto", "person", "people", "man",
  "woman", "child", "bag", "backpack", "handbag", "suitcase", "phone", "laptop",
  "knife", "gun", "bottle", "dog", "cat", "umbrella",
];

export default function SearchPanel({ onSearch, searching, faceEnabled }) {
  const t = useT();
  const [mode, setMode] = useState("text");
  const [text, setText] = useState("");
  const [file, setFile] = useState(null);
  // Group nearby frames into events. Default ON, except Object search where
  // you usually want every individual instance (e.g. count all the cars).
  const [group, setGroup] = useState(true);
  // Region (instance) search: match individual detected objects, not whole
  // frames — so "red car" returns every car, not just the most prominent.
  const [perObject, setPerObject] = useState(false);
  const fileRef = useRef(null);

  const current = MODES.find((m) => m.key === mode);
  const isImageMode = mode === "image" || mode === "face";
  // Whole-frame text search is weak for a specific object; nudge toward the
  // precise region ("find every object") mode when the query reads like one.
  const looksLikeObject =
    mode === "text" &&
    !perObject &&
    text.trim() &&
    text.toLowerCase().split(/\W+/).some((w) => OBJECT_WORDS.includes(w));
  const runRegion = () => {
    setPerObject(true);
    if (text.trim()) onSearch({ mode: "region", query: text.trim(), group });
  };

  const switchMode = (key) => {
    setMode(key);
    setFile(null);
    setGroup(key !== "object"); // object: show all instances by default
  };

  const submit = () => {
    if (isImageMode) {
      if (file) onSearch({ mode, file, group });
    } else if (text.trim()) {
      const m = mode === "text" && perObject ? "region" : mode;
      onSearch({ mode: m, query: text.trim(), group });
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
              title={disabled ? t("vision.faceUnavailable") : ""}
              className={`inline-flex items-center gap-1.5 rounded-lg px-3 py-1.5 text-xs font-medium transition ${
                active
                  ? "bg-accent-600 text-white"
                  : disabled
                  ? "cursor-not-allowed bg-ink-800 text-slate-600"
                  : "bg-ink-700 text-slate-300 hover:bg-ink-600"
              }`}
            >
              <m.icon size={14} />
              {t(m.label)}
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
                {file
                  ? file.name
                  : t("vision.uploadWhat", { what: t(current.label).toLowerCase() })}
              </div>
              <div className="text-[11px] text-slate-500">
                {mode === "face" ? t("vision.faceHint") : t("vision.imageHint")}
              </div>
            </div>
          </button>
          {file && (
            <img
              src={URL.createObjectURL(file)}
              alt={t("vision.refAlt")}
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
            {t("common.search")}
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
              placeholder={t(current.ph)}
              className="w-full rounded-lg bg-ink-900/60 py-3 pl-10 pr-4 text-sm text-slate-100 outline-none ring-1 ring-ink-600 focus:ring-2 focus:ring-accent"
            />
          </div>
          <button
            onClick={submit}
            disabled={!text.trim() || searching}
            className="flex items-center gap-2 rounded-lg bg-accent-600 px-5 py-3 text-sm font-semibold text-white transition hover:bg-accent-700 disabled:opacity-40"
          >
            {searching ? <Loader2 size={16} className="animate-spin" /> : <Search size={16} />}
            {t("common.search")}
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

      {/* Proactive nudge: query looks like a specific object → region search is far more precise */}
      {looksLikeObject && (
        <div className="mt-3 flex flex-wrap items-center gap-2 rounded-lg border border-accent/30 bg-accent/10 px-3 py-2 text-[11px] text-slate-300">
          <Lightbulb size={13} className="text-accent" />
          <span>
            {t("vision.nudgeLead")}{" "}
            <span className="font-semibold text-accent">{t("vision.findEveryObject")}</span>{" "}
            {t("vision.nudgeTail")}
          </span>
          <button
            onClick={runRegion}
            className="ml-auto inline-flex items-center gap-1.5 rounded-md bg-accent-600 px-2.5 py-1 font-semibold text-white transition hover:bg-accent-700"
          >
            <Boxes size={12} /> {t("vision.findEveryObject")}
          </button>
        </div>
      )}

      {/* Toggles */}
      <div className="mt-3 flex flex-wrap items-center gap-2">
        {mode === "text" && (
          <button
            onClick={() => setPerObject((p) => !p)}
            className={`inline-flex items-center gap-1.5 rounded-lg px-2.5 py-1 text-[11px] font-medium transition ${
              perObject
                ? "bg-signal-green/15 text-signal-green"
                : "bg-ink-700 text-slate-400 hover:bg-ink-600"
            }`}
            title={t("vision.perObjectTitle")}
          >
            <Boxes size={13} />
            {perObject ? t("vision.perObjectOn") : t("vision.perObjectOff")}
          </button>
        )}
        {!perObject && (
          <button
            onClick={() => setGroup((g) => !g)}
            className={`inline-flex items-center gap-1.5 rounded-lg px-2.5 py-1 text-[11px] font-medium transition ${
              group
                ? "bg-accent/15 text-accent"
                : "bg-ink-700 text-slate-400 hover:bg-ink-600"
            }`}
            title={t("vision.groupTitle")}
          >
            <Layers size={13} />
            {group ? t("vision.groupOn") : t("vision.groupOff")}
          </button>
        )}
        <span className="text-[10px] text-slate-500">
          {perObject
            ? t("vision.hintPerObject")
            : group
            ? t("vision.hintGroup")
            : t("vision.hintAll")}
        </span>
      </div>
    </div>
  );
}
