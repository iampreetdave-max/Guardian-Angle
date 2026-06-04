"""CrimeGPT — AI-powered crime documentation automation for CityShield.

Officers enter the facts of a case ONCE into a unified data pool (parties,
seizures, statements). From that single source of truth CrimeGPT:

  * generates every required Indian-police legal document as a branded PDF
    (Purvani Chargesheet, Medical letter, Remand request, Seizure receipt,
    Court custody letter, Accused Panchanama, Face identification form),
  * suggests applicable BNS 2023 / BNSS / BSA sections (with old-IPC
    cross-references and landmark judgments) from the case narrative, and
  * maintains a chronological case diary, auto-logging every document
    generated.

Mounted under /api/crimegpt/* and fully additive — it reuses the platform's
auth/RBAC (officer-gated), audit trail, and the navy/gold report letterhead.
Works fully offline: Hindi/Gujarati narrative translation is delegated to the
Arbiter LLM bridge when a key is configured, but the PDF is NEVER blocked when
translation is unavailable (English structural labels are retained).
"""
