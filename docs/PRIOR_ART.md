# Prior Art and Positioning

_Last updated 19 Aug 2026. Every factual claim below carries a source and an access date. Where a claim could not be verified from a primary or reputable secondary source, it is marked **[unverified]** with the reason._

This document exists to answer three questions a research-methodology reviewer will ask and that the rest of this repo does not answer: **what came before, whose metrics are we reporting, and what here is actually new.** The short answer to the third question is: *the models are not new, the integration is.* Section 4 says so explicitly.

---

## 1. The academic lineage of hotspot forecasting

The predictive module in this project is a spatio-temporal hotspot ranker. It sits at the end of a well-documented 20-year research line. Naming that line honestly is more useful than claiming novelty.

### 1.1 Near-repeat victimisation — the empirical foundation

Johnson and Bowers (2004) showed that after a residential burglary, the risk to nearby properties rises sharply and then decays over days-to-weeks — the "near repeat" effect — and proposed *prospective hot-spotting* as a consequence: forecast from recent events, not from long-run averages [R1]. This is the empirical fact that makes short-horizon crime forecasting possible at all. Sagovsky and Johnson (2007) refined the timing, finding most near repeats cluster within about seven days of the originating burglary [R2].

**Relevance here:** this project's 7-day forecast horizon and recency-weighted scoring are downstream of this finding. The horizon is not an arbitrary product choice.

### 1.2 Risk terrain modelling — the environmental branch

Caplan, Kennedy and Miller (2011) introduced Risk Terrain Modeling (RTM), which forecasts from *place features* (bars, transit stops, vacant lots) rather than from past crime points, and reported that risk terrains forecast shootings significantly better than retrospective hotspot mapping [R3]. The book-length treatment is Caplan and Kennedy, *Risk Terrain Modeling: Crime Prediction and Risk Reduction* (University of California Press) [R4].

**Relevance here:** RTM is the branch this project **does not** implement. There is no environmental-feature layer in the model. That is a real gap, not a design decision, and it is the most obvious extension available.

### 1.3 Self-exciting point processes — the mathematical branch

Mohler, Short, Brantingham, Schoenberg and Tita (2011) formalised near-repeat behaviour as a self-exciting (Hawkes / ETAS) point process borrowed from seismology, fitted on LAPD residential burglary data [R5]. This is the mathematical core that became PredPol.

### 1.4 The field trials

Mohler et al. (2015) ran a single-blind randomised controlled trial of the ETAS model across three LAPD divisions (Foothill, North Hollywood, Southwest, Nov 2011 – Jan 2013) and two Kent Police divisions in the UK [R6]. This remains the strongest positive evidence for the approach — and it is worth noting how rare that level of evidence is in this field.

Chicago's parallel effort went the other way. Saunders, Hunt and Hollywood (2016) evaluated the Chicago Police Department's 2013 Strategic Subjects List pilot — 426 individuals ranked by predicted gun-violence risk — and found no measurable effect on city-level homicide, while individuals on the list were more likely to be arrested for a shooting [R7]. That is an *individual-level* prediction system, a category this project deliberately does not build (see §4.3).

### 1.5 The critiques — accuracy, feedback, and law

Three distinct objections, often conflated:

**Accuracy.** The Markup and WIRED analysed 23,631 Geolitica (formerly PredPol) predictions generated for Plainfield, NJ between 25 Feb and 18 Dec 2018 and found a success rate below 1% for the crime types examined — against a contract of \$20,500 for the first annual term and \$15,500 for a one-year extension [R8]. LAPD dropped PredPol in April 2020, citing COVID-era budget constraints; the LA Inspector General's March 2019 audit had already concluded there was insufficient data to establish that the program reduced crime [R9].

**Feedback loops.** Lum and Isaac (2016) took PredPol's published algorithm, ran it on Oakland drug-arrest data, and showed the predictions tracked *where police had already been* rather than where drug use actually occurred — "selection bias meets confirmation bias" [R10]. Ensign et al. (2018) proved the runaway-feedback result formally and gave a discovery-reweighting fix [R11].

**Law and governance.** Ferguson, *The Rise of Big Data Policing* (NYU Press, 2017), argues the legal problem is not accuracy but reasonable suspicion — a forecast that a place is high-risk can be laundered into justification for a stop [R12].

**How this project responds — honestly:**

