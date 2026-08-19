# Running CityShield in GitHub Codespaces

A hosted demo with **no credit card**. A personal GitHub account includes
120 core-hours and 15 GB storage per month, and if no payment method is on file
GitHub simply **blocks further use at the quota** rather than charging you.

## Start it

1. On the repo: **Code ▸ Codespaces ▸ Create codespace on main**
2. Wait for the first build — **10–15 minutes** (it compiles ArcFace and pulls
   PyTorch). Subsequent starts are seconds.
3. Open the **Ports** tab, find port **8080**, and set **Visibility ▸ Public**.
4. Open the forwarded URL. Sign in as `admin@city.gov` / `admin123`.

> Port 8080 must be **Public**, otherwise the link only works for you and a judge
> clicking it gets a GitHub sign-in page.

## Before you present

- **Raise the idle timeout.** Default is 30 minutes, and a stopped codespace
  means a dead link mid-demo. github.com/settings/codespaces → *Default idle
  timeout* → **240 minutes**.
- **Open the URL ~20 minutes beforehand.** Never let a judge's click be the
  request that wakes it.
- Quota maths: a 4-core machine spends **4 core-hours per wall-clock hour**, so
  the free 120 is about **30 hours** of running time per month. Stop the
  codespace when you are not using it.

## What is there

**Everything.** All 16 test clips arrive pre-indexed.

`deploy/fetch-demo-data.sh` runs on create and restores a published data bundle
(~306 MB) straight into the Docker volume: the 16 videos, 417 keyframes, 3,362
detections with tracking ids, 434 thumbnails, the FAISS indexes and the seeded
SQLite database. That is deliberate — *ingesting* those clips takes 30-60 minutes
of CPU, so the bundle ships the finished index rather than the raw work.

So a fresh codespace can immediately do the full demo, including
`red car` -> CAM-14 with the bounding box, suspect-face re-identification, and
scene analytics.

If the download fails for any reason the script **does not fail the codespace** —
the app still self-seeds complaints, cases, the map and the predictive forecast.
Only video search would be empty, and uploading one clip fixes it.
