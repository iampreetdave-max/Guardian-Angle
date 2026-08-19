/* City Map (GIS command view) — layers, risk forecast, patrol planner,
   hotspot popups, cyber-fraud layer, model card and backtest panel.

   Plural pairs (report/reports, victim/victims …) exist because English needs
   them; Hindi and Gujarati repeat the same noun in both slots, which keeps the
   call sites identical across all three languages.

   `band.*` and `trend.*` are nested to match the API's closed enums
   (high|elevated|guarded|low, rising|falling|stable) so the render site can do
   t(`citymap.band.${a.risk_band}`) without a lookup table. */
export default {
  en: {
    title: "City Map · Ahmedabad",
    loading: "Loading city intelligence…",

    subReports:
      "Area-wise load from {c} complaints, {k} linked cases and {a} anomaly detections.",
    subRisk:
      "Hotspot forecast — recency-weighted risk model over reports, severity, category and live anomaly signals.",
    subCyber:
      "Victim-location density — where victims live, not where fraudsters operate.",

    layerReports: "Reports",
    layerRisk: "Risk forecast",
    layerCyber: "Cyber fraud",

    allCategories: "All categories",
    win7: "7 days",
    win30: "30 days",
    win90: "90 days",
    winAll: "All time",

    clearRoutes: "Clear routes",
    unitsAvailable: "Patrol units available",
    planRoutes: "Plan patrol routes",
    patrolPlan: "Patrol plan",
    exportPatrolCsv: "Export this patrol plan as CSV",
    exportRiskCsv: "Export the full ranked risk table as CSV",
    exportCsv: "Export CSV",
    unitLabel: "Unit {n}",
    unitTooltip: "Unit {n}: {km} km · ~{min} min",
    routeStats: "{km} km · ~{min} min",

    tilesOffline: "Map tiles unavailable — running offline; data layers still live",

    complaints: "Complaints",
    cases: "Cases",
    topCategory: "Top category",
    risk: "Risk",
    riskScore: "Risk score",
    forecast: "Forecast",
    riskTooltip: "{area}: risk {score} ({band})",

    band: { low: "low", guarded: "guarded", elevated: "elevated", high: "high" },
    trend: { rising: "rising", falling: "falling", stable: "stable" },

    topFraudType: "Top fraud type",
    victimsLabel: "Victims",
    totalAmount: "₹ total",
    via: "via",
    cyberChip: "{amount} lost citywide · {victims} victims · last {days} days",
    topChannels: "Top fraud channels",
    noChannelData: "No channel data in window.",

    topHotspots: "Top predicted hotspots",
    byHour: "Reports by hour of day",
    byDay: "By day of week",

    whyTitle: "Why this hotspot?",
    segPrior: "baseline prior",
    segRecent: "{cat} (recent)",
    segAnomaly: "live anomaly boost",
    whyLead: "Risk {score} = prior {prior}",
    whyCat: " + {v} from recent {cat}",
    whyMore: " (+{n} more)",
    whyAnomaly: " + {v} live anomaly boost",
    whyOver: " over {n} {noun} (recency-decayed).",

    modelCard: "Model card",
    modelCardTitle: "Risk model card",
    halfLife: "Half-life",
    days: "{n} days",
    trendWindow: "Trend window",
    anomalyBoost: "Anomaly boost",
    reportsUsed: "Reports used",
    topWeights: "Top category weights",
    recomputed: "Recomputed from {n} reports ·",

    accuracy: "Model accuracy (backtested)",
    caughtPre: "Caught ",
    caughtPost: " planted crime waves.",
    caughtWaves: "Caught {n}/{m} planted crime waves",
    backtesting: "Backtesting…",
    surgePre: "{area} surfaced rank",
    surgePost: "the week its {cat} wave hit.",
    captureCurve: "Capture curve",
    top10Pre: "Top-10 zones =",
    top10Post: "of next-week crime.",
    topK: "top-{k}",
    ofCeiling: " of {x}× ceiling",
    vsOracle: "vs oracle",
    ceilingNote:
      "PAI {pai}× of the {oracle}× perfect-hindsight ceiling ≈ {pct}% of what's achievable on this data.",
    vsBaselines: "vs baselines (PAI@10)",

    disclaimer:
      "Risk scores are recency-weighted model estimates over locality-level approximations — decision support for patrol planning, not evidence. Built on fully synthetic, deterministic demo data; accuracy figures demonstrate methodology, not real-world performance (data provenance:",

    report: "report",
    reports: "reports",
    victim: "victim",
    victims: "victims",
    unitWord: "unit",
    unitWords: "units",
    anomalyAlert: "anomaly alert",
    anomalyAlerts: "anomaly alerts",
    anomalySignal: "live anomaly signal",
    anomalySignals: "live anomaly signals",
  },

  hi: {
    title: "सिटी मैप · अहमदाबाद",
    loading: "शहर की सूचना लोड हो रही है…",

    subReports:
      "{c} शिकायतों, {k} जुड़े प्रकरणों और {a} विसंगति पहचानों से क्षेत्रवार भार।",
    subRisk:
      "हॉटस्पॉट पूर्वानुमान — रिपोर्ट, गंभीरता, श्रेणी और लाइव विसंगति संकेतों पर नवीनता-भारित जोखिम मॉडल।",
    subCyber:
      "पीड़ित-स्थान घनत्व — जहाँ पीड़ित रहते हैं, वहाँ नहीं जहाँ ठग सक्रिय हैं।",

    layerReports: "रिपोर्ट",
    layerRisk: "जोखिम पूर्वानुमान",
    layerCyber: "साइबर ठगी",

    allCategories: "सभी श्रेणियाँ",
    win7: "7 दिन",
    win30: "30 दिन",
    win90: "90 दिन",
    winAll: "सभी समय",

    clearRoutes: "रूट हटाएँ",
    unitsAvailable: "उपलब्ध गश्ती यूनिट",
    planRoutes: "गश्ती रूट बनाएँ",
    patrolPlan: "गश्ती योजना",
    exportPatrolCsv: "यह गश्ती योजना CSV में निर्यात करें",
    exportRiskCsv: "पूरी जोखिम तालिका CSV में निर्यात करें",
    exportCsv: "CSV निर्यात",
    unitLabel: "यूनिट {n}",
    unitTooltip: "यूनिट {n}: {km} किमी · ~{min} मिनट",
    routeStats: "{km} किमी · ~{min} मिनट",

    tilesOffline: "मैप टाइल्स उपलब्ध नहीं — ऑफ़लाइन चल रहा है; डेटा लेयर चालू हैं",

    complaints: "शिकायतें",
    cases: "प्रकरण",
    topCategory: "मुख्य श्रेणी",
    risk: "जोखिम",
    riskScore: "जोखिम अंक",
    forecast: "पूर्वानुमान",
    riskTooltip: "{area}: जोखिम {score} ({band})",

    band: { low: "कम", guarded: "सतर्क", elevated: "बढ़ा हुआ", high: "उच्च" },
    trend: { rising: "बढ़ रहा", falling: "घट रहा", stable: "स्थिर" },

    topFraudType: "मुख्य ठगी प्रकार",
    victimsLabel: "पीड़ित",
    totalAmount: "₹ कुल",
    via: "माध्यम",
    cyberChip: "शहरभर में {amount} की हानि · {victims} पीड़ित · पिछले {days} दिन",
    topChannels: "मुख्य ठगी माध्यम",
    noChannelData: "इस अवधि में माध्यम डेटा नहीं।",

    topHotspots: "शीर्ष अनुमानित हॉटस्पॉट",
    byHour: "घंटेवार रिपोर्ट",
    byDay: "दिनवार",

    whyTitle: "यह हॉटस्पॉट क्यों?",
    segPrior: "आधार मान",
    segRecent: "{cat} (हालिया)",
    segAnomaly: "लाइव विसंगति बढ़त",
    whyLead: "जोखिम {score} = आधार {prior}",
    whyCat: " + हालिया {cat} से {v}",
    whyMore: " (+{n} और)",
    whyAnomaly: " + {v} लाइव विसंगति बढ़त",
    whyOver: " — {n} {noun} पर (नवीनता-भारित)।",

    modelCard: "मॉडल कार्ड",
    modelCardTitle: "जोखिम मॉडल कार्ड",
    halfLife: "अर्ध-आयु",
    days: "{n} दिन",
    trendWindow: "प्रवृत्ति अवधि",
    anomalyBoost: "विसंगति बढ़त",
    reportsUsed: "प्रयुक्त रिपोर्ट",
    topWeights: "मुख्य श्रेणी भार",
    recomputed: "{n} रिपोर्ट से पुनर्गणित ·",

    accuracy: "मॉडल सटीकता (बैकटेस्टेड)",
    caughtPre: "",
    caughtPost: " नियोजित अपराध लहरें पकड़ीं।",
    caughtWaves: "{n}/{m} नियोजित अपराध लहरें पकड़ीं",
    backtesting: "बैकटेस्ट हो रहा है…",
    surgePre: "{area} रैंक",
    surgePost: "पर पहुँचा — उसी सप्ताह जब {cat} की लहर आई।",
    captureCurve: "कैप्चर कर्व",
    top10Pre: "शीर्ष-10 क्षेत्र =",
    top10Post: "अगले सप्ताह का अपराध।",
    topK: "शीर्ष-{k}",
    ofCeiling: " / {x}× सीमा",
    vsOracle: "बनाम आदर्श",
    ceilingNote:
      "PAI {pai}× बनाम {oracle}× पूर्ण-पूर्वदृष्टि सीमा ≈ इस डेटा पर संभव का {pct}%।",
    vsBaselines: "बनाम आधाररेखा (PAI@10)",

    disclaimer:
      "जोखिम अंक क्षेत्र-स्तरीय अनुमानों पर नवीनता-भारित मॉडल आकलन हैं — गश्त नियोजन हेतु निर्णय-सहायक, साक्ष्य नहीं। पूर्णतः कृत्रिम, नियतात्मक डेमो डेटा पर आधारित; सटीकता आँकड़े पद्धति दर्शाते हैं, वास्तविक प्रदर्शन नहीं (डेटा स्रोत:",

    report: "रिपोर्ट",
    reports: "रिपोर्ट",
    victim: "पीड़ित",
    victims: "पीड़ित",
    unitWord: "यूनिट",
    unitWords: "यूनिट",
    anomalyAlert: "विसंगति अलर्ट",
    anomalyAlerts: "विसंगति अलर्ट",
    anomalySignal: "लाइव विसंगति संकेत",
    anomalySignals: "लाइव विसंगति संकेत",
  },

  gu: {
    title: "સિટી મેપ · અમદાવાદ",
    loading: "શહેરની માહિતી લોડ થઈ રહી છે…",

    subReports:
      "{c} ફરિયાદો, {k} જોડાયેલા કેસ અને {a} વિસંગતિ શોધ પરથી વિસ્તારવાર ભાર.",
    subRisk:
      "હોટસ્પોટ આગાહી — રિપોર્ટ, ગંભીરતા, શ્રેણી અને લાઇવ વિસંગતિ સંકેતો પર તાજેતરતા-ભારિત જોખમ મોડેલ.",
    subCyber:
      "પીડિત-સ્થાન ઘનતા — જ્યાં પીડિતો રહે છે, ઠગ જ્યાં કાર્યરત છે ત્યાં નહીં.",

    layerReports: "રિપોર્ટ",
    layerRisk: "જોખમ આગાહી",
    layerCyber: "સાયબર ઠગાઈ",

    allCategories: "બધી શ્રેણીઓ",
    win7: "7 દિવસ",
    win30: "30 દિવસ",
    win90: "90 દિવસ",
    winAll: "બધો સમય",

    clearRoutes: "રૂટ હટાવો",
    unitsAvailable: "ઉપલબ્ધ પેટ્રોલિંગ યુનિટ",
    planRoutes: "પેટ્રોલિંગ રૂટ બનાવો",
    patrolPlan: "પેટ્રોલિંગ યોજના",
    exportPatrolCsv: "આ પેટ્રોલિંગ યોજના CSV માં નિકાસ કરો",
    exportRiskCsv: "સંપૂર્ણ જોખમ કોષ્ટક CSV માં નિકાસ કરો",
    exportCsv: "CSV નિકાસ",
    unitLabel: "યુનિટ {n}",
    unitTooltip: "યુનિટ {n}: {km} કિમી · ~{min} મિનિટ",
    routeStats: "{km} કિમી · ~{min} મિનિટ",

    tilesOffline: "મેપ ટાઇલ્સ ઉપલબ્ધ નથી — ઑફલાઇન ચાલે છે; ડેટા લેયર ચાલુ છે",

    complaints: "ફરિયાદો",
    cases: "કેસ",
    topCategory: "મુખ્ય શ્રેણી",
    risk: "જોખમ",
    riskScore: "જોખમ સ્કોર",
    forecast: "આગાહી",
    riskTooltip: "{area}: જોખમ {score} ({band})",

    band: { low: "ઓછું", guarded: "સાવધ", elevated: "વધેલું", high: "ઊંચું" },
    trend: { rising: "વધતું", falling: "ઘટતું", stable: "સ્થિર" },

    topFraudType: "મુખ્ય ઠગાઈ પ્રકાર",
    victimsLabel: "પીડિતો",
    totalAmount: "₹ કુલ",
    via: "મારફતે",
    cyberChip: "શહેરભરમાં {amount} નુકસાન · {victims} પીડિતો · છેલ્લા {days} દિવસ",
    topChannels: "મુખ્ય ઠગાઈ માધ્યમો",
    noChannelData: "આ સમયગાળામાં માધ્યમ ડેટા નથી.",

    topHotspots: "ટોચના અનુમાનિત હોટસ્પોટ",
    byHour: "કલાક પ્રમાણે રિપોર્ટ",
    byDay: "વાર પ્રમાણે",

    whyTitle: "આ હોટસ્પોટ કેમ?",
    segPrior: "આધાર મૂલ્ય",
    segRecent: "{cat} (તાજેતરનું)",
    segAnomaly: "લાઇવ વિસંગતિ બુસ્ટ",
    whyLead: "જોખમ {score} = આધાર {prior}",
    whyCat: " + તાજેતરના {cat} થી {v}",
    whyMore: " (+{n} વધુ)",
    whyAnomaly: " + {v} લાઇવ વિસંગતિ બુસ્ટ",
    whyOver: " — {n} {noun} પર (તાજેતરતા-ભારિત).",

    modelCard: "મોડેલ કાર્ડ",
    modelCardTitle: "જોખમ મોડેલ કાર્ડ",
    halfLife: "અર્ધ-આયુ",
    days: "{n} દિવસ",
    trendWindow: "વલણ સમયગાળો",
    anomalyBoost: "વિસંગતિ બુસ્ટ",
    reportsUsed: "વપરાયેલ રિપોર્ટ",
    topWeights: "મુખ્ય શ્રેણી વજન",
    recomputed: "{n} રિપોર્ટ પરથી પુનર્ગણિત ·",

    accuracy: "મોડેલ ચોકસાઈ (બેકટેસ્ટેડ)",
    caughtPre: "",
    caughtPost: " આયોજિત ગુના લહેરો પકડી.",
    caughtWaves: "{n}/{m} આયોજિત ગુના લહેરો પકડી",
    backtesting: "બેકટેસ્ટ ચાલુ છે…",
    surgePre: "{area} રેન્ક",
    surgePost: "પર પહોંચ્યું — તે જ અઠવાડિયે જ્યારે {cat} લહેર આવી.",
    captureCurve: "કેપ્ચર કર્વ",
    top10Pre: "ટોચના-10 ઝોન =",
    top10Post: "આવતા અઠવાડિયાનો ગુનો.",
    topK: "ટોચ-{k}",
    ofCeiling: " / {x}× મર્યાદા",
    vsOracle: "આદર્શ સામે",
    ceilingNote:
      "PAI {pai}× એ {oracle}× સંપૂર્ણ-પશ્ચાદ્દર્શી મર્યાદાનો ≈ {pct}% — આ ડેટા પર શક્ય તેટલું.",
    vsBaselines: "આધારરેખા સામે (PAI@10)",

    disclaimer:
      "જોખમ સ્કોર વિસ્તાર-સ્તરીય અંદાજો પર તાજેતરતા-ભારિત મોડેલ આકલન છે — પેટ્રોલિંગ આયોજન માટે નિર્ણય-સહાય, પુરાવો નહીં. સંપૂર્ણ કૃત્રિમ, નિર્ધારિત ડેમો ડેટા પર આધારિત; ચોકસાઈના આંકડા પદ્ધતિ દર્શાવે છે, વાસ્તવિક પ્રદર્શન નહીં (ડેટા સ્રોત:",

    report: "રિપોર્ટ",
    reports: "રિપોર્ટ",
    victim: "પીડિત",
    victims: "પીડિત",
    unitWord: "યુનિટ",
    unitWords: "યુનિટ",
    anomalyAlert: "વિસંગતિ ચેતવણી",
    anomalyAlerts: "વિસંગતિ ચેતવણી",
    anomalySignal: "લાઇવ વિસંગતિ સંકેત",
    anomalySignals: "લાઇવ વિસંગતિ સંકેત",
  },
};