| Objection | This project's actual position |
|---|---|
| Predictions reflect enforcement, not crime | **Not solved.** The model is trained on incident records; on real data it would inherit the same bias. It is currently run on synthetic data, which sidesteps rather than answers the problem. |
| Runaway feedback | **Not implemented.** No discovery-reweighting per Ensign et al. [R11]. This is the highest-value fairness change available. |
| Individual risk scoring / heat lists | **Explicitly out of scope.** Predictions are per-locality (30 areas), never per-person. |
| Unfalsifiable vendor accuracy claims | **Directly addressed.** The backtest, its folds, its baselines and its oracle ceiling are published in `docs/VALIDATION.md` and reproducible with one command. See §2. |

---

## 2. Evaluation metrics: whose metrics these are

This project reports Hit Rate and PAI. It has never said where those come from. It should.

### 2.1 Hit Rate and PAI (Chainey, Tompson & Uhlig, 2008)

The **Prediction Accuracy Index** was defined by Chainey, Tompson and Uhlig (2008) in *Security Journal*, comparing four hotspot-mapping techniques for burglary, street crime and vehicle crime [R13]:

```
Hit Rate = n / N            (share of subsequent crimes falling inside flagged areas)
PAI      = (n/N) / (a/A)    (hit rate divided by the share of area flagged)
```

where *n* = crimes inside hotspots, *N* = all crimes observed, *a* = hotspot area, *A* = total study area. PAI = 1.0 is no better than flagging area at random; PAI = 2.4 means the flagged area is 2.4x denser in next-period crime than the map average.

**PAI's known weakness:** it is unbounded above and it moves with the fraction of area flagged, so PAI values are not comparable across studies that flag different coverage. This is exactly why the next metric exists.

### 2.2 PEI and PEI* (Hunt; White, Hunt & Green, 2023)

The **Prediction Efficiency Index** normalises PAI against the best PAI *any* map could have achieved at the same coverage — i.e. against an oracle. PAI and PEI\* were the two official scoring metrics of the NIJ Real-Time Crime Forecasting Challenge (2017), run on Portland Police Bureau calls-for-service data; 40 prizes were awarded, one each for best PAI and best PEI\* across 20 categories [R14]. White, Hunt and Green (2023, *Security Journal*) review PAI, RRI, PEI and PEI\*, and argue PEI\* is the operationally realistic efficiency measure [R15].

### 2.3 What this project already does, and what it should call it

From `docs/VALIDATION.md` (generated 2026-08-16 by `backend/scripts/run_all_checks.py`; rolling-origin temporal cross-validation, 8 weekly folds, 7-day horizon, 30 Ahmedabad localities):

| k | Hit-Rate@k | 90% CI | PAI@k | 90% CI | Oracle ceiling |
|---|---|---|---|---|---|
| 5 | 0.562 | [0.541, 0.583] | 3.37x | [3.246, 3.499] | 3.59x |
| 10 | 0.791 | [0.765, 0.818] | 2.37x | [2.295, 2.454] | 2.54x |

**The point worth making to a reviewer:** reporting PAI *against a computed oracle ceiling* is a PEI-style efficiency measure. At k=10 the model reaches 2.37 of a possible 2.54 — roughly 93% of the achievable ceiling. Much of the commercial field publishes a bare hit rate with no coverage denominator at all, which is uninterpretable. **The naming should be fixed:** what this project computes is closer to PEI in the sense of Hunt / White et al. [R14][R15] than to a raw Chainey PAI, and the docs should cite [R13] for PAI and [R15] for the ceiling-normalised form.

**Two honest caveats, both already in the repo:**

1. **The data is synthetic.** All predictive metrics are computed on a deterministic synthetic Ahmedabad incident stream (`backend/app/platform/seed_synthetic.py`, fixed seed). They demonstrate that the pipeline and the evaluation harness are correct. They are **not** evidence of real-world accuracy, and no comparison to [R6] or [R8] on accuracy grounds is legitimate.
2. **The model does not beat the naive baseline everywhere.** From `docs/VALIDATION.md` §3.4: at k=10 the model gets HR 0.791 vs the frequency baseline's 0.771; **at k=5 the frequency baseline wins (0.566 vs the model's 0.562).** A recency-weighted model that only edges out a plain frequency count on synthetic data has not demonstrated much beyond harness correctness. Publishing that is the point.

Surge detection is reported **per surge: 2/2 planted surges detected** in the live top-10 during their surge week. Per-*area* tallies are not reported because they are not reproducible — one locality sits exactly on the top-10 boundary and flips between runs as the 180-day window slides with the seed timestamp.

---

## 3. Commercial and government systems

### 3.1 What exists

