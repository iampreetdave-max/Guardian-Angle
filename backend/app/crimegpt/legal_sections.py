"""Legal section intelligence — offline BNS 2023 / BNSS / BSA mapping.

A curated, offline mapping of ~25 common offence patterns to:
  * BNS 2023 substantive sections (with old-IPC cross-references),
  * BNSS 2023 procedural references where apt, and
  * landmark judgments where they are well-established and apt.

The suggestion engine scores the case narrative against each entry's keyword /
synonym set (pure offline, deterministic) and returns ranked sections with the
terms that matched and why.

SAFETY NOTE (read before editing): wrong section numbers in front of police
judges is fatal. Section numbers below were cross-checked against the Bharatiya
Nyaya Sanhita 2023, the Bharatiya Nagarik Suraksha Sanhita 2023 and the
Bharatiya Sakshya Adhiniyam 2023 as enacted. Where a mapping is broad or a
specific clause should be confirmed against the bare act for the exact facts, it
carries `verify=True` and the UI surfaces a "verify before use" caution. We
deliberately attach a landmark judgment ONLY where it is squarely on point and
uncontroversial; otherwise the list is left empty rather than risk a bad cite.
The IPC cross-references are the closest pre-2023 equivalents for officer
familiarity, not assertions of identical scope.
"""
from __future__ import annotations

import re
from typing import TypedDict


class SectionEntry(TypedDict, total=False):
    key: str
    label: str            # human title of the offence pattern
    bns: list[str]        # BNS 2023 sections, with IPC cross-ref in the string
    bnss: list[str]       # BNSS procedural references
    other: list[str]      # special acts (IT Act, NDPS, Arms Act, BSA, …)
    judgments: list[str]  # landmark judgments (only where squarely on point)
    keywords: list[str]   # primary trigger terms
    synonyms: list[str]   # secondary / colloquial terms (lower weight)
    verify: bool          # if True, UI shows "verify exact clause before use"


