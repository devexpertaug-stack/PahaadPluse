"""Responsible-collection controls for non-official methods (Req 2).

These controls apply when reviews are gathered by crawling public pages (rather
than an official API/export):

* :class:`RobotsCache` fetches and caches ``robots.txt`` for 24h; a server
  error or a timeout (>10s) means the whole domain is treated as disallowed
  (Req 2.3). Disallowed URLs are skipped and counted (Req 2.2).
* :class:`RateLimiter` enforces at most 1 request / 5s per domain, honouring a
  longer ``Crawl-delay`` when present (Req 2.4).
* :func:`build_user_agent` embeds the ``PahadPulse`` product token and a
  contact e-mail on every request (Req 2.5).
* :func:`pseudonymise_reviewer` produces a salted hash of the reviewer display
  name that is stable per (reviewer, platform) and never exposes the raw name;
  the salt comes from the secrets store/env, never the repo (Req 2.6, 2.7).

The HTTP fetcher is injected so the whole module is testable offline with a
fake transport.
"""

from __future__ import annotations

import hashlib
import hmac
import time
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Protocol
from urllib.parse import urlparse

from app.core.config import get_settings

# Default contact e-mail embedded in the user-agent (Req 2.5).
DEFAULT_CONTACT_EMAIL = "research@pahadpulse.example"
PRODUCT_TOKEN = "PahadPulse"

ROBOTS_CACHE_TTL_SECONDS = 24 * 60 * 60
REQUEST_TIMEOUT_SECONDS = 10.0
MIN_REQUEST_INTERVAL_SECONDS = 5.0


def build_user_agent(version: str, contact_email: str = DEFAULT_CONTACT_EMAIL) -> str:
    """Return the user-agent string used on every outbound request (Req 2.5)."""
    return f"{PRODUCT_TOKEN}/{version} (+mailto:{contact_email})"


def pseudonymise_reviewer(display_name: str, platform: str) -> str:
    """Return a stable salted-hash pseudonym for a reviewer (Req 2.6).

    The salt is read from settings (env/secrets store) and never persisted in
    records or the repo. The same (reviewer, platform) always yields the same
    pseudonym; the raw display name is never returned or logged.
    """
    settings = get_settings()
    message = f"{platform}\x1f{display_name.strip().lower()}"
    digest = hmac.new(
        settings.pseudonym_salt.encode("utf-8"),
        message.encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()
    return f"anon-{digest[:16]}"


@dataclass
class RobotsResponse:
    """A fetched robots.txt body + crawl-delay, or a disallow-all marker."""

    body: str | None
    crawl_delay: float | None = None
    disallowed_domain: bool = False


class HttpFetcher(Protocol):
    """Minimal fetch interface so tests can inject a fake transport."""

    def __call__(self, url: str, *, headers: dict[str, str], timeout: float) -> str:
        ...


@dataclass
class _CachedRobots:
    rules: list[str]
    crawl_delay: float | None
    disallowed_domain: bool
    fetched_at: float


class RobotsCache:
    """Fetch + 24h cache of robots.txt with disallow handling (Req 2.1-2.3)."""

    def __init__(
        self,
        fetcher: HttpFetcher,
        user_agent: str,
        clock: Callable[[], float] = time.monotonic,
        ttl: float = ROBOTS_CACHE_TTL_SECONDS,
    ) -> None:
        self._fetcher = fetcher
        self._user_agent = user_agent
        self._clock = clock
        self._ttl = ttl
        self._cache: dict[str, _CachedRobots] = {}
        self.skipped_url_count = 0

    def _domain(self, url: str) -> str:
        parsed = urlparse(url)
        return f"{parsed.scheme}://{parsed.netloc}"

    def _load(self, domain: str) -> _CachedRobots:
        cached = self._cache.get(domain)
        now = self._clock()
        if cached is not None and (now - cached.fetched_at) < self._ttl:
            return cached
        try:
            body = self._fetcher(
                f"{domain}/robots.txt",
                headers={"User-Agent": self._user_agent},
                timeout=REQUEST_TIMEOUT_SECONDS,
            )
        except Exception:
            # Server error / timeout => treat the whole domain as disallowed.
            entry = _CachedRobots([], None, disallowed_domain=True, fetched_at=now)
            self._cache[domain] = entry
            return entry
        rules, crawl_delay = _parse_robots(body, self._user_agent)
        entry = _CachedRobots(rules, crawl_delay, disallowed_domain=False, fetched_at=now)
        self._cache[domain] = entry
        return entry

    def is_allowed(self, url: str) -> bool:
        """Return True if ``url`` may be fetched; count + skip disallowed URLs."""
        domain = self._domain(url)
        entry = self._load(domain)
        if entry.disallowed_domain:
            self.skipped_url_count += 1
            return False
        path = urlparse(url).path or "/"
        for disallowed_path in entry.rules:
            if disallowed_path and path.startswith(disallowed_path):
                self.skipped_url_count += 1
                return False
        return True

    def crawl_delay(self, url: str) -> float | None:
        """Return the crawl-delay for the URL's domain, if any."""
        return self._load(self._domain(url)).crawl_delay


def _parse_robots(body: str, user_agent: str) -> tuple[list[str], float | None]:
    """Parse a robots.txt body for the ``*`` and product-token groups."""
    product = user_agent.split("/", 1)[0].lower()
    disallows: list[str] = []
    crawl_delay: float | None = None
    applies = False
    for raw_line in body.splitlines():
        line = raw_line.split("#", 1)[0].strip()
        if not line:
            continue
        key, _, value = line.partition(":")
        key = key.strip().lower()
        value = value.strip()
        if key == "user-agent":
            agent = value.lower()
            applies = agent in ("*", product)
        elif applies and key == "disallow":
            if value:
                disallows.append(value)
        elif applies and key == "crawl-delay":
            try:
                crawl_delay = float(value)
            except ValueError:
                pass
    return disallows, crawl_delay


class RateLimiter:
    """At most 1 request / 5s per domain, honouring a longer crawl-delay."""

    def __init__(
        self,
        clock: Callable[[], float] = time.monotonic,
        sleeper: Callable[[float], None] = time.sleep,
        min_interval: float = MIN_REQUEST_INTERVAL_SECONDS,
    ) -> None:
        self._clock = clock
        self._sleeper = sleeper
        self._min_interval = min_interval
        self._last_request: dict[str, float] = {}

    def wait(self, domain: str, crawl_delay: float | None = None) -> float:
        """Block until the domain may be hit again; return the slept duration."""
        interval = max(self._min_interval, crawl_delay or 0.0)
        now = self._clock()
        last = self._last_request.get(domain)
        slept = 0.0
        if last is not None:
            elapsed = now - last
            if elapsed < interval:
                slept = interval - elapsed
                self._sleeper(slept)
        self._last_request[domain] = self._clock()
        return slept


@dataclass
class CollectionAudit:
    """Counts surfaced on the website for responsible collection (Req 2.2/2.9)."""

    skipped_disallowed: int = 0
    missing_source_url: int = 0
    notes: list[str] = field(default_factory=list)