**BriefCam** — video content analytics (synopsis, search, face/object matching) layered on an existing VMS. Acquired by Canon in 2018; merged into Milestone Systems (also Canon Group) in 2024 [R16][R17]. The **Processing Server requires an NVIDIA GPU**; certified cards include Tesla P4/T4 and Quadro P4000, and a single GPU cannot serve real-time and on-demand processing simultaneously [R18]. Licensing is per camera channel.

**Axon / Fusus** — real-time crime centre aggregating live video, data and sensor feeds. Axon acquired Fusus on 1 Feb 2024 [R19]. Cloud/subscription. Publicly reported municipal contracts vary by an order of magnitude: Dearborn, MI approved ~\$720,000 over five years (~\$144k/yr); Lawrence, KS approved a consolidated contract of ~\$3.2M through Jan 2029 (~\$640k/yr) [R20].

**Genetec** — Security Center / Omnicast VMS with an analytics module ecosystem, proprietary, per-camera connection licensing. **[unverified: list pricing]** — Genetec does not publish price lists; all figures are quote-based through integrators, so no cost number is asserted here.

**Milestone XProtect** — the dominant open-platform VMS. Notably, **Milestone discontinued the free XProtect Essential+ tier (long free for up to 8 cameras) with the XProtect 2025 R2 release; activation of previously downloaded Essential+ licences ceased on 1 Jan 2026, and the entry point is now the paid Express+** [R21]. The "free small VMS" option in this market closed within the last year.

**India — national spine.** CCTNS (Crime and Criminal Tracking Network and Systems), launched 2009 under MHA, is deployed across roughly 17,700 police stations; ICJS (2017) links CCTNS to e-Courts, e-Prisons, e-Prosecution and e-Forensics, with ICJS 2.0 in rollout [R22][R23]. Any system intended for an Indian police station is an *adjunct* to CCTNS, not a replacement for it.

**Gujarat — Project Vishwas.** "Video Integration and Statewide Advanced Security". Phase 1 deployed 7,000 CCTV cameras; Phase 2 adds **12,500 cameras across 54 cities and 79 interstate check posts** (reported 27 Nov 2025) [R24].

**Ahmedabad city.** As of a 25 Feb 2026 report, **6,703 public CCTV cameras are active in the city — 3,409 connected to police stations and 3,294 to the control room**; the public-camera programme began March 2025 [R25].

**Nirbhaya / Safe City.** The Empowered Committee under the Nirbhaya Fund approved Safe City projects for eight cities — Delhi, Mumbai, Kolkata, Chennai, Bengaluru, Hyderabad, **Ahmedabad** and Lucknow — at a total cost of ₹2,919.55 crore, cost-shared 60:40 Centre:State (Delhi fully central) [R26].

### 3.2 Comparison

| System | What it does | Cost signal | Runs fully offline? | Open? |
|---|---|---|---|---|
| **BriefCam** (Milestone/Canon) | Video synopsis, object/face search, real-time alerting on top of a VMS | Per-channel licence + NVIDIA GPU servers; quote-based **[unverified: list price]** | On-prem yes, but **requires NVIDIA GPU** [R18] | No |
| **Axon Fusus** | RTCC: aggregates live camera/sensor feeds, integrates body-worn video | ~\$144k–\$640k/yr in reported municipal contracts [R20] | No — cloud-centric | No |
| **Genetec Security Center** | Enterprise VMS + analytics ecosystem, ANPR | Per-camera connection licence, quote-based **[unverified: list price]** | Yes, on-prem | No |
| **Milestone XProtect** | Open-platform VMS, third-party analytics marketplace | Free tier **discontinued** at 2025 R2; paid Express+ upward [R21] | Yes, on-prem | Open *integration* API; closed core |
| **CCTNS / ICJS** | National FIR/case record spine across police, courts, prisons, forensics | Government programme | Government network | Government-only access [R22][R23] |
| **Project Vishwas** (Gujarat) | Statewide camera estate: 12,500 cameras / 54 cities / 79 check posts | State programme | State network | Government-only [R24] |
| **Safe City** (incl. Ahmedabad) | Cameras, panic buttons, GIS crime mapping for women's safety | ₹2,919.55 cr across 8 cities [R26] | Government network | Government-only [R26] |
| **This project** | CCTV search + anomaly detection + hotspot forecast + case management, closed-loop | ₹0 licence; commodity CPU box | **Yes — no GPU, no internet, no external API** | Source-available in this repo |

The two columns that matter are the last two. Every commercial row is either GPU-dependent, cloud-dependent, per-seat licensed, or all three. The distinguishing constraint here is not capability — it is the deployment envelope.

---

## 4. Where this project actually sits

### 4.1 What is NOT novel — stated plainly