# ---------------------------------------------------------------- the mapping
# Each entry maps an offence pattern to its sections. BNS strings carry the
# IPC equivalent in parentheses for officer familiarity.
OFFENCE_MAP: list[SectionEntry] = [
    {
        "key": "theft",
        "label": "Theft",
        "bns": ["BNS 303 — Theft (IPC 379)"],
        "bnss": ["BNSS 173 — registration of FIR (cognizable offence)"],
        "judgments": [],
        "keywords": ["theft", "stolen", "steal", "stole", "pickpocket"],
        "synonyms": ["chori", "lifted", "missing wallet", "robbed of"],
    },
    {
        "key": "snatching",
        "label": "Snatching",
        "bns": ["BNS 304 — Snatching (new offence; cf. IPC 379/356)"],
        "bnss": ["BNSS 173 — FIR; BNSS 175 — investigation of cognizable case"],
        "judgments": [],
        "keywords": ["snatch", "snatching", "snatched", "grabbed", "chain snatch"],
        "synonyms": ["mobile snatched", "purse snatched", "phone grabbed", "jhapatmari"],
    },
    {
        "key": "robbery_dacoity",
        "label": "Robbery / Dacoity",
        "bns": [
            "BNS 309 — Robbery (IPC 392)",
            "BNS 310 — Dacoity, five or more persons (IPC 395)",
        ],
        "bnss": ["BNSS 173 — FIR; BNSS 175 — investigation"],
        "judgments": [],
        "keywords": ["robbery", "robbed", "dacoity", "loot", "looted", "armed robbery"],
        "synonyms": ["daka", "gunpoint", "knifepoint", "held up"],
    },
    {
        "key": "extortion",
        "label": "Extortion",
        "bns": ["BNS 308 — Extortion (IPC 383–389)"],
        "bnss": ["BNSS 173 — FIR"],
        "judgments": [],
        "keywords": ["extortion", "extort", "ransom", "protection money", "hafta"],
        "synonyms": ["demanded money", "threatened for money", "khandani", "blackmail for money"],
    },
    {
        "key": "cheating_personation_online",
        "label": "Cheating / Online personation & fraud",
        "bns": [
            "BNS 318 — Cheating (IPC 415/420)",
            "BNS 319 — Cheating by personation (IPC 416/419)",
        ],
        "other": [
            "IT Act 66C — identity theft",
            "IT Act 66D — cheating by personation using computer resource",
        ],
        "bnss": ["BNSS 173 — FIR; route via 1930 / NCRP for cyber-financial fraud"],
        "judgments": [],
        "keywords": ["cheating", "fraud", "otp", "phishing", "personation",
                     "impersonat", "fake", "online fraud", "upi fraud", "scam"],
        "synonyms": ["duped", "kyc fraud", "fake call", "bank fraud", "card fraud",
                     "vishing", "smishing", "lottery", "fake profile", "money transferred"],
    },
    {
        "key": "criminal_breach_of_trust",
        "label": "Criminal breach of trust",
        "bns": ["BNS 316 — Criminal breach of trust (IPC 405/406/409)"],
        "bnss": ["BNSS 173 — FIR"],
        "judgments": [],
        "keywords": ["breach of trust", "misappropriat", "embezzle", "entrusted"],
        "synonyms": ["criminal breach", "siphoned funds", "dishonestly used"],
    },
    {
        "key": "assault_hurt",
        "label": "Assault / Hurt / Grievous hurt",
        "bns": [
            "BNS 115 — Voluntarily causing hurt (IPC 323)",
            "BNS 117 — Voluntarily causing grievous hurt (IPC 325)",
        ],
        "bnss": ["BNSS 173 — FIR; medico-legal certificate (MLC) of the injured"],
        "judgments": [],
        "keywords": ["assault", "beaten", "beat", "hurt", "injured", "attack",
                     "grievous", "fracture", "stabbed", "wounded"],
        "synonyms": ["thrashed", "marpit", "physical fight", "hit with", "bleeding injury"],
    },
    {
        "key": "sexual_harassment",
        "label": "Sexual harassment",
        "bns": ["BNS 75 — Sexual harassment (IPC 354A)"],
        "bnss": ["BNSS 173; statement of victim (BNSS 176) by woman officer where required"],
        "judgments": [
            "Vishaka v. State of Rajasthan (1997) 6 SCC 241 — workplace harassment guidelines",
        ],
        "keywords": ["sexual harassment", "molest", "molestation", "354a",
                     "unwelcome", "lewd", "obscene gesture"],
        "synonyms": ["chhedchhad", "eve teasing", "inappropriate touch", "passed comments"],
        "verify": True,
    },
    {
        "key": "outraging_modesty",
        "label": "Assault to outrage modesty of a woman",
        "bns": ["BNS 74 — Assault or use of criminal force to woman with intent to outrage modesty (IPC 354)"],
        "bnss": ["BNSS 173; woman officer to record statement where applicable"],
        "judgments": [],
        "keywords": ["outrage modesty", "criminal force woman", "354", "groped"],
        "synonyms": ["inappropriately touched", "modesty"],
        "verify": True,
    },
    {
        "key": "stalking",
        "label": "Stalking (including cyber-stalking)",
        "bns": ["BNS 78 — Stalking, incl. monitoring electronic communication (IPC 354D)"],
        "other": ["IT Act 67 — where obscene material is transmitted"],
        "bnss": ["BNSS 173 — FIR"],
        "judgments": [],
        "keywords": ["stalk", "stalking", "following her", "cyber stalk",
                     "repeatedly messag", "monitoring", "354d"],
        "synonyms": ["kept following", "online harassment", "tracking her", "spying messages"],
    },
    {
        "key": "criminal_intimidation",
        "label": "Criminal intimidation",
        "bns": ["BNS 351 — Criminal intimidation (IPC 503/506)"],
        "bnss": ["BNSS 173 — FIR"],
        "judgments": [],
        "keywords": ["intimidat", "threat", "threaten", "death threat", "506"],
        "synonyms": ["dhamki", "warned to", "threatened to kill", "menacing message"],
    },
    {
        "key": "house_trespass_burglary",
        "label": "House-trespass / Burglary (house-breaking)",
        "bns": [
            "BNS 331 — House-trespass / house-breaking & aggravated forms (IPC 442–457)",
            "BNS 329 — Criminal trespass / house-trespass (IPC 441/448)",
        ],
        "bnss": ["BNSS 173 — FIR"],
        "judgments": [],
        "keywords": ["burglary", "house breaking", "housebreaking", "trespass",
                     "broke into", "forced entry", "lock broken"],
        "synonyms": ["entered house", "ghar mein ghuse", "night break-in", "broke the lock"],
    },
    {
        "key": "murder",
        "label": "Murder",
        "bns": ["BNS 103 — Punishment for murder (IPC 302)"],
        "bnss": ["BNSS 173; inquest (BNSS 194); post-mortem"],
        "judgments": [
            "Bachan Singh v. State of Punjab (1980) 2 SCC 684 — 'rarest of rare' for death sentence",
        ],
        "keywords": ["murder", "killed", "homicide", "death caused", "302", "stabbed to death"],
        "synonyms": ["hatya", "shot dead", "killed him", "killed her", "beaten to death"],
    },
    {
        "key": "culpable_homicide",
        "label": "Culpable homicide not amounting to murder",
        "bns": ["BNS 105 — Punishment for culpable homicide not amounting to murder (IPC 304)"],
        "bnss": ["BNSS 173; inquest (BNSS 194)"],
        "judgments": [],
        "keywords": ["culpable homicide", "304", "not amounting to murder"],
        "synonyms": ["sudden fight death", "without premeditation"],
        "verify": True,
    },
    {
        "key": "attempt",
        "label": "Attempt to commit offence",
        "bns": ["BNS 109 — Attempt to murder (IPC 307); BNS 62 — attempt generally (IPC 511)"],
        "bnss": ["BNSS 173 — FIR"],
        "judgments": [],
        "keywords": ["attempt to murder", "attempt", "tried to kill", "307"],
        "synonyms": ["attempted", "tried to murder", "fired but missed"],
        "verify": True,
    },
    {
        "key": "rioting",
        "label": "Rioting",
        "bns": ["BNS 191 — Rioting (IPC 146/147); BNS 192 — armed with deadly weapon (IPC 148)"],
        "bnss": ["BNSS 173 — FIR"],
        "judgments": [],
        "keywords": ["riot", "rioting", "mob", "violent crowd", "stone pelting"],
        "synonyms": ["unlawful mob", "clash between groups", "danga"],
    },
    {
        "key": "unlawful_assembly",
        "label": "Unlawful assembly",
        "bns": ["BNS 189 — Unlawful assembly (IPC 141/143)"],
        "bnss": ["BNSS 173 — FIR"],
        "judgments": [],
        "keywords": ["unlawful assembly", "five or more", "common object", "141"],
        "synonyms": ["illegal gathering", "assembled to"],
    },
    {
        "key": "dowry_death",
        "label": "Dowry death",
        "bns": ["BNS 80 — Dowry death (IPC 304B)"],
        "other": ["Dowry Prohibition Act 1961"],
        "bnss": ["BNSS 173; inquest by Executive Magistrate (BNSS 196) for unnatural death of woman within 7 years of marriage"],
        "judgments": [],
        "keywords": ["dowry death", "dowry", "304b", "harassment for dowry", "bride death"],
        "synonyms": ["dahej", "burnt for dowry", "died within marriage"],
        "verify": True,
    },
    {
        "key": "cruelty_husband",
        "label": "Cruelty by husband or relatives",
        "bns": ["BNS 85 — Cruelty by husband or relative of husband (IPC 498A)"],
        "bnss": ["BNSS 173 — FIR"],
        "judgments": [
            "Arnesh Kumar v. State of Bihar (2014) 8 SCC 273 — arrest guidelines, no automatic arrest",
        ],
        "keywords": ["cruelty", "498a", "harassment by husband", "matrimonial cruelty"],
        "synonyms": ["domestic cruelty", "in-laws harassment", "tortured by husband"],
        "verify": True,
    },
    {
        "key": "rash_driving",
        "label": "Rash / negligent driving causing death",
        "bns": [
            "BNS 281 — Rash driving on a public way (IPC 279)",
            "BNS 106 — Causing death by negligence (IPC 304A)",
        ],
        "other": ["Motor Vehicles Act 1988 — relevant provisions"],
        "bnss": ["BNSS 173; mechanical inspection of vehicle"],
        "judgments": [],
        "keywords": ["rash driving", "negligent driving", "hit and run", "accident",
                     "ran over", "death by negligence", "279", "304a"],
        "synonyms": ["over speeding", "drunk driving accident", "vehicle hit"],
    },
    {
        "key": "abduction_kidnapping",
        "label": "Kidnapping / Abduction",
        "bns": [
            "BNS 137 — Kidnapping (IPC 359/363)",
            "BNS 140 — Kidnapping/abduction to murder, ransom, etc. (IPC 364/364A)",
        ],
        "bnss": ["BNSS 173 — FIR"],
        "judgments": [],
        "keywords": ["kidnap", "abduct", "abduction", "ransom demand", "forcibly took"],
        "synonyms": ["apraharan", "lifted the child", "took away forcibly"],
    },
    {
        "key": "forgery",
        "label": "Forgery",
        "bns": [
            "BNS 336 — Forgery (IPC 463/465)",
            "BNS 340 — Forged document used as genuine (IPC 471)",
        ],
        "other": ["IT Act 66 — where electronic records are tampered"],
        "bnss": ["BNSS 173 — FIR; document examiner (BSA expert opinion)"],
        "judgments": [],
        "keywords": ["forgery", "forged", "fake document", "counterfeit document",
                     "fabricated", "false signature"],
        "synonyms": ["fake stamp", "forged signature", "tampered document"],
    },
    {
        "key": "counterfeit_currency",
        "label": "Counterfeit currency",
        "bns": ["BNS 178 — Counterfeiting currency / bank notes (IPC 489A–489E)"],
        "bnss": ["BNSS 173 — FIR; FSL examination of notes"],
        "judgments": [],
        "keywords": ["counterfeit", "fake currency", "fake notes", "fake money", "489a"],
        "synonyms": ["fake 500 notes", "nakli note", "duplicate currency"],
    },
    {
        "key": "mischief",
        "label": "Mischief (damage to property)",
        "bns": ["BNS 324 — Mischief (IPC 425/426/427)"],
        "bnss": ["BNSS 173 — FIR"],
        "judgments": [],
        "keywords": ["mischief", "damaged property", "vandal", "destroyed", "broke"],
        "synonyms": ["smashed", "set fire to property", "property damage"],
    },
    {
        "key": "defamation",
        "label": "Defamation",
        "bns": ["BNS 356 — Defamation (IPC 499/500)"],
        "bnss": ["Generally non-cognizable; complaint to Magistrate (BNSS 223)"],
        "judgments": [
            "Subramanian Swamy v. Union of India (2016) 7 SCC 221 — criminal defamation upheld",
        ],
        "keywords": ["defamation", "defamed", "slander", "libel", "reputation harmed"],
        "synonyms": ["maligned", "false allegations published", "character assassination"],
        "verify": True,
    },
    {
        "key": "voyeurism",
        "label": "Voyeurism",
        "bns": ["BNS 77 — Voyeurism (IPC 354C)"],
        "other": ["IT Act 66E — capturing/transmitting private images"],
        "bnss": ["BNSS 173 — FIR"],
        "judgments": [],
        "keywords": ["voyeur", "voyeurism", "secretly filmed", "hidden camera",
                     "private images", "354c"],
        "synonyms": ["recorded without consent", "spy camera", "filmed in private"],
    },
    {
        "key": "obscene_acts",
        "label": "Obscene acts / songs in public",
        "bns": ["BNS 296 — Obscene acts and songs in public place (IPC 294)"],
        "other": ["IT Act 67 — publishing obscene material electronically"],
        "bnss": ["BNSS 173 — FIR"],
        "judgments": [],
        "keywords": ["obscene", "obscenity", "indecent", "vulgar", "294"],
        "synonyms": ["lewd act in public", "obscene song"],
    },
    {
        "key": "drugs_ndps",
        "label": "Narcotic drugs (NDPS)",
        "bns": [],
        "other": [
            "NDPS Act 8 — prohibition of production/possession/sale",
            "NDPS Act 20 — cannabis; 21 — manufactured drugs; 22 — psychotropic substances",
        ],
        "bnss": ["BNSS 173; NDPS search/seizure safeguards (NDPS s.42/50)"],
        "judgments": [
            "State of Punjab v. Baldev Singh (1999) 6 SCC 172 — s.50 search-rights compliance",
        ],
        "keywords": ["ndps", "drugs", "narcotic", "ganja", "charas", "heroin",
                     "mdma", "cocaine", "psychotropic", "contraband substance"],
        "synonyms": ["drug peddling", "drug seizure", "nasha", "brown sugar"],
    },
    {
        "key": "arms_act",
        "label": "Illegal arms (Arms Act)",
        "bns": [],
        "other": ["Arms Act 1959 s.25 — punishment for illegal arms/ammunition"],
        "bnss": ["BNSS 173; FSL ballistic examination"],
        "judgments": [],
        "keywords": ["arms act", "illegal weapon", "country pistol", "firearm",
                     "unlicensed", "katta", "ammunition"],
        "synonyms": ["pistol seized", "desi katta", "live cartridges"],
    },
    {
        "key": "pocso",
        "label": "Offences against children (POCSO)",
        "bns": ["BNS 137/140 — kidnapping where apt"],
        "other": ["POCSO Act 2012 — sexual offences against children"],
        "bnss": ["BNSS 173; child-friendly procedure; statement before Magistrate"],
        "judgments": [],
        "keywords": ["pocso", "minor", "child sexual", "child victim", "under 18"],
        "synonyms": ["minor girl", "minor boy", "child abuse"],
        "verify": True,
    },
]


