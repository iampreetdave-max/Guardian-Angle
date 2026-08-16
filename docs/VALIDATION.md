# VisionScan / CityShield — Validation Report

_Generated **2026-08-16 10:16:14** by `backend/scripts/run_all_checks.py`. Every number below was produced by actually running the code on this machine — reproduce them with the commands in each section._

**Overall: PASS** — 5/5 suites green.

> Data provenance: all metrics are computed on a **fully synthetic, deterministic** Ahmedabad incident stream (`backend/app/platform/seed_synthetic.py`, fixed seed). They demonstrate methodology and pipeline correctness, **not** real-world operational accuracy. See `docs/AHMEDABAD_CRIME_DATA.md`.

## 1. Suite results

| Check | Result | Summary |
|---|---|---|
| pytest backend/tests | ✅ PASS | 81 passed |
| predictive smoke test | ✅ PASS | all 31 checks passed |
| anomaly self-test | ✅ PASS | all 13 checks passed |
| demo_reset self-checks (dry-run) | ✅ PASS | all 15 demo-state checks passed |
| predictive backtest | ✅ PASS | Hit-Rate@10: 0.79 \| PAI@10: 2.4x (oracle ceiling 2.5x) \| capture 79% of next-week crime in |

Re-run commands:

```bash
# pytest backend/tests
cd backend && PYTHONPATH=. python -m pytest tests
# predictive smoke test
cd backend && PYTHONPATH=. python scripts/predictive_smoketest.py
# anomaly self-test
cd backend && PYTHONPATH=. python scripts/anomaly_selftest.py
# demo_reset self-checks (dry-run)
cd backend && PYTHONPATH=. python scripts/demo_reset.py --dry-run
# predictive backtest
cd backend && PYTHONPATH=. python scripts/predictive_backtest.py --folds 8
```

## 2. Test counts (pytest)

- **Passed:** 81

## 3. Predictive model — backtest

Method: **rolling-origin temporal cross-validation** · folds: **8** · horizon: **7 days** · areas: **30**.

Window: `2026-06-21 10:16:13` → `2026-08-09 10:16:13`.

**Headline:** Hit-Rate@10: 0.79 | PAI@10: 2.4x (oracle ceiling 2.5x) | capture 79% of next-week crime in 33% of the city (90% CI hit-rate@10 [0.77, 0.82], 8 weekly folds) | detected 2/2 planted surges in the live top-10 during their surge week (3/3 surge-areas)

### 3.1 Model metrics (mean over folds, 90% bootstrap CI)

| k | Hit-Rate@k | HR@k 90% CI | PAI@k | PAI@k 90% CI | Oracle ceiling |
|---|---|---|---|---|---|
| 5 | 0.562 | [0.5411, 0.5831] | 3.37x | [3.246, 3.499] | 3.59x |
| 10 | 0.791 | [0.765, 0.8179] | 2.37x | [2.295, 2.454] | 2.54x |

### 3.2 Capture-rate curve (share of next-week crime in top-k areas)

| top-k | % of city | % of next-week crime |
|---|---|---|
| 1 | 3% | 13.7% |
| 3 | 10% | 37.7% |
| 5 | 17% | 56.2% |
| 10 | 33% | 79.1% |
| 15 | 50% | 89.2% |

### 3.3 Surge detection

Detected **2/2** planted, time-boxed surges — at least one area of each rose into the live top-10 during its surge week (3 of 3 surge-*areas* individually).

| Area | Category | Rank before → during | In top-10 | Surge |
|---|---|---|---|---|
| Maninagar | chain_snatching | 5 → 5 | yes | Maninagar chain-snatching spree (weeks 8-10) |
| SG Highway | cyber_fraud | 6 → 4 | yes | SG Highway / Satellite cyber-fraud ramp (final 4 weeks) |
| Satellite | cyber_fraud | 11 → 10 | yes | SG Highway / Satellite cyber-fraud ramp (final 4 weeks) |

### 3.4 Baseline comparison

| Strategy | HR@5 | HR@10 | PAI@5 | PAI@10 |
|---|---|---|---|---|
| model | 0.562 | 0.791 | 3.37x | 2.37x |
| frequency | 0.566 | 0.771 | 3.40x | 2.31x |
| prior | 0.436 | 0.647 | 2.62x | 1.94x |
| random | 0.174 | 0.352 | 1.04x | 1.06x |

Model beats the uniform-random floor at HR@10 by **43.9 points** (0.791 vs 0.352).

> Computed on fully synthetic, deterministic demo data (see docs/AHMEDABAD_CRIME_DATA.md). Numbers demonstrate methodology, not real-world operational accuracy.

## 4. Reproduce this whole report

```bash
cd backend
PYTHONPATH=. python scripts/run_all_checks.py
# writes docs/VALIDATION.md
```
