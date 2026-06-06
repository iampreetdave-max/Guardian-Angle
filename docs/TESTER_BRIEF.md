# CityShield / VisionScan — Reviewer Brief

Thanks for taking a fresh look before we submit to the **Kanad S.H.I.E.L.D. 2026**
hackathon (Cyber Crime Branch, Ahmedabad). ~20–30 minutes is plenty.

## What it is (in 3 lines)
An AI policing platform for the Cyber Crime Branch. It does **GIS crime-hotspot
mapping + predictive patrol routing**, **always-on CCTV anomaly detection**
(fire/smoke/accident/weapon/violence), **structured cyber-fraud intake**, and
**AI legal-document drafting** — one platform answering five problem statements.
It runs live, on CPU, offline-capable.

## How to get in
**Live site (no install):** https://visionscan.centralindia.cloudapp.azure.com

| Role | Email | Password |
|---|---|---|
| Admin | `admin@city.gov` | `admin123` |
| Team lead | `lead@city.gov` | `lead123` |
| Officer | `officer@city.gov` | `officer123` |
| Citizen | `citizen@example.com` | `citizen123` |

**Test footage** (download a clip to upload): https://drive.google.com/drive/folders/1mHoekSVX4ytmBEBaCnFrutMljqKxfmiz

## What to try (≈6 clicks per feature)

1. **GIS hotspots & predictions** — log in as **officer** → *City Map*.
   - Look at the red hotspot circles over Ahmedabad.
   - Expand a hotspot → **"Why this hotspot?"** (should break the score into parts).
   - Open the **Accuracy panel** (should show hit-rate / PAI / surge detection).
   - Toggle the **Cyber-fraud** layer (map should shift; ₹-loss headline).
   - Generate a **patrol route**; try the **Export CSV** buttons.
2. **CCTV Anomaly Watch** — *VisionScan → Upload* a clip from the Drive folder
   (try `fire/fire_highrise_shanghai_01.ogv`). Wait ~30–90 s (CPU), then check
   *Live Alerts* — it should raise the matching alert. Bonus: upload a `normal/`
   clip → it should raise **nothing** (false-alarm control).
3. **CrimeGPT** — *CrimeGPT* tab → pick a case → add a party/seizure →
   **Suggest sections** (should propose BNS/BNSS) → **Generate** a document
   (downloads a branded PDF).
4. **Cyber complaint (citizen)** — log in as **citizen** → file a complaint →
   toggle **Cybercrime** → pick "UPI/OTP fraud", enter an amount + "hours ago"
   ≤ 24 → a red **"call 1930 — golden hour"** banner should appear.
5. **GovIntel** — *Legal Feed* → search e.g. "pension" / "cyber" → check
   filters, related documents, bookmark/save.

## What feedback helps most
- **Bugs / crashes / broken links** — anything that errors or looks broken.
- **Confusing UX** — where did you get lost, what wasn't obvious?
- **Anything that looks fake or overclaimed** — we want it to be defensible to a
  police/technical judge. Flag any number or claim that feels unsupported.
- **Gaps vs the brief** — does each feature above actually do what it says?
- First-impression: does it look credible / polished?

## Honest caveats (so nothing surprises you)
- All data is **synthetic** demo data (no real people/cases). Crime figures are
  editorial estimates from public sources — it's a prototype, not live police data.
- **CPU inference**: an uploaded clip takes ~30–90 s to process before alerts show.
- The map needs internet for OpenStreetMap tiles; data layers still work offline.
- The GitHub source repo is **private** until submission day.
- Optional AI (Gemini) is off by default — the app runs fully offline; legal
  drafting falls back to grounded templates.

Reply with notes per feature (or just "feature N: OK / issue: …"). Anything you
flag, we'll fix before the 20 June submission. Thank you!
