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

export const listUsers = () => api.get("/users").then((r) => r.data);
export const createUser = (p) => api.post("/users", p).then((r) => r.data);
export const listTeams = () => api.get("/teams").then((r) => r.data);
export const createTeam = (p) => api.post("/teams", p).then((r) => r.data);

export const getNotifications = () => api.get("/notifications").then((r) => r.data);
export const markNotificationsRead = () =>
  api.post("/notifications/read-all").then((r) => r.data);

export const getHealth = () => api.get("/health").then((r) => r.data);

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

// ---- Arbiter (legal intelligence) ----
export const legalHealth = () => api.get("/legal/health").then((r) => r.data);
export const legalSections = (payload) =>
  api.post("/legal/sections", payload).then((r) => r.data);
export const legalFir = (payload) =>
  api.post("/legal/fir", payload).then((r) => r.data);
export const legalQuery = (payload) =>
  api.post("/legal/query", payload).then((r) => r.data);

export default api;
