# Ahmedabad Crime & Disaster Data (Demo Reference)

Compiled to power a realistic area-wise crime heatmap and demo seed data for CityShield / VisionScan.

> **IMPORTANT DISCLAIMER (read first):** The figures and intensity ratings in this
> document are **approximations compiled from public sources for demonstration purposes
> only**. India's NCRB and police data are published at the *city* and *police-zone*
> level, **not** per-neighbourhood. There is **no official open dataset that ranks
> Ahmedabad localities (e.g. Navrangpura vs. Vatva) by crime intensity.** The
> locality-level "intensity" and "dominant category" assignments below are *editorial
> estimates* derived by mapping (a) NCRB/police category totals, (b) press-reported
> hotspot patterns, and (c) the well-documented east/west socio-economic divide of the
> city onto the supported map localities. They must **not** be presented as authoritative
> crime ratings of any neighbourhood, and no real individuals are named anywhere in this
> file or the seed data.

---

## 1. Sources & reliability

| # | Source | URL | What it gives us | Reliability |
|---|--------|-----|------------------|-------------|
| S1 | NCRB *Crime in India 2022* (official report) | https://www.ncrb.gov.in/uploads/nationalcrimerecordsbureau/custom/1701607577CrimeinIndia2022Book1.pdf | City-level crime totals & rates; Ahmedabad crime rate ~96.6 per 100k (5th among metros) | High (official, but city-level only, ~2-yr lag) |
| S2 | Open Government Data (OGD) Platform — Crime in India 2022 | https://www.data.gov.in/catalog/crime-india-2022 | Machine-readable city crime tables | High (official) |
| S3 | Gujarat Samachar (English) — "Ahmedabad Cyber Crimes surge 61% in 2024" | https://english.gujaratsamachar.com/news/gujarat/ahmedabad-cyber-crimes-surge-61-in-2024-amid-statewide-decline-ncrb-37168049478.html | 2024 cyber-crime breakdown (396 cases, category split, motives) | Medium-High (reputable daily citing NCRB) |
| S4 | Gujarat Samachar — "NCRB report reveals safety concerns for seniors in Ahmedabad" | https://english.gujaratsamachar.com/news/gujarat/ncrb-report-reveals-safety-concerns-for-seniors-in-ahmedabad | 2023 elderly-victim burglary/fraud/intimidation counts | Medium-High |
| S5 | Vibes of India — "AI Helps Ahmedabad Cops To Predict Crimes" | https://www.vibesofindia.com/ai-helps-ahmedabad-cops-to-predict-crimes/ | Named hotspot localities for two-wheeler theft & chain-snatching (Chandkheda, Khokhra, Rakhial, Maninagar) | Medium (press, paraphrasing police AI model) |
| S6 | Gujarat Samachar — "Crime Branch busts chain-snatching gang" | https://english.gujaratsamachar.com/news/gujarat/ahmedabad-crime-branch-busts-chain-snatching-gang | Chain-snatching cases mapped to Satellite, Navrangpura, Anandnagar, Ghatlodia, Ellisbridge, Paldi | Medium-High |
| S7 | The420.in — "Digital Arrest Gang Busted in Ahmedabad, ₹2.27 Cr" | https://the420.in/digital-arrest-gang-ahmedabad-busted-227-crore-fraud-4-arrested/ | Notable digital-arrest cyber-fraud incident, 2024 | Medium |
| S8 | The420.in — "Ahmedabad Records 694 Cyber Fraud Cases in 2 Years" | https://the420.in/ahmedabad-records-694-cyber-fraud-cases-664-accused-arrested/ | Cyber-fraud distribution across police stations (Naroda 21, Vatva 1, central Cyber PS 238) Feb-2024–Jan-2026 | Medium |
| S9 | DNA India — "Zone 5: Ahmedabad's 'murder capital'" | https://www.dnaindia.com/india/report-zone-5-ahmedabad-s-murder-capital-1483736 | Eastern Zone-5 belt (Gomtipur, Bapunagar, Rakhial, Odhav, Amraiwadi, Ramol) as violent-crime concentration | Medium (older, but structurally still cited) |
| S10 | DeshGujarat — "Ahmedabad Police Seize Over ₹42 Cr Liquor & Narcotics in 2 Years" | https://deshgujarat.com/2026/02/20/ahmedabad-police-seize-over-%E2%82%B942-crore-worth-of-liquor-and-narcotics-in-two-years/ | Prohibition/bootlegging & narcotics seizure scale | Medium-High |
| S11 | The Federal — "Ahmedabad flooded for a week as Sabarmati level raised" | https://thefederal.com/states/west/gujarat/ahmedabad-flooded-for-a-week-as-sabarmati-level-is-raised-for-cruise | 2024 monsoon waterlogging; AMC identified 125 problem spots, 300+ affected | Medium-High |
| S12 | Urban Acres — "Ahmedabad's Annual Flooding Root Causes" | https://urbanacres.in/ahmedabads-annual-flooding-root-causes-unveiled/ | Named waterlogging-prone areas (Ghuma-Bopal, Kathwada, Jodhpur); drainage capacity gap | Medium |
| S13 | Wikipedia — 2017 Gujarat flood | https://en.wikipedia.org/wiki/2017_Gujarat_flood | 2017 Sabarmati/Vasna Barrage flooding, 18 deaths in district, riverfront submerged | Medium |
| S14 | indiastatdistrictcrime — Ahmedabad district crime tables | https://www.indiastatdistrictcrime.com/GUJARAT/Ahmedabad/crimeandlaw/incidencecrime | District IPC crime incidence (aggregated) | Medium (paywalled aggregator of official data) |

