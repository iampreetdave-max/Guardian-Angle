# Screenshots & GIFs Needed — 20-minute capture checklist

Goal: capture the ~10 stills + 3 GIFs that the README hero, the 5 proposal docs,
and the [`JUDGE_ONEPAGER.md`](JUDGE_ONEPAGER.md) reference. **Save every file under
`docs/assets/`** with the exact filename below so the doc links resolve.

**Setup once before you start (5 min):**
- `docker compose up -d` (or `start.ps1`), open `http://localhost:8080`.
- Have 2–3 short clips **already processed** with distinct `camera_id`s
  (e.g. CAM-Gate, CAM-Lobby) and one suspect face photo on the desktop.
- Run one search to warm CLIP/YOLO so the status bar shows everything online.
- Use a clean browser window (no bookmarks bar), ~1440px wide, light/normal zoom.
- Login accounts: `admin@city.gov / admin123`, `officer@city.gov / officer123`
  (officer can see Dashboard, VisionScan, Map, Alerts, Arbiter, CrimeGPT, Cases).

---

## Stills (PNG)

| # | Filename (`docs/assets/`) | Account & page | State / toggles to set | Used in |
|---|---|---|---|---|
| 1 | `hero-search-results.png` | officer · **VisionScan** tab | Text search `two people standing near a car`; results visible with an **event badge** (e.g. "×9, 00:12–00:21"). Status bar showing CLIP/YOLO online in frame. | **README hero**, one-pager |
| 2 | `vision-object-search.png` | officer · VisionScan | **Object** mode, query `car` (or click chip); grid of vehicle matches with confidence scores. | Proposal §VisionScan, abstract 1 |
| 3 | `vision-face-suspect.png` | officer · VisionScan | **Suspect Face** mode; a face photo uploaded, matches across cameras shown. (Use a non-sensitive/test face.) | Proposal §VisionScan |
| 4 | `vision-report-pdf.png` | officer · VisionScan | 3–4 frames ticked → **Generate Report** → the exported PDF open, showing timestamps/cameras/confidence + the human-in-the-loop footer. | Proposal §VisionScan, one-pager |
| 5 | `map-risk-layer.png` | officer · **City Map** | **Risk forecast** layer active; risk circles over the 30 Ahmedabad localities; legend visible. | **README**, proposal §Hotspot, abstract 2, fallback |
| 6 | `map-why-hotspot.png` | officer · City Map | A locality's **"Why this hotspot?"** popover open — the stacked-bar breakdown + plain-English sentence. | Proposal §Hotspot (explainability), fallback |
| 7 | `map-accuracy-panel.png` | officer · City Map | **Model accuracy (backtested)** panel expanded — HR@10, PAI@10 vs oracle, surge-detection rows. | Proposal §Hotspot, one-pager, fallback |
| 8 | `map-cyber-layer.png` | officer · City Map | **Cyber fraud** layer active; violet circles sized by ₹ lost. | Proposal §Hotspot / cyber, abstract 2 |
| 9 | `complaint-cyber-1930.png` | citizen *or* officer · **Complaints** | Cyber intake toggle ON, an NCRP fraud category picked, hours-ago ≤ 24 so the **red golden-hour 1930 banner** is showing + applicable BNS sections. | Proposal §Cyber intake, abstract 5 |
| 10 | `closed-loop-case.png` | officer · **Cases** | An **AUTO** case opened (title "AUTO: ... detected at ...") showing the attached anomaly keyframe as evidence + the dispatch notification. | Proposal §Closed loop, one-pager |
| 11 | `crimegpt-document.png` | officer · **CrimeGPT** | A generated statutory document (e.g. Remand Request) open, with the suggested BNS/BNSS sections panel visible. | Proposal §CrimeGPT, abstract 4 |
| 12 | `govintel-legal-feed.png` | any · **Legal Feed** | A filtered list of GR/notification/judgment results with a bookmark + a saved-search alert visible. | Proposal §Legal, abstract 3 |

> #1, #5, #7, #10 are the must-haves if time is short. #6–#9, #11–#12 are the
> "depth" shots for the proposal sections.

---

## GIFs (use **ScreenToGif**, Windows — easiest for trimming + size)

Keep each **≤ 4 MB**. Target ~1000px wide, 12–15 fps, trim dead frames. Save under
`docs/assets/`. If a GIF exceeds 4 MB, drop fps to 10 and/or width to 900px in
ScreenToGif's editor before exporting.

| # | Filename | Length | Content to record | Used in |
|---|---|---|---|---|
| G1 | `gif-search-flow.gif` | 8–12 s | VisionScan: type a text query → results stream in → click an event badge to expand grouped frames. | **README hero GIF**, proposal §VisionScan |
| G2 | `gif-closed-loop.gif` | 10–15 s | Live Alerts shows a new anomaly → cut to Cases showing the freshly **AUTO** case with keyframe → the dispatch notification bell. Tells the closed-loop story in one motion. | Proposal §Closed loop, README |
| G3 | `gif-map-explain.gif` | 8–12 s | City Map: switch Reports → **Risk forecast** layer, click a hotspot → "Why this hotspot?" breakdown opens → expand the accuracy panel. | Proposal §Hotspot, README |

---

## Capture tips
- Hide personal info (real names/faces) — use the demo/test data only.
- Capture at a consistent window size so the README grid looks uniform.
- For the PDF shot (#4), open the exported file in a PDF viewer, not the browser
  download bar, so the forensic footer is legible.
- After capturing, eyeball that every filename here exists in `docs/assets/`
  before committing — broken image links read worse than no image.

See [`DEMO_FALLBACK.md`](DEMO_FALLBACK.md) for the pre-recorded full **video**
(`demo-full.mp4`) capture commands — that is separate from these GIFs.
