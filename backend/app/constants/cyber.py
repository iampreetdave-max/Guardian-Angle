"""NCRP / 1930 cybercrime fraud taxonomy for structured complaint intake.

A small, controlled vocabulary that mirrors the categories the National Cyber
Crime Reporting Portal (cybercrime.gov.in) and the 1930 helpline triage on.
Each entry carries a victim-facing label + description, the applicable legal
sections (IT Act + Bharatiya Nyaya Sanhita) as a display string, a one-line
prevention tip, and a ``golden_hour`` flag.

``golden_hour`` marks money-loss categories where reporting to 1930 within the
first hours can let the bank/payment rails *freeze* the fraudulent transfer
before the mule account cashes out — so the UI nudges the victim to call 1930
immediately for those.

Legal-section notes (kept accurate, plain-language):
- IT Act s.66C  — identity theft (stolen passwords / OTP / e-signature)
- IT Act s.66D  — cheating by personation using a computer resource
- BNS  s.318    — cheating (s.318(4) = cheating + dishonest inducement)
- BNS  s.308    — extortion
- BNS  s.336/356— forgery / defamation (impersonation harms)
- BNS  s.351    — criminal intimidation (threats, fake "arrest")
"""
from __future__ import annotations

# Ordered dict so the frontend dropdown reads in a sensible triage order
# (highest-frequency money-loss frauds first).
CYBER_CATEGORIES: dict[str, dict] = {
    "upi_otp_fraud": {
        "label": "UPI / OTP Fraud",
        "description": "Money debited after sharing an OTP, UPI PIN, or approving "
                       "a collect/autopay request you didn't initiate.",
        "legal_sections": "IT Act s.66C/66D; BNS s.318(4) Cheating",
        "prevention": "Never share an OTP or UPI PIN — banks never ask for them; "
                      "'receiving' money never needs your PIN.",
        "golden_hour": True,
    },
    "digital_arrest_scam": {
        "label": "Digital Arrest Scam",
        "description": "Callers posing as police/CBI/customs keep you on video and "
                       "threaten 'arrest' unless you transfer money for 'verification'.",
        "legal_sections": "IT Act s.66D; BNS s.351 Criminal Intimidation; s.318 Cheating",
        "prevention": "No real agency 'arrests' you over a video call or asks for "
                      "money to clear your name — hang up and call 1930.",
        "golden_hour": False,
    },
    "investment_trading_scam": {
        "label": "Investment / Trading Scam",
        "description": "Fake stock/crypto/forex apps or 'guaranteed return' groups that "
                       "show fake profits, then block withdrawals.",
        "legal_sections": "IT Act s.66D; BNS s.318(4) Cheating",
        "prevention": "Guaranteed high returns are a red flag; verify the broker on "
                      "the SEBI/RBI registered list before investing.",
        "golden_hour": True,
    },
    "sextortion": {
        "label": "Sextortion",
        "description": "Threats to leak intimate photos/video (often from a fake "
                       "video call) unless you keep paying.",
        "legal_sections": "IT Act s.66E/67; BNS s.308 Extortion; s.351 Criminal Intimidation",
        "prevention": "Stop paying — it never ends; preserve the chat, block the "
                      "account and report. Paying only invites more demands.",
        "golden_hour": False,
    },
    "phishing_smishing": {
        "label": "Phishing / Smishing",
        "description": "Fake bank/KYC/electricity-bill links by SMS, email or WhatsApp "
                       "that harvest your card, net-banking or login details.",
        "legal_sections": "IT Act s.66C/66D; BNS s.319 Cheating by Personation",
        "prevention": "Type bank/government URLs yourself; never log in via a link "
                      "sent to you, especially 'KYC expiring today' messages.",
        "golden_hour": False,
    },
    "loan_app_extortion": {
        "label": "Loan-App Extortion",
        "description": "Illegal instant-loan apps that harvest your contacts/photos "
                       "and harass or blackmail you over tiny dues.",
        "legal_sections": "IT Act s.66/67; BNS s.308 Extortion; s.351 Criminal Intimidation",
        "prevention": "Only borrow from RBI-registered lenders; deny apps access to "
                      "your contacts and gallery.",
        "golden_hour": True,
    },
    "job_task_fraud": {
        "label": "Job / Task Fraud",
        "description": "'Work from home' or 'like & review' tasks that pay small "
                       "amounts first, then ask you to deposit to unlock earnings.",
        "legal_sections": "IT Act s.66D; BNS s.318(4) Cheating",
        "prevention": "A real job never asks you to pay to earn; stop the moment a "
                      "'task' requires a deposit.",
        "golden_hour": True,
    },
    "fake_shopping": {
        "label": "Fake Shopping / Delivery",
        "description": "Fraudulent shopping sites, social-media stores or fake "
                       "courier/parcel pages that take payment and vanish.",
        "legal_sections": "IT Act s.66D; BNS s.318(4) Cheating",
        "prevention": "Prefer cash-on-delivery from unknown sellers; check reviews "
                      "and never pay a 'customs/redelivery fee' over a link.",
        "golden_hour": True,
    },
    "identity_theft": {
        "label": "Identity Theft",
        "description": "Your PAN/Aadhaar, photos or documents misused to open "
                       "accounts, take loans or pass as you.",
        "legal_sections": "IT Act s.66C Identity Theft; BNS s.319 Cheating by Personation",
        "prevention": "Mask your Aadhaar, watch your credit report, and report misuse "
                      "early to limit the damage.",
        "golden_hour": False,
    },
    "social_media_impersonation": {
        "label": "Social-Media Impersonation",
        "description": "A fake profile cloning your name/photo to scam your friends "
                       "and family for money.",
        "legal_sections": "IT Act s.66C/66D; BNS s.319 Cheating by Personation; s.356 Defamation",
        "prevention": "Report and get the clone taken down fast, and warn your "
                      "contacts not to send money on your 'behalf'.",
        "golden_hour": False,
    },
}

# Controlled vocabulary for *how* the money/contact moved — keeps the field
# analysable instead of free text.
FRAUD_CHANNELS: tuple[str, ...] = (
    "UPI", "card", "phone_call", "SMS", "WhatsApp", "fake_app", "website",
    "social_media",
)


def category_keys() -> list[str]:
    """Valid cyber_category values (taxonomy keys)."""
    return list(CYBER_CATEGORIES.keys())


def is_golden_hour(category: str | None) -> bool:
    """True when rapid 1930 reporting may still freeze the fraudulent transfer."""
    if not category:
        return False
    entry = CYBER_CATEGORIES.get(category)
    return bool(entry and entry.get("golden_hour"))


def category_list() -> list[dict]:
    """Taxonomy as a JSON-friendly list (key + fields) for the frontend."""
    return [{"key": k, **v} for k, v in CYBER_CATEGORIES.items()]
