// Mirrors the Docker/nginx serving model: static SPA from dist/ with /api and
// /thumbnails proxied to the backend, and SPA fallback to index.html.
import http from "http";
import { readFile } from "fs/promises";
import { existsSync, statSync } from "fs";
import { extname, join, resolve } from "path";
import { fileURLToPath } from "url";
import { dirname } from "path";

const __dirname = dirname(fileURLToPath(import.meta.url));
const DIST = resolve(__dirname, "../dist");
const BACKEND = "http://localhost:8000";
const PORT = 4173;

const MIME = {
  ".html": "text/html", ".js": "text/javascript", ".css": "text/css",
  ".png": "image/png", ".svg": "image/svg+xml", ".json": "application/json",
  ".ico": "image/x-icon", ".map": "application/json",
};

const server = http.createServer(async (req, res) => {
  const url = req.url || "/";
  if (url.startsWith("/api") || url.startsWith("/thumbnails")) {
    const proxyReq = http.request(BACKEND + url, {
      method: req.method, headers: { ...req.headers, host: "localhost:8000" },
    }, (pr) => { res.writeHead(pr.statusCode || 502, pr.headers); pr.pipe(res); });
    proxyReq.on("error", () => { res.writeHead(502); res.end("proxy error"); });
    req.pipe(proxyReq);
    return;
  }
  let filePath = join(DIST, decodeURIComponent(url.split("?")[0]));
  if (!existsSync(filePath) || statSync(filePath).isDirectory()) {
    filePath = join(DIST, "index.html"); // SPA fallback
  }
  try {
    const body = await readFile(filePath);
    res.writeHead(200, { "content-type": MIME[extname(filePath)] || "application/octet-stream" });
    res.end(body);
  } catch {
    res.writeHead(404); res.end("not found");
  }
});

server.listen(PORT, () => console.log(`dist served on http://localhost:${PORT}`));
