# GovIntel — Unified Legal & Government Intelligence

> Problem statement: **PS-69EEFDD4DA6E9** (Legal Feed). The "polish" features that
> complete the statement — advanced filters, the cross-linking engine,
> bookmarks + saved searches, and the trending/insights strip — are documented in
> the [Polish features](#polish-features-ps-69eefdd4da6e9) section below.

A single point of access to **Government Resolutions (GRs), notifications,
circulars, Acts, rules, court judgments and schemes** from Central and Gujarat
sources. Search once, get categorised, cross-linked, summarised results with
direct links to the official source — and subscribe to keyword/category alerts
that arrive in the same in-app notification bell as case updates.

It is a modular add-on (like Arbiter): mounted under `/api/gov/*` and the
**Legal Feed** tab in the UI. It never touches the VisionScan or Arbiter routes.

---

## Design: bundled corpus + free live feeds

There is no free, keyless JSON API for Indian GRs/judgments (Indian Kanoon,
SooperKanoon and data.gov.in all require keys or payment, and the Gujarat GR
portal has no API). GovIntel therefore uses two layers:

1. **Bundled curated corpus** (`backend/app/govintel/corpus/gov_corpus.json`) —
   the always-on, fully-offline backbone. ~25 real documents across every
   category and both jurisdictions, each with an official `source_url`. This is
   what guarantees search/categorisation/summaries work with no network and no
   keys.

2. **Free government RSS/Atom feeds** — the live layer (`sources.py`). These need
   **no API key** and can be polled on a schedule (PIB national + PIB Gujarat,
   RBI notifications/press releases). Each feed is fetched with the Python
   standard library (`urllib` + `xml.etree`, **no new dependency**) using a
   browser User-Agent and a short timeout. Every feed is wrapped in its own
   try/except: a 403, a moved URL or a timeout simply skips that feed — refresh
   never fails and the bundled corpus is never at risk.

### Search modes
- **Semantic** (default) when ChromaDB is installed — the same MiniLM ONNX
  embedder Arbiter uses, fully offline after a one-time model download.
- **Keyword** automatic fallback when ChromaDB isn't present (lightweight/field
  deployments). The module stays fully functional, just lexical instead of
  semantic. `GET /api/gov/health` reports which mode is active.

### AI summaries
Reuse the Arbiter LLM layer: **Gemini** when `VISIONSCAN_GEMINI_API_KEY` is set,
otherwise a deterministic offline extractive summary. Summaries are multilingual
(English / Hindi / Gujarati).

---

## Notifications integration

