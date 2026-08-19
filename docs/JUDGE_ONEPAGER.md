# VisionScan + CityShield — Judge One-Pager

> **KANAD S.H.I.E.L.D. 2026** · Cyber Crime Branch, Ahmedabad · Live pitch, i-Hub Gujarat
> Brand: navy `#0a1124` / gold `#f4b23c`. Designed to print on **one page**.

---

### The problem (one line)
**Investigators drown in CCTV, complaints, and legal paperwork** — VisionScan turns
all of it into searchable evidence, a predictive map, an auto-dispatched response,
and court-ready documents, **fully offline on a field laptop.**

---

### Measured on REAL footage (no synthetic data anywhere in this table)
*16 hand-verified HD CCTV clips, hand-labelled ground truth, scored offline on CPU.*

| Vision metric | Result |
|---|---|
| **Macro recall** (natural-language search over real clips) | **84.6%** |
| **Top-1 accuracy** | **61.5%** |
| **False positives** | **zero** |
| **Suspect face re-identification** | source frame returns at **rank 1**, score **0.80** |
| Scene analytics throughput | 3,362 detections → 1,409 tracked objects |

> Per-camera tracking quality is graded by **measured fragmentation**, and we publish the
> bad grades too: market **0.13 (good)**, highway **0.39 (degraded)**, junction
> **0.45 (poor)**. We would rather show a judge our worst camera than hide it.

---

### The predictive numbers (synthetic data — see disclaimer)
*Source: `python scripts/predictive_backtest.py --folds 8` over the deterministic
synthetic stream (2,011 complaints, 30 localities, 8 weekly walk-forward folds).
Rolling-origin temporal cross-validation — no future data leaks into a prediction.*

| Metric | Model | Honest ceiling / floor |
|---|---|---|
| **Hit-Rate@10** | **0.790** (90% CI 0.77–0.81) | — |
| **PAI@10** (Predictive Accuracy Index) | **2.37×** | oracle ceiling **2.53×** (94% of perfect) |
| **Crime captured in top-10 zones** (33% of city) | **79.0%** of next-week crime | — |
| **Planted surges detected in live top-10** | **2 / 2 surges** during their surge week | third surge-*area* sits on the top-10 boundary and moves between runs |
| Beats baselines (HR@10) | model 0.790 | frequency 0.771 · prior 0.647 · random 0.352 |

> We publish the **oracle ceiling** (the best any predictor could do on this data)
> so the PAI number is interpretable, not inflated. Numbers demonstrate
> *methodology* on synthetic demo data — not real-world operational accuracy.

**Engineering health:** `pytest backend/tests` → **81 passed** (recorded in
`docs/VALIDATION.md`); `npm run build` passes; **109 API endpoints**; **760 i18n keys at
en/hi/gu parity**; app boots and demos **with Wi-Fi unplugged**.

---

### Judging criteria — at a glance

| Criterion | How VisionScan meets it |
|---|---|
| **Practical field value** | Ctrl-F for CCTV; auto-case + nearest-unit dispatch; 7 court-ready documents. |
| **Data security** | 100% offline; OWASP middleware, rate-limit, lockdown, SSRF & prompt-injection guards; audit-logged exports. |
| **Credibility / no black box** | Open models (CLIP, YOLOv8, ArcFace, FAISS); glass-box risk formula; human-in-the-loop. |
| **Measured accuracy** | **Real footage: 84.6% macro recall, zero false positives, face re-id at rank 1.** Predictive (synthetic): HR@10 0.790, PAI@10 2.37× vs 2.53× oracle, bootstrap CIs. |
| **Innovation** | One live anomaly closes the loop into a geo-tagged case + risk bump + dispatch. |
| **Local relevance** | 30 real Ahmedabad localities, NCRP/1930 cyber intake, BNS/BNSS sections, en/hi/gu. |
| **Aligned with live gov't initiatives** | **Gujarat Police Innovation Challenge 2026** (announced 17 Aug 2026 — unify 80,000+ CCTVs with AI video analytics, opens September) and Gujarat's **e-Zero FIR** launch with **I4C** (27 Jul 2026 — a 1930 call auto-files a zero FIR). This platform already does both jobs. |
| **Completeness / polish** | Full RBAC platform, GIS dashboard, exports, security report, one-command deploy. |

---

### What makes this different (3 bullets)
1. **It closes the loop.** A live fire/weapon/violence detection auto-creates a
   geo-tagged case with the keyframe as evidence, bumps that locality's risk, and
   pings the nearest patrol unit — detection becomes *action*, not just an alert.
2. **Measured accuracy with an honest ceiling.** The search numbers are from **real
   footage** — 84.6% macro recall with **zero false positives** across 16 hand-verified
   clips. The predictive numbers are backtested with rolling-origin CV and reported
   against their own **oracle ceiling** (PAI@10 2.37× vs 2.53×) and a random-0.352 floor,
   with 90% CIs — on synthetic data, and we say so on every slide that shows them.
3. **Offline-first by design.** Models and footage never leave the laptop. Gemini,
   gov RSS, and map tiles are optional polish that degrade gracefully — the whole
   product works air-gapped at a crime scene.

---

### Try it / demo accounts
**Source code (everything, MIT):** https://github.com/iampreetdave-max/Guardian-Angle
**Demo video (2:46, captioned):** https://youtu.be/LE9iE1_mCrU
**Run it yourself:** `docker compose up -d` → `http://localhost:8080` (or `.\start.ps1`) —
no API keys, no GPU, no internet required.
**Test footage (upload these):** https://drive.google.com/drive/folders/1mHoekSVX4ytmBEBaCnFrutMljqKxfmiz

> **On hosting:** the pilot ran on an Azure-for-Students VM; that credit has lapsed, so
> **there is no public URL right now** and we would rather say that than hand a judge a link
> that 404s. A hosted instance can be stood up on request in one command — the product is
> offline-first by design, and the demo runs from the repo on any laptop.

| Role | Email | Password |
|---|---|---|
| Admin | `admin@city.gov` | `admin123` |
| Lead investigator | `lead@city.gov` | `lead123` |
| Officer | `officer@city.gov` | `officer123` |
| Citizen | `citizen@example.com` | `citizen123` |

> **[ QR CODE ]** — `docs/assets/ppt/qr_github.png` (repo) and `qr_video.png` (demo
> video); drop both on the printed page, ~180×180 px, captions "Scan for the source" and
> "Scan for the 2:46 demo". Do **not** print a QR for any hosted URL — there isn't one.

---

### Submissions (Kanad S.H.I.E.L.D.)
1. VisionScan CCTV — `PS-69E9C85F9C307` (Cat 1) · 2. Crime Hotspot — `PS-69EEFE1294451` ·
3. Unified Legal — `PS-69EEFDD4DA6E9` · 4. CrimeGPT — `PS-69EEFDFB90B99` ·
5. Open-Ended — `PS-69EEFE4F8CD1C` (2–5 Cat 2). Abstracts: `docs/abstracts/`.

*Verification: backtest numbers from `scripts/predictive_backtest.py` (8 folds); test
count from `pytest backend/tests` as recorded in `docs/VALIDATION.md`; real-footage search
numbers from the 16 hand-verified clips in the Drive folder above; demo accounts from
`backend/app/platform/seed.py`. Gujarat Police Innovation Challenge 2026 and e-Zero FIR
citations in `docs/AHMEDABAD_CRIME_DATA.md` §7 (S18, S19).*
