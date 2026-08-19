import { useEffect, useRef, useState } from "react";
import { Languages, Check } from "lucide-react";

import { LANGUAGES, useI18n } from "../i18n";

/** Header control for the signed-in user's interface language.

    The choice is per user, not per deployment: it saves to their account so it
    follows them to another machine, and falls back to this browser's last
    choice when signed out (which is why the login screen is already
    translated). */
export default function LanguageSwitcher({ compact = false }) {
  const { lang, setLang, t } = useI18n();
  const [open, setOpen] = useState(false);
  const ref = useRef(null);

  useEffect(() => {
    if (!open) return;
    const onDown = (e) => {
      if (ref.current && !ref.current.contains(e.target)) setOpen(false);
    };
    const onKey = (e) => e.key === "Escape" && setOpen(false);
    document.addEventListener("mousedown", onDown);
    document.addEventListener("keydown", onKey);
    return () => {
      document.removeEventListener("mousedown", onDown);
      document.removeEventListener("keydown", onKey);
    };
  }, [open]);

  const current = LANGUAGES.find((l) => l.code === lang) || LANGUAGES[0];

  return (
    <div className="relative" ref={ref}>
      <button
        onClick={() => setOpen((v) => !v)}
        aria-label={t("common.language")}
        aria-expanded={open}
        title={`${t("common.language")}: ${current.native}`}
        className="inline-flex h-9 items-center gap-1.5 rounded-lg bg-ink-700 px-2.5 text-xs
                   font-medium text-slate-300 transition hover:bg-ink-600 hover:text-slate-100"
      >
        <Languages size={15} className="shrink-0" />
        <span className={compact ? "hidden" : "hidden whitespace-nowrap sm:inline"}>
          {current.native}
        </span>
      </button>

      {open && (
        <div
          role="menu"
          aria-label={t("common.language")}
          className="absolute right-0 top-full z-50 mt-2 w-44 overflow-hidden rounded-xl
                     border border-ink-600 bg-ink-800 py-1 shadow-2xl"
        >
          {LANGUAGES.map((l) => (
            <button
              key={l.code}
              role="menuitemradio"
              aria-checked={l.code === lang}
              onClick={() => {
                setLang(l.code);
                setOpen(false);
              }}
              className={`flex w-full items-center justify-between gap-3 px-3 py-2 text-left text-sm
                          transition hover:bg-ink-700 ${
                            l.code === lang ? "text-accent" : "text-slate-300"
                          }`}
            >
              <span>
                <span className="font-medium">{l.native}</span>
                {l.native !== l.label && (
                  <span className="ml-2 text-[11px] text-slate-500">{l.label}</span>
                )}
              </span>
              {l.code === lang && <Check size={14} className="shrink-0" />}
            </button>
          ))}
        </div>
      )}
    </div>
  );
}
