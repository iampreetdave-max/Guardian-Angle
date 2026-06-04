import axios from "axios";

// Same-origin: Vite proxies /api -> backend in dev; in Docker they share origin.
const api = axios.create({ baseURL: "/api" });

// ---- auth token injection ----
const TOKEN_KEY = "cityshield_token";
export const getToken = () => localStorage.getItem(TOKEN_KEY);
export const setToken = (t) =>
  t ? localStorage.setItem(TOKEN_KEY, t) : localStorage.removeItem(TOKEN_KEY);

api.interceptors.request.use((config) => {
  const t = getToken();
  if (t) config.headers.Authorization = `Bearer ${t}`;
  return config;
});

// If the server starts rejecting our token (expired, or VISIONSCAN_REQUIRE_AUTH
// was switched on), drop it and bounce back to the login screen — but not for the
// login call itself, where a 401 just means wrong credentials.
api.interceptors.response.use(
  (r) => r,
  (err) => {
    const url = err?.config?.url || "";
    const isLogin = url.includes("/auth/login");
    if (err?.response?.status === 401 && getToken() && !isLogin) {
      setToken(null);
      window.location.reload();
    }
    return Promise.reject(err);
  }
);

// ---- auth / platform ----
export const authRegister = (p) => api.post("/auth/register", p).then((r) => r.data);
export const authLogin = (p) => api.post("/auth/login", p).then((r) => r.data);
export const authMe = () => api.get("/auth/me").then((r) => r.data);
export const authLogout = () => api.post("/auth/logout").then((r) => r.data);
export const changePassword = (p) =>
  api.post("/auth/change-password", p).then((r) => r.data);
export const forgotPassword = (p) =>
  api.post("/auth/forgot-password", p).then((r) => r.data);
export const resetPassword = (p) =>
  api.post("/auth/reset-password", p).then((r) => r.data);

export const listComplaints = () => api.get("/complaints").then((r) => r.data);
export const fileComplaint = (p) => api.post("/complaints", p).then((r) => r.data);
export const triageComplaint = (id, p) =>
  api.post(`/complaints/${id}/triage`, p).then((r) => r.data);
// NCRP/1930 cybercrime fraud taxonomy for the structured intake form.
export const getCyberCategories = () =>
  api.get("/complaints/cyber/categories").then((r) => r.data);

export const listCases = (statusFilter) =>
  api.get("/cases", { params: statusFilter ? { status_filter: statusFilter } : {} }).then((r) => r.data);
export const createCase = (p) => api.post("/cases", p).then((r) => r.data);
export const getCase = (id) => api.get(`/cases/${id}`).then((r) => r.data);
export const assignCase = (id, p) => api.post(`/cases/${id}/assign`, p).then((r) => r.data);
export const listEvidence = (id) => api.get(`/cases/${id}/evidence`).then((r) => r.data);
export const addEvidence = (id, p) => api.post(`/cases/${id}/evidence`, p).then((r) => r.data);
export const listDocuments = (id) => api.get(`/cases/${id}/documents`).then((r) => r.data);
export const addDocument = (id, p) => api.post(`/cases/${id}/documents`, p).then((r) => r.data);
export const listMessages = (id) => api.get(`/cases/${id}/messages`).then((r) => r.data);
export const postMessage = (id, p) => api.post(`/cases/${id}/messages`, p).then((r) => r.data);
export const setCitizenVisibility = (id, p) =>
  api.post(`/cases/${id}/citizen-visibility`, p).then((r) => r.data);
export const closeCase = (id, p) => api.post(`/cases/${id}/close`, p).then((r) => r.data);
export const rateCase = (id, p) => api.post(`/cases/${id}/rate`, p).then((r) => r.data);
export const caseTimeline = (id) => api.get(`/cases/${id}/timeline`).then((r) => r.data);

export const listMeetings = (id) => api.get(`/cases/${id}/meetings`).then((r) => r.data);
export const createMeeting = (id, p) =>
  api.post(`/cases/${id}/meetings`, p).then((r) => r.data);
export const cancelMeeting = (id, mid) =>
  api.delete(`/cases/${id}/meetings/${mid}`).then((r) => r.data);

export const listUsers = () => api.get("/users").then((r) => r.data);
export const createUser = (p) => api.post("/users", p).then((r) => r.data);
export const updateUser = (id, p) => api.patch(`/users/${id}`, p).then((r) => r.data);
export const listTeams = () => api.get("/teams").then((r) => r.data);
export const createTeam = (p) => api.post("/teams", p).then((r) => r.data);
export const listTeamMembers = (id) =>
  api.get(`/teams/${id}/members`).then((r) => r.data);

export const getNotifications = () => api.get("/notifications").then((r) => r.data);
export const markNotificationsRead = () =>
  api.post("/notifications/read-all").then((r) => r.data);

export const getHealth = () => api.get("/health").then((r) => r.data);

