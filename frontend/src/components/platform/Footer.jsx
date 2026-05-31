import { useState } from "react";
import { Phone, X, ShieldAlert } from "lucide-react";

// National helpline numbers (verified, India-wide).
const HELPLINES = [
  { label: "Cyber Crime / Financial Fraud", num: "1930", hot: true },
  { label: "Emergency (All)", num: "112", hot: true },
  { label: "Police", num: "100" },
  { label: "Women Helpline", num: "1091" },
  { label: "Child Helpline", num: "1098" },
  { label: "Senior Citizen (Elderline)", num: "14567" },
  { label: "Ambulance", num: "108" },
  { label: "Fire", num: "101" },
];

const PAGES = {
  about: {
    title: "About CityShield",
    body: (
      <>
        <p>
          CityShield is a unified AI-assisted policing platform developed for the
          <b> Cyber Crime Branch, Ahmedabad City Police</b>. It brings the full
          investigative lifecycle — <b>Detect → Investigate → Prosecute</b> — into
          one secure, offline-capable system.
        </p>
        <ul>
          <li><b>VisionScan</b> — AI analysis of CCTV footage (natural-language, reference-image, face and object search).</li>
          <li><b>Arbiter</b> — legal intelligence over IPC, IT Act 2000 and CrPC: FIR drafting, section lookup, and citizen Q&amp;A.</li>
          <li><b>Case Management</b> — complaints, cases, evidence governance, and a citizen grievance portal with role-based access.</li>
        </ul>
        <p className="text-slate-400">
          Built for the KANAD S.H.I.E.L.D. 2026 Cybersecurity Hackathon. All
          processing can run on-premise; case data never leaves the department's
          systems.
        </p>
      </>
    ),
  },
  contact: {
    title: "Contact Us",
    body: (
      <>
        <p><b>Cyber Crime Branch, Ahmedabad City Police</b></p>
        <p>Police Bhavan, Shahibaug, Ahmedabad, Gujarat 380004</p>
        <p>Cyber Crime Helpline: <b>1930</b> · Emergency: <b>112</b></p>
        <p>National Cyber Crime Reporting Portal:{" "}
          <a className="text-accent" href="https://cybercrime.gov.in" target="_blank" rel="noreferrer">cybercrime.gov.in</a>
        </p>
        <p className="text-slate-400">For platform/technical queries, contact your station's CityShield administrator.</p>
      </>
    ),
  },
  faq: {
    title: "Help & FAQ",
    body: (
      <>
        <p><b>How do I report a cyber crime?</b><br/>Citizens can register a complaint from the Complaints tab after signing in, or call <b>1930</b> for financial fraud. For emergencies dial <b>112</b>.</p>
        <p><b>Who can see my complaint?</b><br/>Only the assigned police team and administrators. You can track your complaint's status and the official response from your dashboard.</p>
        <p><b>When can I view my case?</b><br/>Once the investigating team enables citizen visibility, you can view progress and shared evidence, and send one message to the team.</p>
        <p><b>Is my data secure?</b><br/>Access is role-based and every action is audit-logged. The platform can run fully offline within the department.</p>
      </>
    ),
  },
  privacy: {
    title: "Privacy Policy",
    body: (
      <>
        <p>CityShield collects only the information necessary to register and investigate complaints and cases (your name, contact details, and the details you provide).</p>
        <ul>
          <li>Data is accessible only to authorised police personnel on a need-to-know, role-based basis.</li>
          <li>Evidence and case data are stored within the department's systems and are not shared with third parties except as required by law.</li>
          <li>All access and changes are recorded in a tamper-evident audit log.</li>
          <li>Citizens may request the status of their own complaints and cases at any time.</li>
        </ul>
        <p className="text-slate-400">This is a hackathon prototype; production deployments follow the IT Act 2000, the DPDP Act 2023, and applicable departmental data-handling rules.</p>
      </>
    ),
  },
  terms: {
    title: "Terms of Use & Disclaimer",
    body: (
      <>
        <p>Access to CityShield is restricted to authorised users. Misuse of the platform or unauthorised access is an offence under the IT Act 2000.</p>
        <ul>
          <li>AI-generated outputs (search results, FIR drafts, legal suggestions) are <b>investigative aids only</b> and must be verified by an officer or qualified legal professional before any action.</li>
          <li>VisionScan is intended for footage the department is authorised to process. Accessing private or unsecured cameras without authorisation is illegal.</li>
          <li>The platform is provided "as is" for the hackathon demonstration without warranty.</li>
        </ul>
      </>
    ),
  },
  accessibility: {
    title: "Accessibility Statement",
    body: (
      <>
        <p>CityShield aims to conform to WCAG 2.1 AA and the Guidelines for Indian Government Websites (GIGW).</p>
        <ul>
          <li>Keyboard navigable with visible focus indicators.</li>
          <li>Colour is never the only means of conveying information (icons/labels accompany status colours).</li>
          <li>Respects the operating-system "reduce motion" setting.</li>
          <li>Text scales with browser zoom; targets meet minimum size guidance.</li>
        </ul>
        <p className="text-slate-400">Report accessibility issues to your station administrator so we can improve.</p>
      </>
    ),
  },
};