**No model was trained. Not one.** Every model is an off-the-shelf pretrained checkpoint used at inference only:

| Component | Model | Provenance | Trained here? |
|---|---|---|---|
| Semantic / text-to-image search | CLIP ViT-B/32 | Radford et al., 2021 [R27] | No — zero-shot, stock weights |
| Object detection | YOLOv8n | Ultralytics; **no peer-reviewed paper exists for YOLOv8** [R28] | No — stock COCO weights |
| Face embedding | ArcFace | Deng et al., CVPR 2019 [R29] | No — stock weights |
| Vector search | FAISS | Johnson, Douze & Jégou [R30] | N/A — library |
| Multi-object tracking | ByteTrack | Zhang et al., ECCV 2022 [R31] | No — association algorithm, not a trained model |

Also not novel: hotspot forecasting as a concept (§1), Hit Rate / PAI as metrics (§2), video search over CCTV (BriefCam has shipped it for a decade), or case management (CCTNS).

**The predictive model is a recency-weighted spatio-temporal ranker, not a Hawkes process.** It does not implement [R5], and it does not implement RTM [R3]. It is simpler than both.

### 4.2 What the contribution actually is

**Systems integration under a hard deployment constraint, plus a published evaluation harness.**

Specifically, three things a reviewer can check:

**(a) The closed loop.** Camera anomaly → auto-created case → risk-surface update → nearest-unit dispatch, as one continuous path rather than four products with an integration budget between them. In the commercial landscape of §3 this loop is spread across a VMS (Milestone/Genetec), an analytics layer (BriefCam), an RTCC (Fusus), and a records system (CCTNS) — four vendors, four licences, four integration projects. Whether this loop is *better* is unproven; that it is *one system* is verifiable.

**(b) The envelope.** 109 API endpoints, 97 backend tests, 760 i18n keys at en/hi/gu parity, running **fully offline on station-grade CPU** — CLIP ViT-B/32 + YOLOv8n + ArcFace + FAISS + SQLite, no GPU, no internet, no external API, no per-seat licence. Against §3.2 this is the actual differentiator: BriefCam mandates NVIDIA GPUs [R18], Fusus is cloud-centric [R20], and even the free small-VMS option (XProtect Essential+) closed in January 2026 [R21].

**(c) Honest evaluation as a deliverable.** Publishing an oracle ceiling, a naive baseline that beats the model at k=5, per-camera tracking quality graded as *degraded* and *poor*, and a prominent synthetic-data disclaimer, is not standard practice in this market — the accuracy record in [R8] and [R9] is what the absence of that practice looks like.

### 4.3 Measured results, with their limits

| Claim | Number | Data | Limit |
|---|---|---|---|
| Hotspot forecast | HR@10 **0.791** (90% CI 0.765–0.818); PAI@10 **2.37x** vs **2.54x** oracle | **Synthetic**, deterministic, 30 areas, 8 folds | Synthetic. Barely beats frequency baseline at k=10, loses to it at k=5. |
| Surge detection | **2/2 surges** detected in live top-10 during surge week | Synthetic, planted surges | n=2. Per-area tally not reported — not reproducible (boundary flip). |
| CCTV search | macro recall **84.6%**, top-1 **61.5%**, **zero false positives** | **16 hand-verified real HD clips** | n=16. Small. Real footage, hand-verified. |
| Face re-identification | source frame returns at **rank 1, score 0.80** | Real footage | Single query. Demonstrative, not an evaluation. |
| Scene analytics | 3,362 detections → 1,409 tracked objects; fragmentation graded market **0.13 good**, highway **0.39 degraded**, junction **0.45 poor** | Real footage | Two of three cameras are graded as failing. Published deliberately. |

**Out of scope by choice:** individual risk scoring / heat lists (the [R7] and [R12] failure mode), live face-matching against a general-population watchlist, and any claim of real-world crime-reduction effect. Establishing the last of those would require an RCT of the kind in [R6], which this project has not run and does not claim.

---

## 5. Fit to the two live Gujarat programmes

### 5.1 Gujarat Police Innovation Challenge 2026 — verified

Announced **17 Aug 2026** under the guidance of Gujarat DGP **G.S. Malik**: the state's largest AI-based CCTV hackathon, with the objective of a unified surveillance network across **more than 80,000 CCTV cameras** currently operated by different departments on different vendors, technologies, VMS platforms and network architectures. Two stages — an Open Innovation Challenge (one category for students and small/medium startups, one for large startups and established companies), then a Finale where six teams demonstrate **on live CCTV feeds in a real production environment**. Total prize pool **₹37 lakh**. Commences **September 2026**. Technology partner **i-Hub Gujarat**; knowledge partners **DA-IICT** and **NFSU** [R32][R33].

