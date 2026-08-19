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

## What is and is not there

The synthetic case data seeds itself on first boot, so the **dashboard, City Map,
predictive forecast, patrol routing, Cases, Complaints, Arbiter, CrimeGPT and
Legal Feed all work immediately**.

**Video footage does not ship with the repo** — the 16 test clips are ~282 MB and
are gitignored, and the specialised fire/smoke weights are ~520 MB. So a fresh
codespace starts with **no cameras**, and VisionScan search will be empty until
you upload something.

To demo video search here, upload a clip or two through the VisionScan tab and
wait for processing. Otherwise demo video search on the laptop, where all 16
clips are already indexed.