# ---------------------------------------------------------------- scoring
_WORD_RE = re.compile(r"[a-z0-9]+")


def _normalise(text: str) -> str:
    return (text or "").lower()


def _term_hits(haystack: str, term: str) -> bool:
    """Whole-token-aware containment: a multi-word term matches as a substring,
    a single token matches on a word boundary so 'arm' doesn't hit 'alarm'."""
    term = term.lower().strip()
    if not term:
        return False
    if " " in term:
        return term in haystack
    return re.search(rf"\b{re.escape(term)}\b", haystack) is not None


def suggest_sections(narrative: str, top_k: int = 6) -> list[dict]:
    """Rank offence patterns against a free-text case narrative.

    Pure-offline keyword/synonym scoring. Keyword hits weigh more than synonym
    hits. Returns ranked entries with the matched terms (why-matched) and the
    full section payload. Deterministic — same input always yields same output.
    """
    hay = _normalise(narrative)
    if not hay.strip():
        return []

    scored: list[dict] = []
    for entry in OFFENCE_MAP:
        matched_kw = [t for t in entry.get("keywords", []) if _term_hits(hay, t)]
        matched_syn = [t for t in entry.get("synonyms", []) if _term_hits(hay, t)]
        if not matched_kw and not matched_syn:
            continue
        # Keywords weigh 2, synonyms 1; cap each unique term once.
        score = 2 * len(set(matched_kw)) + 1 * len(set(matched_syn))
        scored.append({
            "key": entry["key"],
            "label": entry["label"],
            "bns": entry.get("bns", []),
            "bnss": entry.get("bnss", []),
            "other": entry.get("other", []),
            "judgments": entry.get("judgments", []),
            "verify": bool(entry.get("verify", False)),
            "score": score,
            "matched_terms": sorted(set(matched_kw + matched_syn)),
        })

    # Highest score first; tie-break by number of matched terms then label for
    # a stable, deterministic ordering.
    scored.sort(key=lambda s: (-s["score"], -len(s["matched_terms"]), s["label"]))
    return scored[:top_k]


def all_offence_patterns() -> list[dict]:
    """The full curated catalogue (for a reference panel / health check)."""
    return [
        {
            "key": e["key"],
            "label": e["label"],
            "bns": e.get("bns", []),
            "bnss": e.get("bnss", []),
            "other": e.get("other", []),
            "judgments": e.get("judgments", []),
            "verify": bool(e.get("verify", False)),
        }
        for e in OFFENCE_MAP
    ]
