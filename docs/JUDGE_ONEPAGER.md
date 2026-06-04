# VisionScan + CityShield — Judge One-Pager

> **KANAD S.H.I.E.L.D. 2026** · Cyber Crime Branch, Ahmedabad · Live pitch, i-Hub Gujarat
> Brand: navy `#0a1124` / gold `#f4b23c`. Designed to print on **one page**.

---

### The problem (one line)
**Investigators drown in CCTV, complaints, and legal paperwork** — VisionScan turns
all of it into searchable evidence, a predictive map, an auto-dispatched response,
and court-ready documents, **fully offline on a field laptop.**

---

### The live numbers (re-verified, not quoted from memory)
*Source: `python scripts/predictive_backtest.py --folds 8` over the deterministic
synthetic stream (1,969 complaints, 30 localities, 8 weekly walk-forward folds).
Rolling-origin temporal cross-validation — no future data leaks into a prediction.*

| Metric | Model | Honest ceiling / floor |
|---|---|---|
| **Hit-Rate@10** | **0.771** (90% CI 0.74–0.80) | — |
| **PAI@10** (Predictive Accuracy Index) | **2.31×** | oracle ceiling **2.51×** (92% of perfect) |
| **Crime captured in top-10 zones** (33% of city) | **77.1%** of next-week crime | — |
| **Planted surges caught in live top-10** | **3 / 3** during their surge week | — |
| Beats baselines (HR@10) | model 0.771 | frequency 0.733 · prior 0.629 · random 0.370 |

> We publish the **oracle ceiling** (the best any predictor could do on this data)
> so the PAI number is interpretable, not inflated. Numbers demonstrate
> *methodology* on synthetic demo data — not real-world operational accuracy.

**Engineering health:** `pytest backend/tests` → **77 passed**; `npm run build`
passes; app boots and demos **with Wi-Fi unplugged**.

---

### Judging criteria — at a glance

| Criterion | How VisionScan meets it |
|---|---|
| **Practical field value** | Ctrl-F for CCTV; auto-case + nearest-unit dispatch; 7 court-ready documents. |
| **Data security** | 100% offline; OWASP middleware, rate-limit, lockdown, SSRF & prompt-injection guards; audit-logged exports. |
| **Credibility / no black box** | Open models (CLIP, YOLOv8, ArcFace, FAISS); glass-box risk formula; human-in-the-loop. |
| **Measured accuracy** | Backtested HR@10 0.771, PAI@10 2.31× vs 2.51× oracle, with bootstrap CIs. |
| **Innovation** | One live anomaly closes the loop into a geo-tagged case + risk bump + dispatch. |
| **Local relevance** | 30 real Ahmedabad localities, NCRP/1930 cyber intake, BNS/BNSS sections, en/hi/gu. |
| **Completeness / polish** | Full RBAC platform, GIS dashboard, exports, security report, one-command deploy. |

---

### What makes this different (3 bullets)
1. **It closes the loop.** A live fire/weapon/violence detection auto-creates a
   geo-tagged case with the keyframe as evidence, bumps that locality's risk, and
   pings the nearest patrol unit — detection becomes *action*, not just an alert.
2. **Measured accuracy with an honest ceiling.** We don't claim a magic number; we
   backtest with rolling-origin CV and report PAI@10 2.31× against a 2.51× oracle
   ceiling and a random-0.370 floor, with 90% confidence intervals.
3. **Offline-first by design.** Models and footage never leave the laptop. Gemini,
   gov RSS, and map tiles are optional polish that degrade gracefully — the whole
   product works air-gapped at a crime scene.

---

### Try it / demo accounts
**Deploy:** `docker compose up -d` → `http://localhost:8080` (or `start.ps1`).
**HF Space:** https://huggingface.co/spaces/iampreetdave/visionscan

| Role | Email | Password |
|---|---|---|
| Admin | `admin@city.gov` | `admin123` |
| Lead investigator | `lead@city.gov` | `lead123` |
| Officer | `officer@city.gov` | `officer123` |
| Citizen | `citizen@example.com` | `citizen123` |

> **[ QR CODE PLACEHOLDER ]** — generate a QR for the HF Space URL above and drop
> it here (and on the printed page). Suggested: any offline QR tool, ~180×180 px,
> caption "Scan to try VisionScan live."

---

### Submissions (Kanad S.H.I.E.L.D.)
1. VisionScan CCTV — `PS-69E9C85F9C307` (Cat 1) · 2. Crime Hotspot — `PS-69EEFE1294451` ·
3. Unified Legal — `PS-69EEFDD4DA6E9` · 4. CrimeGPT — `PS-69EEFDFB90B99` ·
5. Open-Ended — `PS-69EEFE4F8CD1C` (2–5 Cat 2). Abstracts: `docs/abstracts/`.

*Verification: backtest numbers from `scripts/predictive_backtest.py` (8 folds);
test count from `pytest backend/tests`; demo accounts from
`backend/app/platform/seed.py`.*
