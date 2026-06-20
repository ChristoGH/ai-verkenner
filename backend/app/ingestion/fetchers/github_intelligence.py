"""Curated GitHub-intelligence fetchers (M6.5) — the four `github_*` source types from ADR 0002.

Code ships before blog posts, so GitHub is often the **earliest** convergence signal
(SIGNATURE_OUTPUTS §4). The hard guardrail: this is a **curated pipeline via the official GitHub
API**, driven by *watched* orgs / users / topics / packages declared in `sources.yaml` — **never a
broad crawler**. Each fetcher:

- requires `GITHUB_TOKEN`; without it the source is **skipped** with a clear warning (degrade,
  never crash);
- makes ~1 bounded API call (`GITHUB_PER_SOURCE_ITEMS` ceiling) and is fail-safe per source;
- preserves every item's URL.

The four types:
- `github_new_repos`      — recent repos from a watched org/user or topic (created in the window).
- `github_star_velocity`  — honest *delta* of stars vs the previous run's snapshot (not absolute
  stars); the first run for a repo seeds the baseline and emits nothing.
- `github_advisories`     — security/dependency advisories affecting a watched package (Early
  Warning for the user's own stack).
- `github_changes`        — recent breaking-change/deprecation issues/PRs (by label) in a watched
  repo.

Parse/compute functions are split out so they can be unit-tested on recorded fixtures with no
network.
"""

from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone

import httpx

from app.core.config import settings
from app.schemas.raw_item import RawItem
from app.schemas.source import Source

logger = logging.getLogger(__name__)

_API = "https://api.github.com"


# ---- shared HTTP ----


def _has_token() -> bool:
    if settings.github_token:
        return True
    return False


def _headers() -> dict[str, str]:
    return {
        "User-Agent": settings.user_agent,
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
        "Authorization": f"Bearer {settings.github_token}",
    }


def _github_get(path: str, params: dict | None = None):
    """Authenticated GitHub GET. Raises on transport/HTTP error (orchestrator isolates)."""
    resp = httpx.get(
        f"{_API}{path}", headers=_headers(), params=params or {},
        timeout=settings.http_timeout, follow_redirects=True,
    )
    remaining = resp.headers.get("x-ratelimit-remaining")
    if remaining is not None and remaining.isdigit() and int(remaining) < 5:
        logger.warning("GitHub rate limit low: %s requests remaining", remaining)
    resp.raise_for_status()
    return resp.json()


def _skip_no_token(source: Source) -> list[RawItem]:
    logger.warning(
        "source '%s' (%s): GITHUB_TOKEN not set — skipping github intelligence source",
        source.name, source.source_type.value,
    )
    return []


def _since_iso_date(days: int) -> str:
    return (datetime.now(timezone.utc) - timedelta(days=max(days, 1))).date().isoformat()


def _parse_gh_datetime(raw: str | None) -> datetime | None:
    if not raw:
        return None
    try:
        return datetime.fromisoformat(raw.replace("Z", "+00:00"))
    except ValueError:
        return None


# ---- github_new_repos ----


def new_repos_query(source: Source, since_date: str) -> str:
    scope = f"topic:{source.github_topic}" if source.github_topic else f"user:{source.repo_owner}"
    return f"{scope} created:>={since_date}"


def parse_repo_search(payload: dict, source: Source, *, title_prefix: str) -> list[RawItem]:
    """Parse a Search Repositories payload into RawItems, preserving each repo's html_url."""
    items: list[RawItem] = []
    for repo in payload.get("items", []):
        full = repo.get("full_name") or "(unknown repo)"
        url = (repo.get("html_url") or source.url).strip()
        items.append(RawItem(
            source_name=source.name,
            source_type=source.source_type,
            title=f"{title_prefix}: {full}",
            url=url,
            published_at=_parse_gh_datetime(repo.get("created_at")),
            summary=repo.get("description") or "",
        ))
    return items


def fetch_github_new_repos(source: Source) -> list[RawItem]:
    if not _has_token():
        return _skip_no_token(source)
    payload = _github_get("/search/repositories", {
        "q": new_repos_query(source, _since_iso_date(settings.source_max_age_days)),
        "sort": "created", "order": "desc",
        "per_page": settings.github_per_source_items,
    })
    return parse_repo_search(payload, source, title_prefix="New repo")


# ---- github_star_velocity (honest: delta vs previous snapshot) ----


