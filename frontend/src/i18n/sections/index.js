/* One file per UI section, each exporting { en, hi, gu } for its own keys.

   Structured this way so a section can be translated in isolation without
   touching a shared 500-line dictionary — which also means several people (or
   agents) can work in parallel without colliding. Add a section here and it is
   live in all three languages. */
import common from "./common";
import nav from "./nav";
import login from "./login";
import header from "./header";
import vision from "./vision";
import alerts from "./alerts";
import citymap from "./citymap";
import dashboard from "./dashboard";
import cases from "./cases";
import complaints from "./complaints";
import arbiter from "./arbiter";
import crimegpt from "./crimegpt";
import govintel from "./govintel";
import admin from "./admin";
import enums from "./enums";

export const SECTIONS = {
  common, nav, login, header, vision, alerts, citymap,
  dashboard, cases, complaints, arbiter, crimegpt, govintel, admin, enums,
};

/** Build a flat per-language dictionary namespaced by section name. */
export function buildDict(lang) {
  const out = {};
  for (const [name, section] of Object.entries(SECTIONS)) {
    out[name] = section[lang] || section.en || {};
  }
  return out;
}
