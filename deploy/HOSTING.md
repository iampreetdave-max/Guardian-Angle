# VisionScan — Hosting Guide

Two complementary deployments:

1. **Hugging Face Spaces** — a permanent public link for the submission & judges.
2. **Local + Cloudflare Tunnel** — your demo-day primary: full hardware, fastest,
   shows the offline field-deployment story.

> The hosted Space runs the **core stack** (CLIP + YOLOv8 + FAISS → text /
> reference-image / object search) for fast, reliable cold starts on the free
> CPU tier. **Face matching (ArcFace)** runs in the local/Docker deployment.

---

## 1) Hugging Face Spaces (free, permanent link)

**One-time setup**
1. Create a free account at <https://huggingface.co>.
2. **New → Space**. Choose:
   - **SDK: Docker**  → **Blank**
   - **Hardware: CPU basic** (free, 16 GB RAM / 2 vCPU)
3. The Space is a git repo. The root `Dockerfile` (already in this project) and
   the YAML front-matter at the top of `README.md` make it Spaces-ready.

**Push the project to the Space**
```bash
# from the VisionScan project root
git init                          # if not already a repo
git add .
git commit -m "VisionScan"
# add your Space as a remote (replace USER/SPACE)
git remote add space https://huggingface.co/spaces/USER/SPACE
git push space main               # or: git push space HEAD:main
```
HF builds the Dockerfile and serves on port 7860. First build downloads the
CLIP + YOLO weights (a few minutes); subsequent loads are fast. The Space sleeps
when idle and wakes on the next visit.

**Notes**
- Storage is ephemeral on the free tier — uploaded footage / indexes reset when
  the Space restarts. Perfect for a try-it demo; for persistence add HF
  persistent storage (paid) and point `VISIONSCAN_DATA_DIR` at `/data`.
- Keep demo clips short (≈10–60 s) so CPU processing stays snappy.

---

## 2) Local + Cloudflare Tunnel (demo-day primary)

Run on your own laptop (fastest, face-matching enabled, no cold start), then
expose a temporary public `https://<name>.trycloudflare.com` URL. **No
Cloudflare account or domain required.**

```bash
# 1. start the full stack (UI on http://localhost:8080)
docker compose up --build

# 2. in another terminal, open the public tunnel
#    Windows:
./deploy/tunnel.ps1
#    macOS / Linux:
./deploy/tunnel.sh
```
Share the printed `https://….trycloudflare.com` link. Closing the tunnel
process revokes the URL.

> Running locally **without** Docker? Start the backend (`uvicorn app.main:app
> --port 8000`) and `npm run dev` (UI on :5173), then `./deploy/tunnel.ps1 5173`.

---

## Which to use when
| Situation | Use |
|---|---|
| Submission / "click this link" for judges | Hugging Face Spaces |
| Live demo on stage | Local Docker + Cloudflare Tunnel |
| No internet at venue | Local Docker only (the offline story — open `http://localhost:8080`) |