export default function Footer() {
  const [page, setPage] = useState(null);
  const links = [
    ["about", "About"], ["contact", "Contact"], ["faq", "Help / FAQ"],
    ["privacy", "Privacy Policy"], ["terms", "Terms & Disclaimer"],
    ["accessibility", "Accessibility"],
  ];

  return (
    <footer className="border-t border-ink-700 bg-ink-900/80">
      <div className="tricolor-bar" />
      {/* helpline strip */}
      <div className="border-b border-ink-800 bg-signal-red/5 px-5 py-2">
        <div className="mx-auto flex max-w-6xl flex-wrap items-center gap-x-4 gap-y-1 text-[11px]">
          <span className="inline-flex items-center gap-1.5 font-semibold text-signal-red">
            <ShieldAlert size={13} /> Helplines:
          </span>
          {HELPLINES.map((h) => (
            <a key={h.num} href={`tel:${h.num}`}
              className={`inline-flex items-center gap-1 ${h.hot ? "text-accent" : "text-slate-400"} hover:underline`}>
              <Phone size={10} /> {h.label} <b className="font-mono">{h.num}</b>
            </a>
          ))}
        </div>
      </div>
      {/* links + credit */}
      <div className="mx-auto flex max-w-6xl flex-col items-center justify-between gap-2 px-5 py-3 text-[11px] text-slate-500 sm:flex-row">
        <div className="flex items-center gap-2">
          <img src="/logo.png" alt="Ahmedabad City Police" className="h-7 w-7 object-contain" />
          <span>© {new Date().getFullYear()} Cyber Crime Branch, Ahmedabad City Police · CityShield</span>
        </div>
        <nav className="flex flex-wrap items-center gap-x-3 gap-y-1">
          {links.map(([k, label]) => (
            <button key={k} onClick={() => setPage(k)} className="hover:text-accent hover:underline">{label}</button>
          ))}
        </nav>
      </div>

      {page && (
        <div className="fixed inset-0 z-[60] flex items-center justify-center bg-black/80 p-4" onClick={() => setPage(null)}>
          <div className="max-h-[85vh] w-full max-w-2xl overflow-y-auto rounded-xl border border-ink-500 bg-ink-800 shadow-2xl" onClick={(e) => e.stopPropagation()}>
            <div className="tricolor-bar" />
            <div className="flex items-center justify-between border-b border-ink-600 px-5 py-3">
              <h3 className="font-serif text-lg font-semibold text-white">{PAGES[page].title}</h3>
              <button onClick={() => setPage(null)} className="text-slate-400 hover:text-white"><X size={20} /></button>
            </div>
            <div className="space-y-3 p-5 text-sm leading-relaxed text-slate-300 [&_a]:underline [&_b]:text-slate-100 [&_li]:ml-4 [&_li]:list-disc [&_ul]:space-y-1">
              {PAGES[page].body}
            </div>
          </div>
        </div>
      )}
    </footer>
  );
}
