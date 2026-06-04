# VisionScan / CityShield — Validation Report

_Generated **2026-06-04 12:19:52** by `backend/scripts/run_all_checks.py`. Every number below was produced by actually running the code on this machine — reproduce them with the commands in each section._

**Overall: PASS** — 5/5 suites green.

> Data provenance: all metrics are computed on a **fully synthetic, deterministic** Ahmedabad incident stream (`backend/app/platform/seed_synthetic.py`, fixed seed). They demonstrate methodology and pipeline correctness, **not** real-world operational accuracy. See `docs/AHMEDABAD_CRIME_DATA.md`.

## 1. Suite results

| Check | Result | Summary |
|---|---|---|
| pytest backend/tests | ✅ PASS | 77 passed |
| predictive smoke test | ✅ PASS | all 31 checks passed |
| anomaly self-test | ✅ PASS | all 13 checks passed |
| demo_reset self-checks (dry-run) | ✅ PASS | all 15 demo-state checks passed |
| predictive backtest | ✅ PASS | Hit-Rate@10: 0.77 \| PAI@10: 2.3x (oracle ceiling 2.5x) \| capture 77% of next-week crime in |

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

- **Passed:** 77

## 3. Predictive model — backtest

Method: **rolling-origin temporal cross-validation** · folds: **8** · horizon: **7 days** · areas: **30**.

Window: `2026-04-09 06:49:52` → `2026-05-28 06:49:52`.

**Headline:** Hit-Rate@10: 0.77 | PAI@10: 2.3x (oracle ceiling 2.5x) | capture 77% of next-week crime in 33% of the city (90% CI hit-rate@10 [0.74, 0.80], 8 weekly folds) | caught 3/3 planted surge-areas in the live top-10 during their surge week

### 3.1 Model metrics (mean over folds, 90% bootstrap CI)

| k | Hit-Rate@k | HR@k 90% CI | PAI@k | PAI@k 90% CI | Oracle ceiling |
|---|---|---|---|---|---|
| 5 | 0.541 | [0.4952, 0.5845] | 3.25x | [2.971, 3.507] | 3.54x |
| 10 | 0.771 | [0.7383, 0.803] | 2.31x | [2.215, 2.409] | 2.51x |

### 3.2 Capture-rate curve (share of next-week crime in top-k areas)

| top-k | % of city | % of next-week crime |
|---|---|---|
| 1 | 3% | 13.3% |
| 3 | 10% | 34.6% |
| 5 | 17% | 54.1% |
| 10 | 33% | 77.1% |
| 15 | 50% | 89.3% |

### 3.3 Surge detection

Caught **3/3** planted, time-boxed surge-areas in the live top-10 during their surge week.

| Area | Category | Rank before → during | In top-10 | Surge |
|---|---|---|---|---|
| Maninagar | chain_snatching | 5 → 3 | yes | Maninagar chain-snatching spree (weeks 8-10) |
| SG Highway | cyber_fraud | 7 → 5 | yes | SG Highway / Satellite cyber-fraud ramp (final 4 weeks) |
| Satellite | cyber_fraud | 10 → 9 | yes | SG Highway / Satellite cyber-fraud ramp (final 4 weeks) |

### 3.4 Baseline comparison

| Strategy | HR@5 | HR@10 | PAI@5 | PAI@10 |
|---|---|---|---|---|
| model | 0.541 | 0.771 | 3.25x | 2.31x |
| frequency | 0.525 | 0.733 | 3.15x | 2.20x |
| prior | 0.398 | 0.629 | 2.39x | 1.89x |
| random | 0.161 | 0.370 | 0.96x | 1.11x |

Model beats the uniform-random floor at HR@10 by **40.0 points** (0.771 vs 0.370).

> Computed on fully synthetic, deterministic demo data (see docs/AHMEDABAD_CRIME_DATA.md). Numbers demonstrate methodology, not real-world operational accuracy.

## 4. Reproduce this whole report

```bash
cd backend
PYTHONPATH=. python scripts/run_all_checks.py
# writes docs/VALIDATION.md
```