// ---- anomaly watch (always-on CCTV incident alerts) ----
export const listAnomalies = (params = {}) =>
  api.get("/anomalies", { params }).then((r) => r.data);
export const anomalySummary = () =>
  api.get("/anomalies/summary").then((r) => r.data);
export const ackAnomaly = (id) =>
  api.post(`/anomalies/${id}/ack`).then((r) => r.data);
export const dismissAnomaly = (id) =>
  api.post(`/anomalies/${id}/dismiss`).then((r) => r.data);

export const getAnalytics = () => api.get("/analytics/summary").then((r) => r.data);

// ---- city map + broadcasts ----
export const getAreas = () => api.get("/analytics/areas").then((r) => r.data);
export const getMapData = (params = {}) =>
  api.get("/analytics/map", { params }).then((r) => r.data);
// Cyber-fraud victim-location density (₹ lost + fraud-channel mix per area).
export const getCyberMapData = (params = {}) =>
  api.get("/analytics/map/cyber", { params }).then((r) => r.data);

// ---- predictive policing ----
export const getRiskScores = () => api.get("/predict/risk").then((r) => r.data);
// Backtested accuracy (rolling-origin CV). compare=true also returns the
// baseline comparison table + surge detection; officer-gated, cached ~10 min.
export const getValidation = (params = { compare: true }) =>
  api.get("/predict/validation", { params }).then((r) => r.data);
export const getTemporal = (params = {}) =>
  api.get("/predict/temporal", { params }).then((r) => r.data);
export const getPatrolRoutes = (params = {}) =>
  api.get("/predict/patrol-routes", { params }).then((r) => r.data);
export const addPatrolLog = (p) =>
  api.post("/predict/patrol-logs", p).then((r) => r.data);
export const listPatrolLogs = (params = {}) =>
  api.get("/predict/patrol-logs", { params }).then((r) => r.data);
export const sendBroadcast = (p) =>
  api.post("/notifications/broadcast", p).then((r) => r.data);
export const getActiveBroadcasts = () =>
  api.get("/notifications/broadcasts/active").then((r) => r.data);
export const listBroadcasts = () =>
  api.get("/notifications/broadcasts").then((r) => r.data);
export const deactivateBroadcast = (id) =>
  api.post(`/notifications/broadcasts/${id}/deactivate`).then((r) => r.data);

export const listVideos = () => api.get("/videos").then((r) => r.data);

export const uploadVideo = (file, cameraId, onProgress) => {
  const form = new FormData();
  form.append("file", file);
  form.append("camera_id", cameraId);
  return api
    .post("/videos", form, {
      onUploadProgress: (e) =>
        onProgress && onProgress(Math.round((e.loaded * 100) / (e.total || 1))),
    })
    .then((r) => r.data);
};

export const getFeeds = () => api.get("/feeds").then((r) => r.data);

export const ingestStream = (payload) =>
  api.post("/streams", payload).then((r) => r.data);

export const startLive = (payload) =>
  api.post("/streams/live", payload).then((r) => r.data);

export const stopLive = (id) =>
  api.post(`/videos/${id}/stop`).then((r) => r.data);

export const deleteVideo = (id) =>
  api.delete(`/videos/${id}`).then((r) => r.data);

export const searchText = (payload) =>
  api.post("/search/text", payload).then((r) => r.data);

export const searchObject = (payload) =>
  api.post("/search/object", payload).then((r) => r.data);

export const searchRegion = (payload) =>
  api.post("/search/region", payload).then((r) => r.data);

export const reindexObjects = () => api.post("/reindex").then((r) => r.data);

const searchWithImage = (endpoint, file, { top_k, camera_id, video_id, group_events }) => {
  const form = new FormData();
  form.append("file", file);
  form.append("top_k", top_k ?? 30);
  if (camera_id) form.append("camera_id", camera_id);
  if (video_id) form.append("video_id", video_id);
  if (group_events !== undefined) form.append("group_events", group_events);
  return api.post(endpoint, form).then((r) => r.data);
};

export const searchImage = (file, opts = {}) =>
  searchWithImage("/search/image", file, opts);

export const searchFace = (file, opts = {}) =>
  searchWithImage("/search/face", file, opts);

export const generateReport = (payload) =>
  api
    .post("/report", payload, { responseType: "blob" })
    .then((r) => r.data);

// ---- admin system / security / monitoring / data ----
export const getSystemStatus = () => api.get("/admin/system").then((r) => r.data);
export const setLockdown = (enabled) =>
  api.post("/admin/lockdown", { enabled }).then((r) => r.data);
export const getSecurityEvents = () =>
  api.get("/admin/security-events").then((r) => r.data);
export const logoutAll = () => api.post("/auth/logout-all").then((r) => r.data);

