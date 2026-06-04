// Module-local API helpers for GovIntel's polish features (insights + saved
// searches). The existing search/bookmark/subscription calls live in src/api.js
// and are reused as-is; these NEW endpoints are kept here so the GovIntel module
// owns its own surface without editing the shared api.js.
//
// Reuses the same axios instance (baseURL "/api", bearer-token interceptor) that
// api.js configures, so auth and the 401-bounce behaviour are identical.
import axios from "axios";

const TOKEN_KEY = "cityshield_token";
const gov = axios.create({ baseURL: "/api" });
gov.interceptors.request.use((config) => {
  const t = localStorage.getItem(TOKEN_KEY);
  if (t) config.headers.Authorization = `Bearer ${t}`;
  return config;
});

// Trending / insights strip: counts by type & jurisdiction, most-bookmarked,
// latest-fetched timestamp, per-feed source health.
export const govInsights = () => gov.get("/gov/insights").then((r) => r.data);

// Saved searches (query + advanced filters + optional alert flag).
export const govSavedSearches = () =>
  gov.get("/gov/saved-searches").then((r) => r.data);
export const govAddSavedSearch = (payload) =>
  gov.post("/gov/saved-searches", payload).then((r) => r.data);
export const govRunSavedSearch = (id) =>
  gov.post(`/gov/saved-searches/${id}/run`).then((r) => r.data);
export const govRemoveSavedSearch = (id) =>
  gov.delete(`/gov/saved-searches/${id}`).then((r) => r.data);