**Reliability legend:** *High* = official government data. *Medium-High* = reputable mainstream
press directly citing official data. *Medium* = single press report / older or indirect data.

---

## 2. Headline figures (city-level, factual)

- **Ahmedabad crime rate ~96.6 per 100,000** (NCRB 2022) — 5th among major metros, behind
  Delhi (150.6), Chennai (101.6); ahead of Mumbai (73.3) and Surat (64.3). *(S1)*
- **Cyber crime 2024: 396 cases, +61% YoY** (from 246 in 2023) — a sharp rise even as
  Gujarat statewide cyber crime *fell* ~20%. *(S3)*
  - Cheating & forgery: **229 cases (~57%)** · Computer-related offences: 36 ·
    Identity theft: 30 · Obscene/explicit transmission: 40.
  - Motive split: **Fraud 261 (~65%)** · causing disrepute 80 · sexual exploitation 35 · extortion 20.
  - 343 arrests (327 M / 16 F).
- **Crimes against elderly (2023): 184 total** incl. **76 burglaries** targeting seniors'
  homes, 29 financial-fraud, 25 intimidation cases. *(S4)*
- **Prohibition/narcotics (2024):** foreign liquor ₹6.12 cr + country liquor ₹83.55 lakh +
  narcotics ₹16.66 cr seized (~₹24.5 cr that year); ~₹42 cr over two years. *(S10)*
- **East/West structural divide:** Eastern industrial/working-class belt (Zone 5/6 —
  Gomtipur, Bapunagar, Rakhial, Odhav, Amraiwadi, Naroda, Vatva) historically concentrates
  **violent / body-offence** crime; western planned suburbs (Satellite, SG Highway,
  Vastrapur, Bodakdev, Thaltej) skew toward **cyber-fraud, vehicle theft and chain-snatching**
  of affluent residents. *(S9, S5, S6)*

---

## 3. Category mix (approximate, demo weighting)

Derived from S1/S3/S4/S5/S6/S10. Treat as relative weights, not exact shares.

| Category | Relative weight | Notes |
|----------|-----------------|-------|
| Cyber fraud (digital arrest, OTP/UPI, loan/investment scam, ATM swap) | **High & fastest-growing** | 396 cases 2024, +61%; ~65% fraud-motivated *(S3)* |
| Vehicle theft (esp. two-wheeler) | High | AI-flagged hotspots Chandkheda, Khokhra *(S5)* |
| Chain snatching | Medium-High | Satellite, Navrangpura, Ghatlodia, Ellisbridge, Paldi, Rakhial, Maninagar *(S5,S6)* |
| Burglary / house break-in | Medium-High | 76 elderly-targeted burglaries in 2023 alone *(S4)* |
| Theft (general / pickpocketing) | Medium-High | Broad across markets & transit hubs |
| Assault / hurt / body offences | Medium (High in east) | Concentrated in eastern Zone-5 belt *(S9)* |
| Prohibition (bootlegging) & narcotics | Medium | Dry-state enforcement; large seizures *(S10)* |
| Cheating / economic fraud (non-cyber) | Medium | Overlaps cyber; senior-citizen targeting *(S4)* |
| Murder / culpable homicide | Low-Medium (clustered east) | Eastern belt "murder zone" reputation *(S9)* |