// URL of an export endpoint (relative to the /api base). The component fetches
// it as a blob (auth header applied by the axios interceptor) and triggers an
// anchor download — same responseType: "blob" pattern as generateReport.
export const downloadExport = (kind) => `/admin/export/${kind}`;
export const fetchExportBlob = (kind) =>
  api.get(downloadExport(kind), { responseType: "blob" }).then((r) => r.data);

// ---- GovIntel (Unified Legal & Government Intelligence) ----
export const govHealth = () => api.get("/gov/health").then((r) => r.data);
export const govSearch = (params) =>
  api.get("/gov/search", { params }).then((r) => r.data);
export const govDocument = (id) => api.get(`/gov/document/${id}`).then((r) => r.data);
export const govRelated = (id) =>
  api.get(`/gov/document/${id}/related`).then((r) => r.data);
export const govSummarize = (payload) =>
  api.post("/gov/summarize", payload).then((r) => r.data);
export const govSuggest = (q) =>
  api.get("/gov/suggest", { params: { q } }).then((r) => r.data);
export const govTrending = () => api.get("/gov/trending").then((r) => r.data);
export const govDepartments = () => api.get("/gov/departments").then((r) => r.data);
export const govBookmarks = () => api.get("/gov/bookmarks").then((r) => r.data);
export const govAddBookmark = (doc_id) =>
  api.post("/gov/bookmarks", { doc_id }).then((r) => r.data);
export const govRemoveBookmark = (doc_id) =>
  api.delete(`/gov/bookmarks/${doc_id}`).then((r) => r.data);
export const govSubscriptions = () =>
  api.get("/gov/subscriptions").then((r) => r.data);
export const govAddSubscription = (payload) =>
  api.post("/gov/subscriptions", payload).then((r) => r.data);
export const govRemoveSubscription = (id) =>
  api.delete(`/gov/subscriptions/${id}`).then((r) => r.data);
export const govRefresh = () => api.post("/gov/refresh").then((r) => r.data);

// ---- CrimeGPT (AI crime documentation automation) ----
export const crimegptHealth = () => api.get("/crimegpt/health").then((r) => r.data);
export const crimegptSuggestSections = (payload) =>
  api.post("/crimegpt/suggest-sections", payload).then((r) => r.data);
export const crimegptLegalCatalogue = () =>
  api.get("/crimegpt/legal/catalogue").then((r) => r.data);

export const crimegptGetPool = (caseId) =>
  api.get(`/crimegpt/cases/${caseId}/pool`).then((r) => r.data);
export const crimegptAddParty = (caseId, p) =>
  api.post(`/crimegpt/cases/${caseId}/parties`, p).then((r) => r.data);
export const crimegptUpdateParty = (caseId, partyId, p) =>
  api.patch(`/crimegpt/cases/${caseId}/parties/${partyId}`, p).then((r) => r.data);
export const crimegptDeleteParty = (caseId, partyId) =>
  api.delete(`/crimegpt/cases/${caseId}/parties/${partyId}`).then((r) => r.data);
export const crimegptAddSeizure = (caseId, p) =>
  api.post(`/crimegpt/cases/${caseId}/seizures`, p).then((r) => r.data);
export const crimegptDeleteSeizure = (caseId, seizureId) =>
  api.delete(`/crimegpt/cases/${caseId}/seizures/${seizureId}`).then((r) => r.data);
export const crimegptAddStatement = (caseId, p) =>
  api.post(`/crimegpt/cases/${caseId}/statements`, p).then((r) => r.data);
export const crimegptDeleteStatement = (caseId, statementId) =>
  api.delete(`/crimegpt/cases/${caseId}/statements/${statementId}`).then((r) => r.data);

export const crimegptDiary = (caseId) =>
  api.get(`/crimegpt/cases/${caseId}/diary`).then((r) => r.data);
export const crimegptAddDiary = (caseId, p) =>
  api.post(`/crimegpt/cases/${caseId}/diary`, p).then((r) => r.data);

export const crimegptDocuments = (caseId) =>
  api.get(`/crimegpt/cases/${caseId}/documents`).then((r) => r.data);
// Generate a document; returns the PDF as a blob (auth header applied by the
// axios interceptor) plus the version from the response headers.
export const crimegptGenerateDocument = (caseId, docType, language = "en") =>
  api
    .post(`/crimegpt/cases/${caseId}/documents/${docType}`, null, {
      params: { language },
      responseType: "blob",
    })
    .then((r) => ({
      blob: r.data,
      version: r.headers["x-document-version"],
      docType: r.headers["x-document-type"] || docType,
    }));

// ---- Arbiter (legal intelligence) ----
export const legalHealth = () => api.get("/legal/health").then((r) => r.data);
export const legalSections = (payload) =>
  api.post("/legal/sections", payload).then((r) => r.data);
export const legalFir = (payload) =>
  api.post("/legal/fir", payload).then((r) => r.data);
export const legalQuery = (payload) =>
  api.post("/legal/query", payload).then((r) => r.data);

export default api;
