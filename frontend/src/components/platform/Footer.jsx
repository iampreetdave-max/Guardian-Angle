import { useState } from "react";
import { Phone, X, ShieldAlert } from "lucide-react";
import { useT } from "../../i18n";

/* HELPLINES and PAGES live at module level, so they hold translation KEYS, not
   text — hooks cannot be called out here. The component passes `t` in. */

// National helpline numbers (verified, India-wide).
const HELPLINES = [
  { key: "hlCyber", num: "1930", hot: true },
  { key: "hlEmergency", num: "112", hot: true },
  { key: "hlPolice", num: "100" },
  { key: "hlWomen", num: "1091" },
  { key: "hlChild", num: "1098" },
  { key: "hlSenior", num: "14567" },
  { key: "hlAmbulance", num: "108" },
  { key: "hlFire", num: "101" },
];

const PAGES = {
  about: {
    title: "common.footer.aboutTitle",
    body: (t) => (
      <>
        <p>
          {t("common.footer.aboutP1a")}
          <b>{t("common.org")}</b>
          {t("common.footer.aboutP1b")}
          <b>{t("common.footer.aboutCycle")}</b>
          {t("common.footer.aboutP1c")}
        </p>
        <ul>
          <li><b>VisionScan</b> {t("common.footer.aboutVision")}</li>
          <li><b>Arbiter</b> {t("common.footer.aboutArbiter")}</li>
          <li><b>{t("common.footer.aboutCasesLabel")}</b> {t("common.footer.aboutCases")}</li>
        </ul>
        <p className="text-slate-400">{t("common.footer.aboutNote")}</p>
      </>
    ),
  },
  contact: {
    title: "common.footer.contactTitle",
    body: (t) => (
      <>
        <p><b>{t("common.org")}</b></p>
        <p>{t("common.footer.contactAddr")}</p>
        <p>{t("common.footer.contactCyber")} <b>1930</b> · {t("common.footer.contactEmergency")} <b>112</b></p>
        <p>{t("common.footer.contactPortal")}{" "}
          <a className="text-accent" href="https://cybercrime.gov.in" target="_blank" rel="noreferrer">cybercrime.gov.in</a>
        </p>
        <p className="text-slate-400">{t("common.footer.contactTech")}</p>
      </>
    ),
  },
  faq: {
    title: "common.footer.faqTitle",
    body: (t) => (
      <>
        <p><b>{t("common.footer.faqQ1")}</b><br/>{t("common.footer.faqA1a")}<b>1930</b>{t("common.footer.faqA1b")}<b>112</b>{t("common.footer.faqA1c")}</p>
        <p><b>{t("common.footer.faqQ2")}</b><br/>{t("common.footer.faqA2")}</p>
        <p><b>{t("common.footer.faqQ3")}</b><br/>{t("common.footer.faqA3")}</p>
        <p><b>{t("common.footer.faqQ4")}</b><br/>{t("common.footer.faqA4")}</p>
      </>
    ),
  },
  privacy: {
    title: "common.footer.privacyTitle",
    body: (t) => (
      <>
        <p>{t("common.footer.privacyP1")}</p>
        <ul>
          <li>{t("common.footer.privacyLi1")}</li>
          <li>{t("common.footer.privacyLi2")}</li>
          <li>{t("common.footer.privacyLi3")}</li>
          <li>{t("common.footer.privacyLi4")}</li>
        </ul>
        <p className="text-slate-400">{t("common.footer.privacyNote")}</p>
      </>
    ),
  },
  terms: {
    title: "common.footer.termsTitle",
    body: (t) => (
      <>
        <p>{t("common.footer.termsP1")}</p>
        <ul>
          <li>{t("common.footer.termsLi1a")}<b>{t("common.footer.termsLi1b")}</b>{t("common.footer.termsLi1c")}</li>
          <li>{t("common.footer.termsLi2")}</li>
          <li>{t("common.footer.termsLi3")}</li>
        </ul>
      </>
    ),
  },
  accessibility: {
    title: "common.footer.a11yTitle",
    body: (t) => (
      <>
        <p>{t("common.footer.a11yP1")}</p>
        <ul>
          <li>{t("common.footer.a11yLi1")}</li>
          <li>{t("common.footer.a11yLi2")}</li>
          <li>{t("common.footer.a11yLi3")}</li>
          <li>{t("common.footer.a11yLi4")}</li>
        </ul>
        <p className="text-slate-400">{t("common.footer.a11yNote")}</p>
      </>
    ),
  },
};

export default function Footer() {
  const t = useT();
  const [page, setPage] = useState(null);
  // page id doubles as its label key
  const links = ["about", "contact", "faq", "privacy", "terms", "accessibility"];

  return (
    <footer className="border-t border-ink-700 bg-ink-900/80">
      <div className="tricolor-bar" />
      {/* helpline strip */}
      <div className="border-b border-ink-800 bg-signal-red/5 px-5 py-2">
        <div className="mx-auto flex max-w-6xl flex-wrap items-center gap-x-4 gap-y-1 text-[11px]">
          <span className="inline-flex items-center gap-1.5 font-semibold text-signal-red">
            <ShieldAlert size={13} /> {t("common.footer.helplines")}
          </span>
          {HELPLINES.map((h) => (
            <a key={h.num} href={`tel:${h.num}`}
              className={`inline-flex items-center gap-1 ${h.hot ? "text-accent" : "text-slate-400"} hover:underline`}>
              <Phone size={10} /> {t(`common.footer.${h.key}`)} <b className="font-mono">{h.num}</b>
            </a>
          ))}
        </div>
      </div>
      {/* links + credit */}
      <div className="mx-auto flex max-w-6xl flex-col items-center justify-between gap-2 px-5 py-3 text-[11px] text-slate-500 sm:flex-row">
        <div className="flex items-center gap-2">
          <img src="/logo.png" alt={t("common.logoAlt")} className="h-7 w-7 object-contain" />
          <span>{t("common.footer.copyright", { year: new Date().getFullYear() })}</span>
        </div>
        <nav className="flex flex-wrap items-center gap-x-3 gap-y-1">
          {links.map((k) => (
            <button key={k} onClick={() => setPage(k)} className="hover:text-accent hover:underline">{t(`common.footer.${k}`)}</button>
          ))}
        </nav>
      </div>

      {page && (
        <div className="fixed inset-0 z-[60] flex items-center justify-center bg-black/80 p-4" onClick={() => setPage(null)}>
          <div className="max-h-[85vh] w-full max-w-2xl overflow-y-auto rounded-xl border border-ink-500 bg-ink-800 shadow-2xl" onClick={(e) => e.stopPropagation()}>
            <div className="tricolor-bar" />
            <div className="flex items-center justify-between border-b border-ink-600 px-5 py-3">
              <h3 className="font-serif text-lg font-semibold text-white">{t(PAGES[page].title)}</h3>
              <button onClick={() => setPage(null)} className="text-slate-400 hover:text-white" aria-label={t("common.close")}><X size={20} /></button>
            </div>
            <div className="space-y-3 p-5 text-sm leading-relaxed text-slate-300 [&_a]:underline [&_b]:text-slate-100 [&_li]:ml-4 [&_li]:list-disc [&_ul]:space-y-1">
              {PAGES[page].body(t)}
            </div>
          </div>
        </div>
      )}
    </footer>
  );
}
