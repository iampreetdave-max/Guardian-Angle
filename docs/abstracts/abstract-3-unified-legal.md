# Unified Legal & Government Intelligence Platform for Central and Gujarat State

**Problem ID:** PS-69EEFDD4DA6E9 · **Category:** 2
**Hackathon:** Kanad S.H.I.E.L.D. 2026 — Cyber Crime Branch, Ahmedabad City
**Team:** _[team name placeholder]_ · **Members:** _[member placeholder]_

---

## Problem

Government Resolutions, notifications, circulars, Acts, rules, schemes, and court
judgments are scattered across dozens of independent Central and Gujarat portals,
gazettes, and judicial sites — unstructured and painful to search. Officers,
citizens, and legal staff must hunt across many sites to assemble the full
picture on one topic (pension, land, a welfare scheme), and existing tools like
India Code or Indian Kanoon cover laws and judgments but ignore GRs, notifications,
and departmental circulars. No single system aggregates and intelligently
organizes all of it.

## Proposed Solution

GovIntel is a working **Single Point of Access** that lets a user type one keyword
(e.g. *pension*) and get categorized, cross-linked, summarized results — GRs,
notifications, Acts, judgments, schemes — each with a direct link to its official
source. Its differentiator is a **bundled-corpus-plus-live-feed, offline-first
design**: a curated corpus of real documents across every category and both
jurisdictions (Central + Gujarat) guarantees semantic search, categorization, and
summaries work with zero network and zero API keys, while free government RSS/Atom
feeds (PIB national + Gujarat, RBI) layer in live updates with no paid API — each
feed wrapped in its own try/except so a dead feed never breaks search. Multilingual
(English/Hindi/Gujarati) summaries reuse the same Gemini-with-offline-fallback
engine as the companion Arbiter legal-AI module.

## Methodology

- **Data aggregation:** Curated offline corpus (every category, both jurisdictions,
  each with an official `source_url`) as the always-on backbone; keyless free
  government RSS/Atom feeds for the live layer, fetched with the Python standard
  library (no new dependency), browser UA, short timeout, per-feed fault isolation.
- **Models:** Semantic search via MiniLM ONNX embeddings in ChromaDB (the same
  offline embedder Arbiter uses); automatic keyword-search fallback when ChromaDB
  is absent, so the module stays functional on light/field deployments. Rule-based
  categorizer (GR/Notification/Circular/Act/Rule/Judgment/Scheme) + metadata
  extraction (department, date, type, region). Cross-linking engine: curated +
  semantic related-document links.
- **Validation:** `/api/gov/health` reports active search mode, corpus size, feed
  status, and LLM availability; keyword queries (pension, land) return categorized,
  source-linked results; summarization works offline (deterministic extractive)
  and online (Gemini).
- **Deployment:** Mounted at `/api/gov/*` with bookmarks, keyword/category/region
  subscriptions, and alerts that drop into the existing in-app notification bell;
  optional opt-in hourly background refresh; SQLite; Docker; runs offline.

## Tools & Technologies

Python · FastAPI · SQLite · ChromaDB · MiniLM ONNX embeddings · `urllib` +
`xml.etree` RSS/Atom ingestion (stdlib) · React + Vite (Legal Feed tab) ·
Gemini-with-offline-fallback summaries · JWT/RBAC for personalization · Docker.

## Key Differentiators

- **Single Point of Access beyond India Code/Kanoon:** unifies GRs, notifications,
  circulars *and* Acts/judgments/schemes — the gap the problem statement names.
- **Offline-first, key-free:** bundled curated corpus guarantees search,
  categorization, and summaries with no network and no paid API; live feeds layer
  on top without ever risking the offline path.
- **Semantic + categorized + cross-linked:** MiniLM semantic search, auto
  categorization, metadata extraction, and GR↔Act↔Judgment cross-links, with
  graceful keyword fallback.
- **Authenticity by design:** every result links to its official government source.
- **Personalization + alerts:** bookmarks, multi-criteria subscriptions, and update
  notifications in the same bell as case alerts; multilingual (en/hi/gu) summaries.

## Expected Impact

GovIntel collapses a multi-portal manual search into one query, returning
categorized, source-verified, summarized results so an officer, citizen, or legal
researcher reaches the right GR, Act, or judgment in seconds rather than hours. Its
key-free offline backbone means the prototype demonstrates full search and
summarization even on a disconnected field machine, while subscriptions keep
stakeholders aware of new GRs and notifications as they publish.
