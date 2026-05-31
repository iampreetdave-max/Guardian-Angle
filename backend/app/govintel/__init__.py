"""GovIntel — Unified Legal & Government Intelligence module for CityShield.

A single point of access to Government Resolutions (GRs), notifications,
circulars, Acts, rules, court judgments and schemes from Central + Gujarat
sources. Semantic + keyword search, categorisation, metadata, AI summaries,
cross-linking, bookmarks, and update alerts that flow into the existing
notification system.

Mounted under /api/gov/* and fully additive — it never touches the VisionScan
or Arbiter routes. Works fully offline over a bundled curated corpus; an
optional, fault-tolerant RSS layer pulls live updates from free government feeds
when the network is available.
"""