Users **subscribe** to a keyword, category and/or region. When `refresh()` pulls
a new document that matches a subscription, it inserts a `gov_update` row into
the existing `notifications` table (with the document's `link`), so government
updates surface in the same bell UI as case/complaint alerts. The bell renders a
"source" link for any notification that carries one.

---

## Refresh / hourly polling

- **Manual:** lead/admin users click **Refresh feeds** in the Legal Feed tab, or
  `POST /api/gov/refresh`.
- **Automatic hourly:** set `VISIONSCAN_GOVINTEL_AUTO_REFRESH=true`. A daemon
  thread then calls `refresh()` every hour. Off by default (no surprise network
  calls). A cron job hitting `POST /api/gov/refresh` works equally well.

### Config (all optional, env-prefixed `VISIONSCAN_`)
| Setting | Default | Meaning |
|---|---|---|
| `GOVINTEL_ENABLE` | `true` | allow the live RSS layer |
| `GOVINTEL_FEED_TIMEOUT` | `6` | seconds per feed fetch |
| `GOVINTEL_AUTO_REFRESH` | `false` | opt-in hourly background poll |
| `GEMINI_API_KEY` | – | enables Gemini summaries (else offline) |

---

## API (mounted at `/api/gov`)

| Method | Path | Auth | Purpose |
|---|---|---|---|
| GET | `/health` | open | corpus size, search mode, feeds, LLM status |
| GET | `/search` | open* | `q, doc_type, region\|jurisdiction, department, date_from, date_to, k` |
| GET | `/document/{id}` | open* | full document |
| GET | `/document/{id}/related` | open* | curated + family + keyword cross-links |
| POST | `/summarize` | open* | `{id\|text, language}` → AI summary |
| GET | `/suggest?q=` | open | auto-complete |
| GET | `/trending` | open | trending searches |
| GET | `/insights` | open | insights strip (counts, most-bookmarked, source health) |
| GET | `/categories`, `/departments` | open | filter options |
| GET/POST/DELETE | `/bookmarks` | login | personal bookmarks |
| GET/POST/DELETE | `/subscriptions` | login | update alerts |
| GET/POST/DELETE | `/saved-searches` | login | save query+filters (+alert) |
| POST | `/saved-searches/{id}/run` | login | re-run a saved search |
| POST | `/refresh` | lead/admin | poll feeds + fan-out alerts |

\* open by default; enforced when `VISIONSCAN_REQUIRE_AUTH=true` (like the rest
of the platform).

---

## Data model (SQLite, additive — see `govintel/schema.py`)
- `gov_documents` — cache of bundled + live docs (canonical metadata/body store).
- `gov_bookmarks` — `(user_id, doc_id)`.
- `gov_subscriptions` — `(user_id, query, doc_type, region)`.
- `gov_saved_searches` — `(user_id, name, query, filters JSON, alert)`.
- `gov_feed_status` — per-feed health (`last_attempt/last_success/last_count/ok`).
- `gov_search_log` — powers trending.
- reuses the platform `notifications` table (a `link` column was added).

All tables are created idempotently. The base set ships from `database.init_db()`;
the two polish tables (`gov_saved_searches`, `gov_feed_status`) are **also**
provisioned defensively in `service._ensure_seed()` via `CREATE TABLE IF NOT
EXISTS`, so the module is self-contained even on an older database.

---

## Polish features (PS-69EEFDD4DA6E9)

### 1. Advanced filters
`GET /api/gov/search` accepts `doc_type` (GR/Notification/Circular/Act/Rule/
Judgment/Scheme), `region` (or its citizen-facing alias `jurisdiction` =
`central|gujarat`), `department`, and a `date_from`/`date_to` ISO range.
`doc_type`/`region` are pushed into the store query (Chroma `where` or SQLite
`WHERE`); `department` + dates are applied as a uniform post-filter so the contract
is identical in semantic and keyword modes. Department/jurisdiction metadata is
**derived once and persisted on seed** (`categorize.guess_department/guess_region`)
when a corpus entry omits it — never recomputed per query. The UI exposes category
chips, region/jurisdiction chips, a department dropdown, date pickers and a
"Clear all".

### 2. Cross-linking engine
`GET /api/gov/document/{id}/related` returns a "Related documents" set built fully
offline: (a) **curated chains** from the corpus `related_ids` (GR ↔ parent Act ↔
judgment), surfaced first; (b) an **offline overlap score** = keyword Jaccard + an
*act-family* key (`rti`, `data`, `pension`, `cyber`, …) + same-category bonus; (c)
blended semantic neighbours when ChromaDB is present, else the whole SQLite cache
scored by overlap. Every entry carries a `link_type`
(`curated|family|keyword|category|semantic`) so the UI labels *why* two documents
are linked. Non-empty for any corpus document with kin.

### 3. Bookmarks & saved searches
- **Bookmarks** — per-user star/unstar; the "Saved" tab lists starred documents.
- **Saved searches** — persist a `query` + the full filter set (`filters` JSON) +
  an optional `alert` flag. The "Saved" tab re-runs them with one click. When
  `alert=1` the saved search **rides the existing `refresh()` fan-out**: a fresh
  document matching its filters raises a `gov_update` notification in the same bell
  as subscriptions (de-duped per user per document).

### 4. Trending / insights strip
`GET /api/gov/insights` powers a 4-tile strip atop the panel: documents indexed
(+live/saved counts), counts **by jurisdiction**, top categories (+ total
bookmarks), and **source health** (`N/M feeds live` + last-fetch time). Source
health is recorded on every `refresh()` into `gov_feed_status`; before the first
refresh it falls back to the static feed catalog (`ok: null`).

### Frontend
`GovIntelPanel.jsx` adds the insights strip, a Search/Saved tab switcher, the
date-range + Save-search + Alert controls, the Saved tab (saved searches with Run +
delete, bookmarks with unstar/open), and cross-link strength labels in the detail
drawer. The two NEW endpoints (`/insights`, `/saved-searches`) are called through a
**module-local helper** `frontend/src/components/GovIntel/govApi.js`, leaving the
shared `src/api.js` untouched; existing search/bookmark/subscription helpers in
`api.js` are reused as-is.

### Offline verification
`pytest backend/tests/test_govintel.py` (13 tests) exercises filtered search,
cross-linking, the bookmark roundtrip, the saved-search persist/re-run roundtrip,
and the insights strip — all on the SQLite keyword path (no chromadb in the venv),
which is the verified deployment fallback. `npm run build` passes; the app boots
offline with `health.semantic == False`.

## Categories
`GR · Notification · Circular · Act · Rule · Judgment · Scheme`, each tagged
`region = central | gujarat`.

## Quick verification
```bash
uvicorn app.main:app --port 8000
curl "localhost:8000/api/gov/health"
curl "localhost:8000/api/gov/search?q=pension&k=5"
curl "localhost:8000/api/gov/search?doc_type=Judgment"
curl -X POST localhost:8000/api/gov/summarize -H "Content-Type: application/json" -d '{"id":"scheme-apy"}'
# refresh + alerts need a lead/admin bearer token
```
