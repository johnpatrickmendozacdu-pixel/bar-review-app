"""Keyword-based subject tagging. Deliberately conservative: returns "" rather
than guess, because a misfiled case puts the wrong law in front of a student."""

import re

KEYWORDS = {
    "criminal": (
        "estafa", "revised penal code", "accused", "homicide", "murder",
        "theft", "robbery", "reclusion", "prision", "criminal liability",
        "bail", "acquitted", "conviction",
    ),
    "labor": (
        "nlrc", "illegal dismissal", "employee", "employer", "labor code",
        "employment", "backwages", "reinstatement", "union",
        "collective bargaining", "labor arbiter",
    ),
    "remedial": (
        "rule 65", "certiorari", "grave abuse of discretion", "rules of court",
        "motion to dismiss", "jurisdiction", "pleading", "appeal",
        "writ of execution", "cause of action", "res judicata",
    ),
    "civil": (
        "contract of sale", "obligation", "civil code", "damages",
        "succession", "usufruct", "easement", "lease", "mortgage",
        "prescription", "co-ownership", "donation",
    ),
    "political": (
        "constitutionality", "constitution", "due process", "public officer",
        "eminent domain", "police power", "election", "comelec",
        "administrative agency", "ombudsman", "separation of powers",
    ),
    "commercial_tax": (
        "corporation", "bir", "income tax", "value-added tax", "securities",
        "insurance", "negotiable instrument", "intellectual property",
        "trademark", "patent", "bank", "deficiency assessment",
    ),
}

# Whole words only: "bir" must not score on "birth", nor "bank" on "bankrupt-"
# style prefixes of unrelated words.
_PATTERNS = {
    subject: [re.compile(rf"\b{re.escape(k)}\b") for k in keys]
    for subject, keys in KEYWORDS.items()
}

# A winner must lead the runner-up by this much, otherwise we decline to tag.
MARGIN = 2


def tag_subject(text: str) -> str:
    lowered = text.lower()
    scores = {
        subject: sum(len(p.findall(lowered)) for p in patterns)
        for subject, patterns in _PATTERNS.items()
    }
    ranked = sorted(scores.items(), key=lambda kv: kv[1], reverse=True)
    best, best_score = ranked[0]
    runner_up_score = ranked[1][1]
    if best_score == 0 or best_score - runner_up_score < MARGIN:
        return ""
    return best
