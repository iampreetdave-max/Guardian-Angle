import axios from "axios";

// Same-origin: Vite proxies /api -> backend in dev; in Docker they share origin.
const api = axios.create({ baseURL: "/api" });

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
