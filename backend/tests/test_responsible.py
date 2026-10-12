"""Tests for responsible-collection controls (Req 2)."""

from __future__ import annotations

from app.services.market_radar.responsible import (
    RateLimiter,
    RobotsCache,
    build_user_agent,
    pseudonymise_reviewer,
)


def test_user_agent_has_product_and_contact() -> None:
    ua = build_user_agent("0.1.0", "ops@pahadpulse.example")
    assert ua.startswith("PahadPulse/0.1.0")
    assert "mailto:ops@pahadpulse.example" in ua


def test_pseudonym_stable_and_hides_name() -> None:
    a = pseudonymise_reviewer("Riya Sharma", "Google")
    b = pseudonymise_reviewer("Riya Sharma", "Google")
    c = pseudonymise_reviewer("Riya Sharma", "Agoda")
    assert a == b  # stable per reviewer+platform
    assert a != c  # platform-scoped
    assert "Riya" not in a and "Sharma" not in a
    assert a.startswith("anon-")


def test_robots_disallow_is_counted_and_skipped() -> None:
    robots = "User-agent: *\nDisallow: /private\nCrawl-delay: 7\n"

    def fetcher(url: str, *, headers: dict, timeout: float) -> str:
        assert headers["User-Agent"].startswith("PahadPulse")
        return robots

    cache = RobotsCache(fetcher, build_user_agent("0.1.0"), clock=lambda: 0.0)
    assert cache.is_allowed("https://site.com/public/page") is True
    assert cache.is_allowed("https://site.com/private/page") is False
    assert cache.skipped_url_count == 1
    assert cache.crawl_delay("https://site.com/x") == 7.0


def test_server_error_disallows_whole_domain() -> None:
    def fetcher(url: str, *, headers: dict, timeout: float) -> str:
        raise TimeoutError("timed out")

    cache = RobotsCache(fetcher, build_user_agent("0.1.0"), clock=lambda: 0.0)
    assert cache.is_allowed("https://down.com/anything") is False
    assert cache.skipped_url_count == 1


def test_robots_cache_is_reused_within_ttl() -> None:
    calls = {"n": 0}

    def fetcher(url: str, *, headers: dict, timeout: float) -> str:
        calls["n"] += 1
        return "User-agent: *\nDisallow:\n"

    cache = RobotsCache(fetcher, build_user_agent("0.1.0"), clock=lambda: 100.0)
    cache.is_allowed("https://site.com/a")
    cache.is_allowed("https://site.com/b")
    assert calls["n"] == 1  # cached


def test_rate_limiter_waits_min_interval() -> None:
    slept: list[float] = []
    now = {"t": 0.0}
    limiter = RateLimiter(clock=lambda: now["t"], sleeper=slept.append, min_interval=5.0)
    limiter.wait("site.com")  # first request, no wait
    assert slept == []
    limiter.wait("site.com")  # immediate second request waits ~5s
    assert slept and slept[0] == 5.0


def test_rate_limiter_honours_longer_crawl_delay() -> None:
    slept: list[float] = []
    limiter = RateLimiter(clock=lambda: 0.0, sleeper=slept.append, min_interval=5.0)
    limiter.wait("site.com", crawl_delay=12.0)
    limiter.wait("site.com", crawl_delay=12.0)
    assert slept[0] == 12.0