Reported focus areas, and what already exists here:

| Published focus area [R32] | Status in this repo |
|---|---|
| Integrating CCTV across different vendors / VMS / network architectures | **Partial.** Ingests standard video files and RTSP-style streams; no VMS-vendor SDK integrations. This is the challenge's central ask and the project's weakest fit. |
| Identifying suspicious people, vehicles and unusual activities | **Yes.** Hybrid CLIP+YOLO anomaly detection with calibrated margins and debounce; localized fire/smoke boxes. |
| Generating real-time alerts | **Yes.** Live alert stream with bounding-box overlay, auto-case creation, notifications. |
| Automatic number plate recognition | **No.** Not implemented. |
| Vehicle tracking | **Partial.** ByteTrack multi-object tracking with per-camera quality grading; not cross-camera vehicle re-ID. |
| Watchlist matching | **Yes.** ArcFace + FAISS face re-identification. |
| Multi-camera search | **Yes.** Text and image search across ingested cameras with timestamped results. |

Two gaps are worth stating rather than hiding: **no ANPR**, and **cross-vendor VMS integration is the one thing the challenge cares most about and the one thing least built here.** A serious entry needs both.

### 5.2 Cyber Financial Fraud e-Zero FIR — verified

Launched in Gandhinagar on **27 July 2026** by Gujarat Deputy Chief Minister **Harsh Sanghavi**. A complaint lodged on the national cybercrime helpline **1930** (operated under I4C, MHA) **automatically generates an e-Zero FIR**, forwarded electronically to the jurisdictional police station — no station visit required. The stated aim is to close the gap between fraud and formal reporting so stolen funds can be recovered; the first reported case prevented a ₹15.76 lakh loss in an Ahmedabad digital-arrest fraud [R34][R35].

Mapping onto this platform:

| e-Zero FIR primitive | Existing capability here |
|---|---|
| Complaint auto-escalates to a case with zero manual re-entry | **Direct match.** Anomaly → auto-created case is the same pattern with a different trigger; the citizen complaint → case path already exists. |
| Electronic routing to the jurisdictional station | **Partial.** Geo-routing to nearest unit exists; jurisdiction-boundary routing rules do not. |
| Speed as the operative metric | **Aligned.** Closed-loop latency is the metric the architecture is built around. |
| Cyber-fraud domain (BNS/BNSS section mapping, financial-fraud clustering) | **Adjacent.** CrimeGPT covers section mapping and documentation; GovIntel covers legal-corpus retrieval. Neither is built specifically for financial-fraud clustering. |

**A distinction the docs should keep straight:** the *Gujarat Police Innovation Challenge 2026* (state-level, 80,000 cameras, September) is **not** the same as the *Ahmedabad City Police Innovation Challenge 2026* whose Category 1 and Category 2 problem statements this project was built against (`docs/hackathon_ps_details.local.md`, problem statements posted 23 and 27 Apr 2026). They are separate competitions with separate organisers. Conflating them in a submission would be a factual error.

---

## References

**Predictive policing — foundations**

