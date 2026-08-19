import { createContext, useCallback, useContext, useEffect, useMemo, useState } from "react";

import * as API from "../api";
import en from "./en";
import gu from "./gu";
import hi from "./hi";

/* Deliberately not react-i18next. The app needs three fixed languages, static
   strings and simple {placeholder} substitution — a context plus three plain
   objects does that in ~80 lines instead of pulling in a 40KB dependency and its
   plugin chain. If plurals or date/number localisation are ever needed, swap
   this module out; nothing outside it knows how lookup works. */

export const LANGUAGES = [
  { code: "en", label: "English", native: "English" },
  { code: "hi", label: "Hindi", native: "हिन्दी" },
  { code: "gu", label: "Gujarati", native: "ગુજરાતી" },
];

const DICTS = { en, hi, gu };
const STORAGE_KEY = "cityshield.lang";

const I18nCtx = createContext({ lang: "en", t: (k) => k, setLang: () => {} });

/** Resolve a dotted key against a dictionary. */
function lookup(dict, key) {
  return key.split(".").reduce((o, part) => (o == null ? undefined : o[part]), dict);
}

export function I18nProvider({ children, user }) {
  // Order matters: the signed-in user's saved preference wins, then whatever
  // this browser last used (so the login screen is already translated), then
  // English.
  const [lang, setLangState] = useState(
    () => user?.language || localStorage.getItem(STORAGE_KEY) || "en"
  );

  // A different user signing in on the same browser must get THEIR language,
  // not the previous user's.
  useEffect(() => {
    if (user?.language && user.language !== lang) setLangState(user.language);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [user?.id, user?.language]);

  useEffect(() => {
    localStorage.setItem(STORAGE_KEY, lang);
    document.documentElement.lang = lang;
  }, [lang]);

  const setLang = useCallback(
    (next) => {
      if (!DICTS[next]) return;
      setLangState(next);
      // Persist server-side so the choice follows the user to another machine.
      // Fire-and-forget: a failed save must never block the UI from switching.
      if (user?.id) API.updatePreferences({ language: next }).catch(() => {});
    },
    [user?.id]
  );

  const t = useCallback(
    (key, vars) => {
      // Fall back through the active language -> English -> the key itself, so a
      // missing translation degrades to readable English rather than a blank.
      let s = lookup(DICTS[lang], key);
      if (s === undefined) s = lookup(DICTS.en, key);
      if (s === undefined) {
        if (import.meta.env.DEV) console.warn(`[i18n] missing key: ${key}`);
        return key;
      }
      if (!vars) return s;
      return Object.keys(vars).reduce(
        (acc, k) => acc.replaceAll(`{${k}}`, String(vars[k])),
        s
      );
    },
    [lang]
  );

  const value = useMemo(() => ({ lang, setLang, t }), [lang, setLang, t]);
  return <I18nCtx.Provider value={value}>{children}</I18nCtx.Provider>;
}

export const useI18n = () => useContext(I18nCtx);
/** Shorthand for components that only need the translate function. */
export const useT = () => useContext(I18nCtx).t;
