"""Polite HTTP with a disk cache. Knows nothing about law."""

import hashlib
import pathlib
import time

import requests

from ingest import config

CERT_BUNDLE = pathlib.Path(__file__).parent.parent / "certs" / "elibrary-chain.pem"

# Hosts that serve an incomplete certificate chain and need the pinned bundle.
PINNED_HOSTS = ("elibrary.judiciary.gov.ph",)


def cache_key(url: str) -> str:
    return hashlib.sha256(url.encode()).hexdigest()[:32] + ".html"


class Fetcher:
    def __init__(self, cache_dir: pathlib.Path, session=None, sleep=time.sleep):
        self.cache_dir = pathlib.Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.sleep = sleep
        self.session = session or requests.Session()
        self.session.headers = {"User-Agent": config.USER_AGENT}

    def _delay_for(self, url: str) -> float:
        """Politeness delay for this host. Government servers get more room."""
        for host, delay in getattr(config, "HOST_RATE_LIMITS", {}).items():
            if host in url:
                return delay
        return config.RATE_LIMIT_SECONDS

    def _verify_for(self, url: str):
        """Return the CA bundle to verify against. Never False."""
        if any(host in url for host in PINNED_HOSTS):
            return str(CERT_BUNDLE)
        return True

    def get(self, url: str) -> str:
        cached = self.cache_dir / cache_key(url)
        if cached.exists():
            return cached.read_text(encoding="utf-8")

        self.sleep(self._delay_for(url))
        response = self.session.get(url, timeout=30, verify=self._verify_for(url))
        response.raise_for_status()
        cached.write_text(response.text, encoding="utf-8")
        return response.text