---

## 4. Locality → intensity → dominant categories

**Estimate basis:** mapped from the east/west divide (S9), named press hotspots (S5/S6),
and city category mix (S1/S3/S4). Every "intensity" is an **editorial estimate** for demo
realism — *not* an official neighbourhood crime rating. Localities not individually named in
any source are inferred from their zone/socio-economic character (flagged "inferred").

| Locality | Intensity (est.) | Dominant categories (est.) | Justification / source |
|----------|------------------|----------------------------|------------------------|
| Navrangpura | Medium | chain snatching, cyber fraud, theft | Named chain-snatching site *(S6)*; central commercial hub |
| Ellisbridge | Medium | chain snatching, theft, cyber fraud | Named chain-snatching site *(S6)* |
| Paldi | Medium | chain snatching, burglary, theft | Named chain-snatching site *(S6)* |
| Vasna | Medium | theft, vehicle theft, burglary | Inferred (mixed residential near Vasna barrage) |
| Vejalpur | Medium | vehicle theft, cyber fraud, theft | Inferred (dense west-central residential) |
| Satellite | High | cyber fraud, chain snatching, vehicle theft | Named chain-snatching site *(S6)*; affluent west = cyber target |
| Vastrapur | Medium-High | cyber fraud, chain snatching, theft | Affluent west suburb; cyber-fraud target (inferred from S6/S9) |
| Bodakdev | Medium-High | cyber fraud, burglary, vehicle theft | Affluent west; high-value-target inference *(S9)* |
| Thaltej | Medium-High | cyber fraud, vehicle theft, burglary | Affluent west; inference *(S9)* |
| Bopal | Medium | cyber fraud, vehicle theft, burglary | West fringe growth; also flood-prone (Ghuma-Bopal) *(S12)* |
| SG Highway | High | cyber fraud, vehicle theft, theft | Commercial west corridor; affluent target (inferred) |
| Gota | Medium | vehicle theft, burglary, cyber fraud | Fast-growing NW suburb (inferred) |
| Ghatlodia | Medium-High | chain snatching, vehicle theft, theft | Named chain-snatching site *(S6)* |
| Memnagar | Medium | chain snatching, theft, cyber fraud | West-central residential near Navrangpura (inferred) |
| Ranip | Medium | vehicle theft, theft, assault | NW transitional belt (inferred) |
| Chandkheda | Medium-High | vehicle theft (two-wheeler), burglary | AI-flagged two-wheeler-theft hotspot *(S5)* |
| Sabarmati | Medium | theft, vehicle theft, assault | Mixed belt; near riverfront flood zone (inferred) |
| Shahibaug | Medium | theft, cyber fraud, assault | Central-east mixed area (inferred) |
| Asarwa | Medium-High | assault, theft, body offences | Eastern belt near civil-hospital area *(S9)* |
| Bapunagar | High | assault, body offences, theft | Eastern Zone-5 "murder belt" *(S9)* |
| Naroda | High | assault, vehicle theft, body offences, cyber fraud | Eastern industrial belt *(S9)*; some cyber cases *(S8)* |
| Nikol | Medium-High | vehicle theft, theft, assault | Dense east residential adjoining Naroda (inferred) |
| Odhav | High | assault, body offences, vehicle theft | Eastern industrial Zone-5 belt *(S9)* |
| Gomtipur | High | murder, assault, body offences | Eastern "murder zone" core *(S9)* |
| Maninagar | Medium-High | chain snatching, theft, vehicle theft | AI-flagged chain-snatching hotspot *(S5)* |
| Kankaria | Medium | theft, pickpocketing, chain snatching | High-footfall lakefront/tourist zone (inferred) |
| Isanpur | Medium | vehicle theft, theft, assault | SE residential-industrial fringe (inferred) |
| Vatva | High | assault, body offences, narcotics, theft | Eastern GIDC industrial belt *(S9)*; low cyber *(S8)* |
| Behrampura | Medium-High | theft, assault, body offences | South-central low-income belt; flood-prone (inferred) |
| Jamalpur | Medium-High | theft, assault, chain snatching | Dense old-city market area; high footfall (inferred) |