def compute_star_velocity(
    repos: list[dict], previous: dict[str, int], source: Source, *, now: datetime,
) -> list[RawItem]:
    """Velocity = stars now − stars at the previous snapshot. Baseline (no previous) emits nothing.

    `repos` is a list of `{full_name, html_url, stargazers_count, description}`. Only positive
    deltas are surfaced — these are the "gaining stars unusually fast" weak-signal indicators.
    """
    items: list[RawItem] = []
    for repo in repos:
        full = repo.get("full_name")
        if not full:
            continue
        stars = int(repo.get("stargazers_count") or 0)
        prev = previous.get(full)
        if prev is None:
            continue  # first time we've seen this repo → seed baseline, emit nothing
        delta = stars - prev
        if delta <= 0:
            continue
        url = (repo.get("html_url") or source.url).strip()
        items.append(RawItem(
            source_name=source.name,
            source_type=source.source_type,
            title=f"{full} gained {delta} stars (now {stars})",
            url=url,
            published_at=now,
            summary=repo.get("description") or "",
        ))
    return items


def _velocity_repos(source: Source) -> list[dict]:
    """The watched repos whose stars we snapshot: top repos under a topic, or a single repo."""
    if source.github_topic:
        payload = _github_get("/search/repositories", {
            "q": f"topic:{source.github_topic}", "sort": "stars", "order": "desc",
            "per_page": settings.github_per_source_items,
        })
        return list(payload.get("items", []))
    repo = _github_get(f"/repos/{source.repo_owner}/{source.repo_name}")
    return [repo]


def fetch_github_star_velocity(source: Source) -> list[RawItem]:
    if not _has_token():
        return _skip_no_token(source)
    # Local imports so the module loads without a DB and tests can patch the store path.
    from app.db.sqlite import get_session, init_db
    from app.ingestion.star_velocity_store import latest_snapshots, record_snapshots

    repos = _velocity_repos(source)
    repo_stars = {r["full_name"]: int(r.get("stargazers_count") or 0)
                  for r in repos if r.get("full_name")}
    init_db()
    with get_session() as session:
        previous = latest_snapshots(session, list(repo_stars))
        items = compute_star_velocity(repos, previous, source, now=datetime.now(timezone.utc))
        record_snapshots(session, repo_stars)
    if not previous:
        logger.info("source '%s': star-velocity baseline seeded (%d repos), no items emitted",
                    source.name, len(repo_stars))
    return items


# ---- github_advisories (Early Warning for the user's stack) ----


def parse_advisories(payload: list, source: Source) -> list[RawItem]:
    """Parse a GitHub Advisory list into RawItems, preserving each advisory's html_url."""
    items: list[RawItem] = []
    for adv in payload:
        ghsa = adv.get("ghsa_id") or adv.get("cve_id") or "advisory"
        summary = adv.get("summary") or adv.get("description") or "(no summary)"
        url = (adv.get("html_url") or adv.get("url") or source.url).strip()
        severity = adv.get("severity")
        items.append(RawItem(
            source_name=source.name,
            source_type=source.source_type,
            title=f"Advisory {ghsa}: {summary}"[:300],
            url=url,
            published_at=_parse_gh_datetime(adv.get("published_at")),
            summary=(f"[severity: {severity}] " if severity else "") + (adv.get("description") or summary),
        ))
    return items


def fetch_github_advisories(source: Source) -> list[RawItem]:
    if not _has_token():
        return _skip_no_token(source)
    if source.github_package:
        # Global Advisory DB: advisories affecting a watched package in the user's stack.
        payload = _github_get("/advisories", {
            "ecosystem": source.github_ecosystem or "pip",
            "affects": source.github_package,
            "per_page": settings.github_per_source_items,
        })
    else:
        # Repository security advisories (those published for a watched repo).
        payload = _github_get(
            f"/repos/{source.repo_owner}/{source.repo_name}/security-advisories",
            {"per_page": settings.github_per_source_items},
        )
    if not isinstance(payload, list):
        raise ValueError(f"unexpected advisories payload (expected a list): {type(payload)}")
    return parse_advisories(payload, source)


# ---- github_changes (breaking-change / deprecation issues & PRs) ----


def parse_issues(payload: list, source: Source) -> list[RawItem]:
    """Parse a repo issues/PRs list into RawItems, preserving each issue's html_url."""
    items: list[RawItem] = []
    for issue in payload:
        title = issue.get("title") or "(untitled issue)"
        url = (issue.get("html_url") or source.url).strip()
        kind = "PR" if issue.get("pull_request") else "issue"
        body = issue.get("body") or ""
        items.append(RawItem(
            source_name=source.name,
            source_type=source.source_type,
            title=f"[{kind}] {title}",
            url=url,
            published_at=_parse_gh_datetime(issue.get("created_at")),
            summary=body[:1000],
        ))
    return items


def fetch_github_changes(source: Source) -> list[RawItem]:
    if not _has_token():
        return _skip_no_token(source)
    label = source.github_label or "breaking-change"
    payload = _github_get(f"/repos/{source.repo_owner}/{source.repo_name}/issues", {
        "labels": label, "state": "all", "sort": "created", "direction": "desc",
        "per_page": settings.github_per_source_items,
    })
    if not isinstance(payload, list):
        raise ValueError(f"unexpected issues payload (expected a list): {type(payload)}")
    return parse_issues(payload, source)