- **[R1]** Johnson, S.D. & Bowers, K.J. (2004). "The burglary as clue to the future: The beginnings of prospective hot-spotting." *European Journal of Criminology*, 1(2), 237–255. DOI: [10.1177/1477370804041252](https://journals.sagepub.com/doi/10.1177/1477370804041252) — accessed 19 Aug 2026.
- **[R2]** Sagovsky, A. & Johnson, S.D. (2007). "When does repeat burglary victimisation occur?" *Australian & New Zealand Journal of Criminology*, 40(1). DOI: [10.1375/acri.40.1.1](https://journals.sagepub.com/doi/abs/10.1375/acri.40.1.1) — accessed 19 Aug 2026.
- **[R3]** Caplan, J.M., Kennedy, L.W. & Miller, J. (2011). "Risk Terrain Modeling: Brokering Criminological Theory and GIS Methods for Crime Forecasting." *Justice Quarterly*, 28(2), 360–381. DOI: [10.1080/07418825.2010.486037](https://www.tandfonline.com/doi/abs/10.1080/07418825.2010.486037) — accessed 19 Aug 2026.
- **[R4]** Caplan, J.M. & Kennedy, L.W. *Risk Terrain Modeling: Crime Prediction and Risk Reduction.* University of California Press. ISBN 9780520282933. [ucpress.edu](https://www.ucpress.edu/books/risk-terrain-modeling/paper) — accessed 19 Aug 2026.
- **[R5]** Mohler, G.O., Short, M.B., Brantingham, P.J., Schoenberg, F.P. & Tita, G.E. (2011). "Self-Exciting Point Process Modeling of Crime." *Journal of the American Statistical Association*, 106(493), 100–108. DOI: [10.1198/jasa.2011.ap09546](https://www.ingentaconnect.com/content/10.1198/jasa.2011.ap09546) — accessed 19 Aug 2026.
- **[R6]** Mohler, G.O. et al. (2015). "Randomized Controlled Field Trials of Predictive Policing." *Journal of the American Statistical Association*, 110(512), 1399–1411. DOI: [10.1080/01621459.2015.1077710](https://www.tandfonline.com/doi/abs/10.1080/01621459.2015.1077710) — accessed 19 Aug 2026.
- **[R7]** Saunders, J., Hunt, P. & Hollywood, J.S. (2016). "Predictions put into practice: a quasi-experimental evaluation of Chicago's predictive policing pilot." *Journal of Experimental Criminology*, 12(3), 347–371. DOI: [10.1007/s11292-016-9272-0](https://link.springer.com/article/10.1007/s11292-016-9272-0) — accessed 19 Aug 2026.

**Predictive policing — critiques**

- **[R8]** Sankin, A. & Mehrotra, D. (2 Oct 2023). "Predictive Policing Software Terrible at Predicting Crimes." *The Markup*, co-published with *WIRED*. [themarkup.org](https://themarkup.org/prediction-bias/2023/10/02/predictive-policing-software-terrible-at-predicting-crimes) · methodology: [Show Your Work](https://themarkup.org/show-your-work/2023/10/02/how-we-assessed-the-accuracy-of-predictive-policing-software) · data: [github.com/the-markup/investigation-geolitica-plainfield](https://github.com/the-markup/investigation-geolitica-plainfield) — accessed 19 Aug 2026.
- **[R9]** Haskins, C. (21 Apr 2020). "The Tool Was Supposed To Predict Crime. Now Los Angeles Police Say They Are Dumping It." *BuzzFeed News*. [buzzfeednews.com](https://www.buzzfeednews.com/article/carolinehaskins1/los-angeles-police-department-dumping-predpol-predictive) — accessed 19 Aug 2026.
- **[R10]** Lum, K. & Isaac, W. (2016). "To predict and serve?" *Significance*, 13(5), 14–19. DOI: [10.1111/j.1740-9713.2016.00960.x](https://rss.onlinelibrary.wiley.com/doi/full/10.1111/j.1740-9713.2016.00960.x) — accessed 19 Aug 2026.
- **[R11]** Ensign, D., Friedler, S.A., Neville, S., Scheidegger, C. & Venkatasubramanian, S. (2018). "Runaway Feedback Loops in Predictive Policing." *FAT\**. arXiv: [1706.09847](https://arxiv.org/pdf/1706.09847) — accessed 19 Aug 2026.
- **[R12]** Ferguson, A.G. (2017). *The Rise of Big Data Policing: Surveillance, Race, and the Future of Law Enforcement.* NYU Press. ISBN 9781479892822. [nyupress.org](https://nyupress.org/9781479892822/the-rise-of-big-data-policing/) — accessed 19 Aug 2026.

**Evaluation metrics**

- **[R13]** Chainey, S., Tompson, L. & Uhlig, S. (2008). "The Utility of Hotspot Mapping for Predicting Spatial Patterns of Crime." *Security Journal*, 21(1–2). DOI: [10.1057/palgrave.sj.8350066](https://link.springer.com/article/10.1057/palgrave.sj.8350066) — **origin of the Prediction Accuracy Index (PAI)**. Accessed 19 Aug 2026.
- **[R14]** National Institute of Justice. *Real-Time Crime Forecasting Challenge* (2017) — PAI and PEI\* as the official scoring metrics; Portland Police Bureau data, 1 Mar – 31 May 2017. [nij.ojp.gov posting](https://nij.ojp.gov/funding/real-time-crime-forecasting-challenge-posting) · [winners](https://nij.ojp.gov/real-time-crime-forecasting-challenge-winners) — accessed 19 Aug 2026.
- **[R15]** White, V.M., Hunt, J. & Green, B. (2023). "A discussion of current crime forecasting indices and an improvement to the prediction efficiency index for applications." *Security Journal*. DOI: [10.1057/s41284-023-00367-4](https://doi.org/10.1057/s41284-023-00367-4) · NIJ record NCJ 306617 — accessed 19 Aug 2026.

**Commercial and government systems**

- **[R16]** BriefCam. "BriefCam To Be Acquired by Canon Inc." (2018). [briefcam.com](https://www.briefcam.com/company/press-releases/briefcam-to-be-acquired-by-canon-inc/) — accessed 19 Aug 2026.
- **[R17]** Milestone Systems, *Annual Report 2024* — acquisition of BriefCam analytics and Arcules cloud. [milestonesys.com](https://www.milestonesys.com/company/news/press-releases/2024-annual-report/) — accessed 19 Aug 2026.
- **[R18]** BriefCam FAQ, "What are the graphical processing unit (GPU) requirements for the BriefCam solution?" — NVIDIA GPU required on the Processing Server; a single GPU cannot process real-time and on-demand simultaneously. [briefcam.com](https://www.briefcam.com/faq/what-are-the-graphical-processing-unit-gpu-requirements-for-the-briefcam-solution/) — accessed 19 Aug 2026.
- **[R19]** Axon. "Axon Accelerates Real-Time Operations Solution with Strategic Acquisition of Fusus", 1 Feb 2024. [investor.axon.com](https://investor.axon.com/2024-02-01-Axon-Accelerates-Real-Time-Operations-Solution-with-Strategic-Acquisition-of-Fusus) — accessed 19 Aug 2026.
- **[R20]** *The Lawrence Times*, "Lawrence police to update city commission on camera surveillance program, future plans", 8 Sep 2025 — ~\$3.2M consolidated contract through Jan 2029. [lawrencekstimes.com](https://lawrencekstimes.com/2025/09/08/lpd-city-comm-fusus-update-pre/) — accessed 19 Aug 2026. Dearborn (\$720k / 5 yr) and Columbia (\$315k / 3 yr) figures are from local press in the same coverage cluster; see "Explicitly unverified" item 4.
- **[R21]** Milestone Systems — discontinuation of XProtect Essential+ at the XProtect 2025 R2 release; activation of previously downloaded Essential+ licences ends 1 Jan 2026; entry point becomes the paid Express+. Quoted notice and discussion: [ipcamtalk.com](https://ipcamtalk.com/threads/milestone-discontinues-free-xprotect-essential.81158/) · variant comparison: [milestonesys.com](https://www.milestonesys.com/products/software/xprotect-comparison/) — accessed 19 Aug 2026. **[partially unverified]** — see "Explicitly unverified" item 2.
- **[R22]** Ministry of Home Affairs — CCTNS programme brief (launched 2009; ~17,700 police stations). [mha.gov.in](https://www.mha.gov.in/sites/default/files/CCTNS_Briefportal24042018.pdf) — accessed 19 Aug 2026.
- **[R23]** Ministry of Home Affairs — Inter-Operable Criminal Justice System (ICJS), established 2017, linking CCTNS, e-Courts, e-Prisons, e-Prosecution and e-Forensics; ICJS 2.0 rollout. [mha.gov.in](https://www.mha.gov.in/en/commoncontent/inter-operable-criminal-justice-system-icjs) — accessed 19 Aug 2026.
- **[R24]** *Indian Masterminds*, "Project Vishwas 2.0: Gujarat Builds Statewide AI-Ready Surveillance Before Hosting 2030 Commonwealth Games", 27 Nov 2025 — VISWAS = Video Integration and Statewide Advanced Security; Phase 1: 7,000 cameras; Phase 2: 12,500 cameras, 54 cities, 79 interstate check posts. [indianmasterminds.com](https://indianmasterminds.com/states/gujarat/gujarat-project-vishwas-next-gen-policing-2030-games-163580/) — accessed 19 Aug 2026.
- **[R25]** *Gujarat Samachar* (English), "Ahmedabad police claim major improvement in crime detection through CCTV surveillance", 25 Feb 2026 — 6,703 active public CCTV cameras (3,409 to police stations, 3,294 to control room); programme began March 2025. [english.gujaratsamachar.com](https://english.gujaratsamachar.com/news/gujarat/ahmedabad-police-claim-major-improvement-in-crime-detection-through-cctv-surveillance-83828226265.html) — accessed 19 Aug 2026.
- **[R26]** Press Information Bureau, Government of India — ₹2,919.55 crore under the Nirbhaya Fund for Safe City projects in eight cities including Ahmedabad; 60:40 Centre–State cost share. [pib.gov.in](https://www.pib.gov.in/Pressreleaseshare.aspx?PRID=1541560&reg=3&lang=2) · MHA Safe City page: [mha.gov.in](https://www.mha.gov.in/en/commoncontent/safe-city-projects) — accessed 19 Aug 2026.

**Models used off-the-shelf in this project**

- **[R27]** Radford, A. et al. (2021). "Learning Transferable Visual Models From Natural Language Supervision." arXiv: [2103.00020](https://arxiv.org/abs/2103.00020) — CLIP. Accessed 19 Aug 2026.
- **[R28]** Ultralytics YOLOv8 — [docs.ultralytics.com](https://docs.ultralytics.com/). **There is no peer-reviewed publication for YOLOv8**; it is a maintained implementation, not a published architecture. Accessed 19 Aug 2026.
- **[R29]** Deng, J., Guo, J., Xue, N. & Zafeiriou, S. (2019). "ArcFace: Additive Angular Margin Loss for Deep Face Recognition." *CVPR 2019*. arXiv: [1801.07698](https://arxiv.org/abs/1801.07698) — accessed 19 Aug 2026.
- **[R30]** Johnson, J., Douze, M. & Jégou, H. "Billion-scale similarity search with GPUs." *IEEE Transactions on Big Data*, 7(3), 535–547. arXiv: [1702.08734](https://arxiv.org/abs/1702.08734) — FAISS. Accessed 19 Aug 2026.
- **[R31]** Zhang, Y. et al. (2022). "ByteTrack: Multi-Object Tracking by Associating Every Detection Box." *ECCV 2022*. arXiv: [2110.06864](https://arxiv.org/abs/2110.06864) — accessed 19 Aug 2026.

**Gujarat programmes, 2026**

- **[R32]** "Gujarat Police plans single network for 80,000 CCTV cameras, through AI-enabled hackathon", 17 Aug 2026 (ANI wire, via Prokerala) — DGP G.S. Malik; 80,000+ cameras; focus areas including suspicious person/vehicle/activity identification, real-time alerts, ANPR, vehicle tracking, watchlist matching and multi-camera search; two stages; ₹37 lakh; September start; i-Hub Gujarat, DA-IICT, NFSU. [prokerala.com](https://www.prokerala.com/news/articles/a1801331.html) — accessed 19 Aug 2026.
- **[R33]** ANI, "Gujarat Police to host country's largest AI-based CCTV hackathon", 17 Aug 2026. [aninews.in](https://www.aninews.in/news/national/general-news/gujarat-police-to-host-countrys-largest-ai-based-cctv-hackathon20260817135250/) — accessed 19 Aug 2026.
- **[R34]** ANI, "Gujarat launches 'Cyber Financial Fraud e-Zero FIR' service; victims can register complaints from home", 27 Jul 2026. [aninews.in](https://www.aninews.in/news/national/general-news/gujarat-launches-cyber-financial-fraud-e-zero-fir-service-victims-can-register-complaints-from-home20260727123630/) — accessed 19 Aug 2026.
- **[R35]** *The Shillong Times*, "'No police station visit': Gujarat launches e-Zero FIR system for cyber fraud victims", 27 Jul 2026 — launched by Dy CM Harsh Sanghavi at Gandhinagar; 1930/I4C auto-generates an e-Zero FIR routed to the jurisdictional station; first case prevented a ₹15.76 lakh loss (Ahmedabad digital-arrest fraud). [theshillongtimes.com](https://theshillongtimes.com/2026/07/27/no-police-station-visit-gujarat-launches-e-zero-fir-system-for-cyber-fraud-victims/) — accessed 19 Aug 2026.

---

## Explicitly unverified

Listed here so a reviewer does not have to hunt for the soft spots.

1. **Genetec and BriefCam list pricing** — not published by either vendor; all figures are quote-based via integrators. No number is asserted anywhere in this document.
2. **Milestone XProtect Essential+ discontinuation** [R21] — the substance (discontinued at 2025 R2; activation ends 1 Jan 2026; Express+ becomes the entry point) is quoted from Milestone communications reproduced on a third-party forum. The primary Milestone release note was not directly retrievable. Treat the *date* as high-confidence but secondary-sourced.
3. **The official Gujarat Police Innovation Challenge problem-statement document** — not retrievable at time of writing (the official portal listing did not resolve). §5.1's focus-area list comes from wire reporting [R32], not from the official portal. **Re-verify before any submission relies on it.**
4. **Dearborn (\$720k / 5 yr) and Columbia (\$315k / 3 yr) Fusus contract figures** — local press reports; only the Lawrence, KS figure is directly sourced to [R20]. The order-of-magnitude range is the load-bearing claim, not the individual figures.
5. **No claim of real-world crime reduction** is made anywhere in this repo, and none can be supported. Establishing one would require a field trial of the kind in [R6].