---

## 5. Seed incidents (generic, public-reported)

All are based on publicly reported event *types*. No private individuals are named; amounts
and dates are approximate. Suitable as demo complaint/case seeds.

| # | Title | Category | Area | Severity | Year |
|---|-------|----------|------|----------|------|
| 1 | Digital-arrest cyber-fraud ring busted | cyber_fraud | Satellite | high | 2024 |
| 2 | Cambodia-linked OTP/loan scam call-centre raided | cyber_fraud | Bodakdev | high | 2024 |
| 3 | Chain-snatching gang traced across west Ahmedabad | chain_snatching | Navrangpura | medium | 2024 |
| 4 | Evening chain-snatching spree on lone pedestrians | chain_snatching | Ellisbridge | medium | 2024 |
| 5 | Two-wheeler theft cluster flagged on Wednesday nights | vehicle_theft | Chandkheda | medium | 2024 |
| 6 | Two-wheeler theft alert raised by predictive policing | vehicle_theft | Khokhra/Maninagar | medium | 2024 |
| 7 | ATM card-swap fraud against senior citizen | cyber_fraud | Maninagar | medium | 2024 |
| 8 | Burglary targeting an elderly resident's home | burglary | Paldi | medium | 2023 |
| 9 | Night-time house break-in in residential society | burglary | Thaltej | medium | 2024 |
| 10 | Illegal liquor-manufacturing unit busted | prohibition | Vatva | medium | 2024 |
| 11 | Narcotics consignment seized in enforcement drive | narcotics | Odhav | high | 2024 |
| 12 | Assault / brawl in eastern industrial belt | assault | Bapunagar | high | 2023 |
| 13 | Violent altercation reported in dense locality | assault | Gomtipur | high | 2023 |
| 14 | Pickpocketing & theft surge at lakefront crowds | theft | Kankaria | low | 2024 |
| 15 | Market-area snatching during festival rush | theft | Jamalpur | medium | 2024 |
| 16 | Fake investment-app scam defrauds residents | cyber_fraud | SG Highway | high | 2024 |
| 17 | Parked-vehicle theft reported near commercial hub | vehicle_theft | Ghatlodia | medium | 2024 |
| 18 | Loan-app extortion call-centre network exposed | cyber_fraud | Vastrapur | high | 2024 |
| 19 | Monsoon waterlogging stranded residents | disaster_flood | Bopal | high | 2024 |
| 20 | Riverfront low-zone flooding after dam release | disaster_flood | Vasna | high | 2017 |

---

## 6. Flood / disaster-prone areas

From S11/S12/S13 plus low-lying-belt inference. The 2024 monsoon affected **300+ spots**
(AMC pre-identified 125); the 2017 Sabarmati event flooded riverfront/low zones after
Dharoi/Dantiwada dam releases and Vasna Barrage opening.

**Named in sources:** Ghuma-Bopal, Kathwada, Jodhpur *(S12)*; Sabarmati riverfront / Vasna
Barrage low zones *(S13)*.

**Demo flood-prone list (named + low-lying inference):** Bopal, Vasna, Behrampura, Jamalpur,
Sabarmati (riverfront), Paldi (river-adjacent), Vatva, Isanpur, Maninagar, Naroda, Odhav,
Ranip, Chandkheda. *(Items beyond the source-named ones are low-lying/old-city inferences for demo use.)*

---

## 7. Disclaimer (repeat for downstream display)

> This dataset is an **approximation compiled from public sources (NCRB reports, Gujarat
> Police/press coverage, and municipal flood reporting) strictly for a civic-tech
> demonstration.** Crime in India is officially published only at city/zone granularity, so
> all neighbourhood-level intensity ratings are **editorial estimates**, not official
> measurements. No real individuals are identified. Figures, dates, and amounts are
> indicative. Do not use this data for operational, legal, real-estate, or any
> decision-making purpose, or to characterise the actual safety of any real neighbourhood.
