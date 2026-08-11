"""Every tunable value in the ingest pipeline. Change values here, not in code."""

import datetime

SCHEMA_VERSION = 1

# 2026 Bar: questions sourced only from law as of this date.
# Bar Bulletin No. 1, 16 October 2025.
COVERAGE_DATE = datetime.date(2025, 6, 30)

# Politeness: one request per this many seconds, per host.
RATE_LIMIT_SECONDS = 2.0

# The e-Library starts refusing connections under sustained crawling, so it
# gets a much wider berth than lawphil's static host. Discovery needs only one
# request per month; bulk full text comes from lawphil instead.
HOST_RATE_LIMITS = {"elibrary.judiciary.gov.ph": 6.0}

USER_AGENT = (
    "BarReviewApp/1.0 (personal law-study tool; "
    "https://github.com/YOUR_USERNAME/bar-review-app)"
)

# Official 2026 Bar subject weights (Bar Bulletin No. 1).
SUBJECT_WEIGHTS = {
    "remedial": 0.25,
    "civil": 0.20,
    "commercial_tax": 0.20,
    "political": 0.15,
    "labor": 0.10,
    "criminal": 0.10,
}

DOCUMENT_TYPES = frozenset({"statute", "case", "bar_question"})

# A run producing fewer than this fraction of the last good run's document
# count is treated as a broken scrape, not a real shrink.
SHRINK_THRESHOLD = 0.95
