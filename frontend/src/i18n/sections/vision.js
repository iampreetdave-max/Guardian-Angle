/* VisionScan video-search workspace: search modes, camera feeds, result cards,
   frame detail, report tray, live player.

   Note on search placeholders: CLIP and the YOLO label vocabulary are
   English-only — there is no query translation on the backend — so the EXAMPLE
   queries stay in English in every language and the surrounding hint tells the
   officer to type in English. Translating the examples would silently break
   search. */
export default {
  en: {
    // search modes
    modeText: "Text",
    modeObject: "Object",
    modeImage: "Reference Image",
    modeFace: "Suspect Face",
    phText: 'e.g. "person in red jacket near the gate"',
    phObject: "e.g. car, person, truck, motorcycle",
    faceUnavailable: "ArcFace model not available",
    uploadWhat: "Upload {what}",
    faceHint: "Match this person across all footage (ArcFace)",
    imageHint: "Find frames that look like this image (CLIP)",
    refAlt: "reference image",

    // region-search nudge + toggles
    nudgeLead: "Searching for a specific object? Whole-frame text match is fuzzy —",
    findEveryObject: "Find every object",
    nudgeTail: "scores each detected object for precise matches.",
    perObjectTitle:
      "Match individual detected objects instead of whole frames — finds EVERY instance (e.g. all 5 red cars), each with its own box.",
    perObjectOn: "Find every object: ON",
    perObjectOff: "Find every object: OFF",
    groupTitle:
      "When on, frames from the same camera within a few seconds are collapsed into one event. Turn off to see every matching frame.",
    groupOn: "Grouping moments: ON",
    groupOff: "Grouping moments: OFF",
    hintPerObject: "instance search — every matching object, with its box",
    hintGroup: "collapses near-duplicate frames into events",
    hintAll: "shows every matching frame",

    // camera feeds / ingest
    cameraFeeds: "Camera Feeds",
    reindex: "Re-index",
    reindexTitle:
      "Re-process existing footage to enable 'Find every object' instance search on it",
    upload: "Upload",
    liveFeed: "Live Feed",
    cameraIdPh: "Camera ID (e.g. CAM-Gate-1)",
    uploadFootage: "Upload Footage",
    streamUrlPh: "Public stream URL (RTSP / HLS / YouTube-live)",
    goLive: "Go Live (watch & search)",
    captureOnce: "Capture once",
    captureOnceTitle: "Capture a fixed window then stop",
    sec: "sec",
    legalNotice:
      "Use only intentionally-public feeds (govt traffic cams, public live streams). Accessing private/unsecured cameras without authorization is illegal.",
    publicFeeds: "Public feeds — click to go live",
    noFootage: "No footage yet. Upload CCTV video to begin.",
    keyframes: "{n} keyframes",
    deleteFeed: "Delete feed",

    // result cards / frame detail
    frameAlt: "frame {id}",
    addToReport: "Add to report",
    inReport: "In report",
    addAllToReport: "Add all to report",
    allInReport: "All in report",
    eventFramesTitle: "{n} frames in this event ({start}–{end})",
    match: "match",
    instances: "{n} instances",
    eventGalleryHint:
      "All {n} frames in this event — click to view, check to add to report",
    frameNo: "frame #{id}",

    // report tray
    framesSelected: "frames selected",
    generateReport: "Generate Report",
    forensicPdf: "Forensic PDF Report",
    linkCase: "Link to one of your cases",
    optional: "(optional)",
    noneOption: "— none —",
    caseTitle: "Case title",
    investigator: "Investigator",
    investigatorPh: "Officer name / ID",
    reportSummary: "{n} timestamped frames · query:",
    downloadPdf: "Download PDF",

    // live player
    indexingLive: "indexing in real time · {n} frames captured",
    showPreview: "Show preview",
    hidePreview: "Hide preview (keeps indexing)",
    show: "Show",
    hide: "Hide",
    stop: "Stop",
    previewUnsupported:
      "This feed can't preview in-browser, but it's being captured and indexed live — search results below update in real time.",
    playbackFailed:
      "Live preview unavailable (the stream blocked playback), but capture + indexing continue on the server.",

    // results header (rendered from App.jsx — keys live here with the rest of
    // the vision workspace)
    searchFailed: "Search failed. Is the footage processed?",
    draftFir: "Draft FIR in Arbiter",
    draftFirTitle: "Send this evidence to Arbiter to draft an FIR",
    nudgeNone: "No strong text matches.",
    nudgeFew: "Few text matches.",
    emptyReady: "Search your footage by natural language, object, reference image, or suspect face.",
    emptyUpload: "Upload CCTV footage, or open the Live Feed tab on the left to load a public feed in one click. Processing runs automatically.",
    scanning: "Scanning footage…",
    matchesFor: "matches for",
    clipFallback:
      "not an exact object label — showing per-object visual matches (CLIP) instead",
  },

  hi: {
    modeText: "टेक्स्ट",
    modeObject: "वस्तु",
    modeImage: "संदर्भ छवि",
    modeFace: "संदिग्ध चेहरा",
    phText: 'अंग्रेज़ी में लिखें, जैसे "person in red jacket near the gate"',
    phObject: "अंग्रेज़ी में लिखें, जैसे car, person, truck",
    faceUnavailable: "ArcFace मॉडल उपलब्ध नहीं",
    uploadWhat: "{what} अपलोड करें",
    faceHint: "इस व्यक्ति को सभी फुटेज में मिलाएँ (ArcFace)",
    imageHint: "इस छवि जैसे फ़्रेम खोजें (CLIP)",
    refAlt: "संदर्भ छवि",

    nudgeLead: "कोई खास वस्तु ढूँढ रहे हैं? पूरे फ़्रेम का टेक्स्ट मिलान अस्पष्ट होता है —",
    findEveryObject: "हर वस्तु खोजें",
    nudgeTail: "प्रत्येक पहचानी गई वस्तु को अलग जाँचकर सटीक मिलान देता है।",
    perObjectTitle:
      "पूरे फ़्रेम के बजाय अलग-अलग पहचानी गई वस्तुओं का मिलान — हर उदाहरण मिलेगा (जैसे सभी 5 लाल कारें), हर एक अपने बॉक्स के साथ।",
    perObjectOn: "हर वस्तु खोजें: चालू",
    perObjectOff: "हर वस्तु खोजें: बंद",
    groupTitle:
      "चालू होने पर एक ही कैमरे के कुछ सेकंड के भीतर के फ़्रेम एक घटना में जोड़ दिए जाते हैं। हर मिलान फ़्रेम देखने के लिए बंद करें।",
    groupOn: "समूहन: चालू",
    groupOff: "समूहन: बंद",
    hintPerObject: "इंस्टेंस खोज — हर मिलती वस्तु, अपने बॉक्स के साथ",
    hintGroup: "लगभग एक जैसे फ़्रेम को घटनाओं में जोड़ता है",
    hintAll: "हर मिलान फ़्रेम दिखाता है",

    cameraFeeds: "कैमरा फ़ीड",
    reindex: "पुनः इंडेक्स",
    reindexTitle:
      "मौजूदा फुटेज पर 'हर वस्तु खोजें' चलाने के लिए उसे दोबारा प्रोसेस करें",
    upload: "अपलोड",
    liveFeed: "लाइव फ़ीड",
    cameraIdPh: "कैमरा ID (जैसे CAM-Gate-1)",
    uploadFootage: "फुटेज अपलोड करें",
    streamUrlPh: "सार्वजनिक स्ट्रीम URL (RTSP / HLS / YouTube-live)",
    goLive: "लाइव करें (देखें और खोजें)",
    captureOnce: "एक बार कैप्चर",
    captureOnceTitle: "तय अवधि तक कैप्चर करके रुक जाएँ",
    sec: "सेकंड",
    legalNotice:
      "केवल जानबूझकर सार्वजनिक की गई फ़ीड ही उपयोग करें (सरकारी ट्रैफ़िक कैमरे, सार्वजनिक लाइव स्ट्रीम)। बिना अनुमति निजी/असुरक्षित कैमरों तक पहुँचना गैरकानूनी है।",
    publicFeeds: "सार्वजनिक फ़ीड — लाइव करने के लिए क्लिक करें",
    noFootage: "अभी कोई फुटेज नहीं। शुरू करने के लिए CCTV वीडियो अपलोड करें।",
    keyframes: "{n} कीफ़्रेम",
    deleteFeed: "फ़ीड हटाएँ",

    frameAlt: "फ़्रेम {id}",
    addToReport: "रिपोर्ट में जोड़ें",
    inReport: "रिपोर्ट में है",
    addAllToReport: "सभी रिपोर्ट में जोड़ें",
    allInReport: "सभी रिपोर्ट में",
    eventFramesTitle: "इस घटना में {n} फ़्रेम ({start}–{end})",
    match: "मिलान",
    instances: "{n} फ़्रेम",
    eventGalleryHint:
      "इस घटना के सभी {n} फ़्रेम — देखने के लिए क्लिक करें, रिपोर्ट में जोड़ने के लिए टिक करें",
    frameNo: "फ़्रेम #{id}",

    framesSelected: "फ़्रेम चयनित",
    generateReport: "रिपोर्ट बनाएँ",
    forensicPdf: "फ़ॉरेंसिक PDF रिपोर्ट",
    linkCase: "अपने किसी केस से जोड़ें",
    optional: "(वैकल्पिक)",
    noneOption: "— कोई नहीं —",
    caseTitle: "केस शीर्षक",
    investigator: "जाँच अधिकारी",
    investigatorPh: "अधिकारी का नाम / ID",
    reportSummary: "{n} टाइमस्टैम्प वाले फ़्रेम · खोज:",
    downloadPdf: "PDF डाउनलोड करें",

    indexingLive: "रीयल टाइम में इंडेक्स हो रहा है · {n} फ़्रेम कैप्चर",
    showPreview: "प्रीव्यू दिखाएँ",
    hidePreview: "प्रीव्यू छिपाएँ (इंडेक्सिंग चालू रहेगी)",
    show: "दिखाएँ",
    hide: "छिपाएँ",
    stop: "रोकें",
    previewUnsupported:
      "यह फ़ीड ब्राउज़र में नहीं चल सकती, पर इसे लाइव कैप्चर व इंडेक्स किया जा रहा है — नीचे के परिणाम रीयल टाइम में अपडेट होंगे।",
    playbackFailed:
      "लाइव प्रीव्यू उपलब्ध नहीं (स्ट्रीम ने प्लेबैक रोक दिया), पर सर्वर पर कैप्चर व इंडेक्सिंग जारी है।",

    searchFailed: "खोज विफल। क्या फुटेज संसाधित है?",
    draftFir: "आर्बिटर में FIR बनाएँ",
    draftFirTitle: "FIR का प्रारूप बनाने के लिए यह साक्ष्य आर्बिटर को भेजें",
    nudgeNone: "कोई सटीक टेक्स्ट मिलान नहीं।",
    nudgeFew: "कम टेक्स्ट मिलान।",
    emptyReady: "प्राकृतिक भाषा, वस्तु, संदर्भ छवि या संदिग्ध चेहरे से फुटेज खोजें।",
    emptyUpload: "CCTV फुटेज अपलोड करें, या बाईं ओर लाइव फ़ीड टैब खोलकर एक क्लिक में सार्वजनिक फ़ीड लोड करें। प्रोसेसिंग स्वतः चलती है।",
    scanning: "फुटेज स्कैन हो रही है…",
    matchesFor: "मिलान —",
    clipFallback:
      "यह सटीक ऑब्जेक्ट लेबल नहीं है — इसके बजाय प्रति-वस्तु दृश्य मिलान (CLIP) दिखाए जा रहे हैं",
  },

  gu: {
    modeText: "ટેક્સ્ટ",
    modeObject: "વસ્તુ",
    modeImage: "સંદર્ભ છબી",
    modeFace: "શંકાસ્પદ ચહેરો",
    phText: 'અંગ્રેજીમાં લખો, દા.ત. "person in red jacket near the gate"',
    phObject: "અંગ્રેજીમાં લખો, દા.ત. car, person, truck",
    faceUnavailable: "ArcFace મોડેલ ઉપલબ્ધ નથી",
    uploadWhat: "{what} અપલોડ કરો",
    faceHint: "આ વ્યક્તિને તમામ ફૂટેજમાં મેળવો (ArcFace)",
    imageHint: "આ છબી જેવા ફ્રેમ શોધો (CLIP)",
    refAlt: "સંદર્ભ છબી",

    nudgeLead: "કોઈ ચોક્કસ વસ્તુ શોધો છો? આખા ફ્રેમનું ટેક્સ્ટ મેચિંગ અસ્પષ્ટ છે —",
    findEveryObject: "દરેક વસ્તુ શોધો",
    nudgeTail: "દરેક ઓળખાયેલ વસ્તુને અલગ તપાસી ચોક્કસ મેચ આપે છે.",
    perObjectTitle:
      "આખા ફ્રેમને બદલે અલગ-અલગ ઓળખાયેલ વસ્તુઓનું મેચિંગ — દરેક ઉદાહરણ મળશે (દા.ત. બધી 5 લાલ કાર), દરેક પોતાના બોક્સ સાથે.",
    perObjectOn: "દરેક વસ્તુ શોધો: ચાલુ",
    perObjectOff: "દરેક વસ્તુ શોધો: બંધ",
    groupTitle:
      "ચાલુ હોય ત્યારે એક જ કૅમેરાના થોડી સેકન્ડમાંના ફ્રેમ એક ઘટનામાં જોડાય છે. દરેક મેચિંગ ફ્રેમ જોવા બંધ કરો.",
    groupOn: "જૂથબદ્ધ: ચાલુ",
    groupOff: "જૂથબદ્ધ: બંધ",
    hintPerObject: "ઇન્સ્ટન્સ શોધ — દરેક મેચ થતી વસ્તુ, તેના બોક્સ સાથે",
    hintGroup: "લગભગ સરખા ફ્રેમને ઘટનાઓમાં જોડે છે",
    hintAll: "દરેક મેચિંગ ફ્રેમ બતાવે છે",

    cameraFeeds: "કૅમેરા ફીડ",
    reindex: "ફરી ઇન્ડેક્સ",
    reindexTitle:
      "હાલના ફૂટેજ પર 'દરેક વસ્તુ શોધો' ચલાવવા તેને ફરી પ્રોસેસ કરો",
    upload: "અપલોડ",
    liveFeed: "લાઇવ ફીડ",
    cameraIdPh: "કૅમેરા ID (દા.ત. CAM-Gate-1)",
    uploadFootage: "ફૂટેજ અપલોડ કરો",
    streamUrlPh: "સાર્વજનિક સ્ટ્રીમ URL (RTSP / HLS / YouTube-live)",
    goLive: "લાઇવ કરો (જુઓ અને શોધો)",
    captureOnce: "એક વાર કૅપ્ચર",
    captureOnceTitle: "નિશ્ચિત સમય કૅપ્ચર કરી બંધ કરો",
    sec: "સેકન્ડ",
    legalNotice:
      "ફક્ત જાણીજોઈને સાર્વજનિક કરાયેલ ફીડ જ વાપરો (સરકારી ટ્રાફિક કૅમેરા, સાર્વજનિક લાઇવ સ્ટ્રીમ). પરવાનગી વગર ખાનગી/અસુરક્ષિત કૅમેરા વાપરવા ગેરકાયદેસર છે.",
    publicFeeds: "સાર્વજનિક ફીડ — લાઇવ કરવા ક્લિક કરો",
    noFootage: "હજુ કોઈ ફૂટેજ નથી. શરૂ કરવા CCTV વિડિયો અપલોડ કરો.",
    keyframes: "{n} કીફ્રેમ",
    deleteFeed: "ફીડ કાઢી નાખો",

    frameAlt: "ફ્રેમ {id}",
    addToReport: "રિપોર્ટમાં ઉમેરો",
    inReport: "રિપોર્ટમાં છે",
    addAllToReport: "બધા રિપોર્ટમાં ઉમેરો",
    allInReport: "બધા રિપોર્ટમાં",
    eventFramesTitle: "આ ઘટનામાં {n} ફ્રેમ ({start}–{end})",
    match: "મેચ",
    instances: "{n} ફ્રેમ",
    eventGalleryHint:
      "આ ઘટનાના બધા {n} ફ્રેમ — જોવા ક્લિક કરો, રિપોર્ટમાં ઉમેરવા ટિક કરો",
    frameNo: "ફ્રેમ #{id}",

    framesSelected: "ફ્રેમ પસંદ કરેલ",
    generateReport: "રિપોર્ટ બનાવો",
    forensicPdf: "ફોરેન્સિક PDF રિપોર્ટ",
    linkCase: "તમારા કોઈ કેસ સાથે જોડો",
    optional: "(વૈકલ્પિક)",
    noneOption: "— કોઈ નહીં —",
    caseTitle: "કેસ શીર્ષક",
    investigator: "તપાસ અધિકારી",
    investigatorPh: "અધિકારીનું નામ / ID",
    reportSummary: "{n} ટાઇમસ્ટૅમ્પ સાથેના ફ્રેમ · શોધ:",
    downloadPdf: "PDF ડાઉનલોડ કરો",

    indexingLive: "રિયલ ટાઇમમાં ઇન્ડેક્સ થાય છે · {n} ફ્રેમ કૅપ્ચર",
    showPreview: "પ્રીવ્યૂ બતાવો",
    hidePreview: "પ્રીવ્યૂ છુપાવો (ઇન્ડેક્સિંગ ચાલુ રહેશે)",
    show: "બતાવો",
    hide: "છુપાવો",
    stop: "બંધ કરો",
    previewUnsupported:
      "આ ફીડ બ્રાઉઝરમાં ચાલી શકતી નથી, પણ તે લાઇવ કૅપ્ચર અને ઇન્ડેક્સ થઈ રહી છે — નીચેનાં પરિણામ રિયલ ટાઇમમાં અપડેટ થશે.",
    playbackFailed:
      "લાઇવ પ્રીવ્યૂ ઉપલબ્ધ નથી (સ્ટ્રીમે પ્લેબૅક રોક્યું), પણ સર્વર પર કૅપ્ચર અને ઇન્ડેક્સિંગ ચાલુ છે.",

    searchFailed: "શોધ નિષ્ફળ. શું ફૂટેજ પ્રોસેસ થયું છે?",
    draftFir: "આર્બિટરમાં FIR બનાવો",
    draftFirTitle: "FIR નો મુસદ્દો બનાવવા આ પુરાવો આર્બિટરને મોકલો",
    nudgeNone: "કોઈ મજબૂત ટેક્સ્ટ મેચ નથી.",
    nudgeFew: "થોડા ટેક્સ્ટ મેચ.",
    emptyReady: "કુદરતી ભાષા, વસ્તુ, સંદર્ભ છબી અથવા શંકાસ્પદ ચહેરાથી ફૂટેજ શોધો.",
    emptyUpload: "CCTV ફૂટેજ અપલોડ કરો, અથવા ડાબી બાજુ લાઇવ ફીડ ટૅબ ખોલીને એક ક્લિકમાં જાહેર ફીડ લોડ કરો. પ્રોસેસિંગ આપમેળે ચાલે છે.",
    scanning: "ફૂટેજ સ્કૅન થઈ રહ્યું છે…",
    matchesFor: "મેચ —",
    clipFallback:
      "આ ચોક્કસ ઑબ્જેક્ટ લેબલ નથી — તેના બદલે વસ્તુ-દીઠ દૃશ્ય મેચ (CLIP) બતાવાય છે",
  },
};
