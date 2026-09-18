"""Who depends on a GitHub repository: the most starred dependents and the companies among them.

FINDINGS
========

Run 2026-09-14 against ``jannikmi/timezonefinder``. The counts are a snapshot and go
stale on their own; re-run rather than quote them.

1. **The dependents page cannot list everyone.** GitHub's headline says 4,905
   repositories, but the cursor chain ends after 68 pages - 2,001 unique repositories -
   with ``Next`` rendered disabled, identically on every re-fetch. The cursors count
   down, so what is reachable is the ~2,000 most recently indexed dependents; older
   ones exist in the headline count and nowhere this page will show them. This is a
   property of GitHub, not of the scraper, and no ``--delay`` changes it.
2. Of the 2,001: 237 forks, 16 archived, 308 organisation and 1,693 user owners, 643
   pushed within a year; 198 non-fork repositories have >= 10 stars and 34 have >= 100.
   Python is the primary language of 1,488.
3. **Most starred** (forks excluded): ``fivetran/great_expectations`` (~11.8k),
   ``dr5hn/countries-states-cities-database`` (~9.8k), ``LibrePhotos/librephotos``
   (~8.1k), ``sgoudelis/ground-station`` (~4.8k), ``endurain-project/endurain`` (~2.2k),
   ``posit-dev/py-shiny`` (~1.7k), ``GoogleCloudPlatform/data-science-on-gcp`` (~1.4k),
   ``RocketPy-Team/RocketPy`` (~1.1k), ``microsoft/farmvibes-ai`` (~0.9k).
4. **Company-owned** (``owner`` evidence): Google (``GoogleCloudPlatform``), Microsoft
   (``farmvibes-ai``, ``whales``), Amazon (``aws-samples/sample-genai-on-eks``,
   ``amazon-science``), Fivetran and Posit (from the top 10 above), NOAA
   (``noaa-oar-arl``); NASA only through an organisation's metadata (``GEOS-ESM``).
5. ``user`` evidence is mostly noise for this purpose - it attributes a 493-star personal
   project to Siemens because its author works there - which is why it is reported
   separately and never mixed into the ``owner`` matches.

HOW IT WORKS
============

GitHub has no API for the "Used by" list, so the list is scraped from the HTML page
``/<owner>/<repo>/network/dependents`` - 30 rows per page, paged by the cursor in the
page's ``Next`` link. That chain ends after roughly 2,000 entries however large
the headline count (finding 1); an intermittent empty page is retried rather than taken
as the end. Every page is appended to ``raw.jsonl`` and the cursor to
``state.json`` as it arrives, so an interrupted scrape continues with ``--resume``.
The row markup (``data-test-id="dg-repo-pkg-dependent"``) is the fragile part; all of
the parsing is in ``parse_page``.

The scraped star counts are enough to rank, but not to tell a company from a person or a
fork from an original, so each dependent is then looked up through the GraphQL API in
batches (stars, fork parent, archived, last push, language, and the owner's type, name,
website and - for users - company field). That needs a token: ``GITHUB_TOKEN`` /
``GH_TOKEN``, or whatever ``gh auth token`` prints. Answers are cached in
``enriched.json``; repositories deleted since GitHub indexed them come back as ``null``.

A dependent is attributed to a company by matching ``COMPANY_PATTERNS`` against, in
order of confidence: the owner login (``owner``), an organisation's display name or
website (``org``), and a user's free-text company field (``user``). Only the first
is strong evidence - a user writing ``@google`` in their profile made a personal repo.

Nothing here is specific to timezonefinder except the default ``--repo``. Standard
library only; runs without the ``proto`` group::

    uv run python prototypes/dependents_analysis.py            # scrape, enrich, report
    uv run python prototypes/dependents_analysis.py --resume   # continue an interrupted run
    uv run python prototypes/dependents_analysis.py --repo owner/name --top 100

Output lands in ``tmp/dependents/<owner>_<name>/`` (gitignored): ``dependents.csv``
(one row per dependent, most starred first) and ``report.md``.
"""

import argparse
import csv
import json
import os
import re
import subprocess
import sys
import time
import urllib.error
import urllib.request
from collections import Counter, defaultdict
from datetime import UTC, datetime, timedelta
from pathlib import Path

DEFAULT_REPO = "jannikmi/timezonefinder"
OUT_ROOT = Path(__file__).resolve().parent.parent / "tmp" / "dependents"
GRAPHQL_URL = "https://api.github.com/graphql"
USER_AGENT = "timezonefinder-dependents-analysis"
GRAPHQL_BATCH = 25  # 50 repositories per query drew HTTP 499 (server-side timeout)
EMPTY_PAGE_RETRIES = 3
ACTIVE_WITHIN = timedelta(days=365)

# Company -> case-insensitive regex, searched in the owner login, an organisation's name
# and website, and a user's company field. ``\b`` treats ``-`` as a boundary, so
# ``\baws\b`` matches ``aws-samples`` but not ``laws``. Keep tokens specific: a short
# bare word (``meta``, ``sap``, ``here``) matches unrelated logins.
COMPANY_PATTERNS: dict[str, str] = {
    "Microsoft": r"\bmicrosoft\b|\bazure(-samples)?\b|\bmsft\b|microsoft\.com",
    "Amazon / AWS": r"\baws(-samples|labs|-solutions-library-samples)?\b|\bamzn\b|\bamazon\b|\bawslabs\b",
    "Google": r"\bgoogle\b|\bgoogleapis\b|\bgooglecloudplatform\b|\bgoogle-research\b|\bdeepmind\b|google\.com",
    "Meta": r"\bfacebook(research|incubator)?\b|\bmeta-llama\b|\bmetaresearch\b|\bmeta\.com\b|\bfb\.com\b",
    "Apple": r"\bapple\b|apple\.com",
    "NVIDIA": r"\bnvidia\b",
    "IBM": r"\bibm\b",
    "Intel": r"\bintel\b|\bintel-analytics\b",
    "Oracle": r"\boracle\b",
    "Salesforce": r"\bsalesforce\b",
    "SAP": r"\bsap-samples\b|\bsap\.com\b|^sap$",
    "Siemens": r"\bsiemens\b",
    "Bosch": r"\bbosch\b",
    "Samsung": r"\bsamsung\b",
    "Huawei": r"\bhuawei\b",
    "Alibaba": r"\balibaba\b|\baliyun\b",
    "Tencent": r"\btencent\b",
    "Baidu": r"\bbaidu\b|\bpaddlepaddle\b",
    "ByteDance": r"\bbytedance\b",
    "Uber": r"\buber\b",
    "Lyft": r"\blyft\b",
    "Airbnb": r"\bairbnb\b",
    "Netflix": r"\bnetflix\b",
    "Spotify": r"\bspotify\b",
    "Shopify": r"\bshopify\b",
    "Stripe": r"\bstripe\b",
    "Cloudflare": r"\bcloudflare\b",
    "Databricks": r"\bdatabricks\b",
    "Snowflake": r"\bsnowflake(db|-labs)?\b",
    "Elastic": r"\belastic\b",
    "Grafana Labs": r"\bgrafana\b",
    "Red Hat": r"\bredhat\b|\bred-hat\b",
    "Mozilla": r"\bmozilla\b",
    "Hugging Face": r"\bhuggingface\b",
    "OpenAI": r"\bopenai\b",
    "Anthropic": r"\banthropics?\b",
    "Mapbox": r"\bmapbox\b",
    "Esri": r"\besri\b",
    "TomTom": r"\btomtom\b",
    "Garmin": r"\bgarmin\b",
    "Planet Labs": r"\bplanetlabs\b",
    "Booking.com": r"\bbookingcom\b|booking\.com",
    "Expedia": r"\bexpedia\b",
    "Zalando": r"\bzalando\b",
    "Delivery Hero": r"\bdeliveryhero\b",
    "DoorDash": r"\bdoordash\b",
    "Grab": r"\bgrab(taxi)?\b",
    "Fivetran": r"\bfivetran\b",
    "Posit": r"\bposit-dev\b|\brstudio\b",
    "Apache Software Foundation": r"^apache$",
    "NASA": r"\bnasa\b",
    "NOAA": r"\bnoaa\b",
    "ECMWF": r"\becmwf\b",
    "Home Assistant": r"\bhome-assistant\b",
}
_COMPILED_PATTERNS = [
    (name, re.compile(rx, re.IGNORECASE)) for name, rx in COMPANY_PATTERNS.items()
]


# --------------------------------------------------------------------------- HTTP


def http(
    url: str,
    *,
    data: bytes | None = None,
    headers: dict[str, str] | None = None,
    tries: int = 6,
) -> bytes:
    """GET (or POST when ``data`` is given) with backoff on rate limits and server errors."""
    headers = {"User-Agent": USER_AGENT, **(headers or {})}
    for attempt in range(tries):
        request = urllib.request.Request(url, data=data, headers=headers)
        try:
            with urllib.request.urlopen(request, timeout=60) as response:
                return response.read()
        except urllib.error.HTTPError as error:
            if (
                error.code not in (403, 429, 499, 500, 502, 503, 504)
                or attempt == tries - 1
            ):
                raise
            wait = int(error.headers.get("Retry-After") or 0) or min(
                2 ** (attempt + 2), 120
            )
        except urllib.error.URLError:
            if attempt == tries - 1:
                raise
            wait = 2 ** (attempt + 1)
        print(f"  retrying in {wait}s ({url[:80]})", file=sys.stderr)
        time.sleep(wait)
    raise AssertionError("unreachable")


# --------------------------------------------------------------------------- scrape

_ROW_SPLIT = 'data-test-id="dg-repo-pkg-dependent"'
_REPO_RE = re.compile(r'data-hovercard-type="repository"[^>]*?href="/([^"/]+/[^"/]+)"')
_STARS_RE = re.compile(r"octicon-star\b.*?</svg>\s*([\d,]+)", re.DOTALL)
_FORKS_RE = re.compile(r"octicon-repo-forked\b.*?</svg>\s*([\d,]+)", re.DOTALL)
_NEXT_RE = re.compile(r'dependents_after=([^"&]+)"[^>]*>\s*Next\s*<')
_TOTAL_RE = re.compile(r"([\d,]+)\s*Repositories", re.DOTALL)


def _int(match: re.Match[str] | None) -> int | None:
    return int(match.group(1).replace(",", "")) if match else None


def parse_page(html: str) -> tuple[list[dict], str | None]:
    """Return the dependent rows on one page and the cursor of the next page."""
    rows = []
    for chunk in html.split(_ROW_SPLIT)[1:]:
        repo = _REPO_RE.search(chunk)
        if repo is None:
            continue
        rows.append(
            {
                "full_name": repo.group(1),
                "stars": _int(_STARS_RE.search(chunk)),
                "forks": _int(_FORKS_RE.search(chunk)),
            }
        )
    next_cursor = _NEXT_RE.search(html)
    return rows, next_cursor.group(1) if next_cursor else None


def scrape(
    repo: str, out: Path, *, resume: bool, max_pages: int | None, delay: float
) -> list[dict]:
    raw_path, state_path = out / "raw.jsonl", out / "state.json"
    state = (
        json.loads(state_path.read_text())
        if resume and state_path.exists()
        else {"pages": 0, "next": ""}
    )
    if not resume:
        raw_path.write_text("")
    base = f"https://github.com/{repo}/network/dependents?dependent_type=REPOSITORY"

    while state["next"] is not None and (
        max_pages is None or state["pages"] < max_pages
    ):
        url = base + (f"&dependents_after={state['next']}" if state["next"] else "")
        # GitHub intermittently answers 200 with a page carrying neither rows nor a Next
        # link, which is indistinguishable from the last page - so an empty page is
        # retried, and only accepted as the end once it keeps coming back empty.
        for attempt in range(EMPTY_PAGE_RETRIES + 1):
            html = http(url).decode()
            rows, next_cursor = parse_page(html)
            if rows:
                break
            (out / "empty_page.html").write_text(html)
            print(f"  empty page, retry {attempt + 1} ({url})", file=sys.stderr)
            time.sleep(10 * (attempt + 1))
        if not rows and next_cursor is not None:
            raise RuntimeError(
                f"no dependent rows parsed from {url} (saved as empty_page.html): "
                "has GitHub changed the markup?"
            )
        if state["pages"] == 0 and (total := _int(_TOTAL_RE.search(html))) is not None:
            state["total"] = total
        state["next"], state["last_url"] = next_cursor, url
        with raw_path.open("a") as fh:
            fh.writelines(json.dumps(row) + "\n" for row in rows)
        state["pages"] += 1
        state_path.write_text(json.dumps(state))
        print(
            f"  page {state['pages']}: {len(rows)} rows (of ~{state.get('total', '?')})",
            file=sys.stderr,
        )
        time.sleep(delay)

    unique: dict[str, dict] = {}
    for line in raw_path.read_text().splitlines():
        row = json.loads(line)
        unique.setdefault(row["full_name"].lower(), row)
    return list(unique.values())


# --------------------------------------------------------------------------- enrich

_FRAGMENT = """
fragment F on Repository {
  nameWithOwner stargazerCount forkCount isFork isArchived pushedAt description
  primaryLanguage { name }
  parent { nameWithOwner }
  owner {
    __typename login
    ... on Organization { name websiteUrl isVerified }
    ... on User { name company }
  }
}"""


def github_token() -> str:
    token = os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN")
    if token:
        return token
    try:
        return subprocess.run(
            ["gh", "auth", "token"], capture_output=True, text=True, check=True
        ).stdout.strip()
    except (OSError, subprocess.CalledProcessError) as error:
        raise SystemExit(
            "enrichment needs GITHUB_TOKEN, GH_TOKEN or a logged-in gh CLI (or pass --skip-enrich)"
        ) from error


def enrich(rows: list[dict], out: Path) -> dict[str, dict | None]:
    """Look every dependent up via GraphQL; cached by lower-cased ``owner/name``."""
    cache_path = out / "enriched.json"
    cache: dict[str, dict | None] = (
        json.loads(cache_path.read_text()) if cache_path.exists() else {}
    )
    todo = [row["full_name"] for row in rows if row["full_name"].lower() not in cache]
    token = github_token()

    for start in range(0, len(todo), GRAPHQL_BATCH):
        batch = todo[start : start + GRAPHQL_BATCH]
        fields = "\n".join(
            f"r{i}: repository(owner: {json.dumps(name.split('/')[0])}, name: {json.dumps(name.split('/')[1])}) {{ ...F }}"
            for i, name in enumerate(batch)
        )
        query = (
            f"query {{\n{fields}\nrateLimit {{ remaining resetAt }}\n}}\n{_FRAGMENT}"
        )
        body = http(
            GRAPHQL_URL,
            data=json.dumps({"query": query}).encode(),
            headers={
                "Authorization": f"bearer {token}",
                "Content-Type": "application/json",
            },
        )
        answer = json.loads(body)
        data = answer.get("data")
        unexpected = [
            e for e in answer.get("errors", []) if e.get("type") != "NOT_FOUND"
        ]
        if data is None or unexpected:
            raise RuntimeError(f"GraphQL error: {unexpected or answer}")
        for i, name in enumerate(batch):
            cache[name.lower()] = data.get(f"r{i}")
        cache_path.write_text(json.dumps(cache))
        remaining = data["rateLimit"]["remaining"]
        print(
            f"  enriched {min(start + GRAPHQL_BATCH, len(todo))}/{len(todo)} (rate limit left: {remaining})",
            file=sys.stderr,
        )
    return cache


# --------------------------------------------------------------------------- analyse


def match_company(node: dict | None, full_name: str) -> tuple[str, str]:
    """Return ``(company, evidence)``; evidence is ``owner``, ``org`` or ``user``, or both are empty."""
    owner = (node or {}).get("owner") or {"login": full_name.split("/")[0]}
    candidates = [("owner", owner.get("login"))]
    if owner.get("__typename") == "Organization":
        candidates += [("org", owner.get("name")), ("org", owner.get("websiteUrl"))]
    elif owner.get("__typename") == "User":
        candidates.append(("user", owner.get("company")))
    for evidence, text in candidates:
        for company, pattern in _COMPILED_PATTERNS:
            if text and pattern.search(text):
                return company, evidence
    return "", ""


def build_table(rows: list[dict], enriched: dict[str, dict | None]) -> list[dict]:
    table = []
    for row in rows:
        node = enriched.get(row["full_name"].lower())
        owner = (node or {}).get("owner") or {}
        company, evidence = match_company(node, row["full_name"])
        table.append(
            {
                "full_name": (node or {}).get("nameWithOwner") or row["full_name"],
                "stars": node["stargazerCount"] if node else row["stars"],
                "forks": node["forkCount"] if node else row["forks"],
                "owner_type": owner.get("__typename", ""),
                "owner_name": owner.get("name") or "",
                "is_fork": node["isFork"] if node else "",
                "parent": ((node or {}).get("parent") or {}).get("nameWithOwner", ""),
                "archived": node["isArchived"] if node else "",
                "pushed_at": (node or {}).get("pushedAt") or "",
                "language": ((node or {}).get("primaryLanguage") or {}).get("name", ""),
                "company": company,
                "company_evidence": evidence,
                "resolved": node is not None,
                "description": ((node or {}).get("description") or "").replace(
                    "\n", " "
                ),
            }
        )
    table.sort(key=lambda r: r["stars"] or 0, reverse=True)
    return table


def _md_escape(text: str) -> str:
    return text.replace("|", "\\|")


def _link(full_name: str) -> str:
    return f"[{full_name}](https://github.com/{full_name})"


def render_report(
    repo: str, table: list[dict], total_listed: int | None, top: int, enriched: bool
) -> str:
    now = datetime.now(UTC)
    # duplicates across pages account for a few percent; much more means paging ended early
    short = (
        " - **GitHub stops paging near 2,000 entries; the rest of the listed total is unreachable here**"
        if total_listed and len(table) < 0.9 * total_listed
        else ""
    )
    resolved = [r for r in table if r["resolved"]]
    originals = [r for r in table if r["is_fork"] is not True]
    active = [
        r
        for r in resolved
        if r["pushed_at"]
        and now - datetime.fromisoformat(r["pushed_at"]) <= ACTIVE_WITHIN
    ]
    owner_types = Counter(r["owner_type"] for r in resolved)
    lines = [
        f"# Dependents of {repo}",
        "",
        f"Generated {now:%Y-%m-%d %H:%M} UTC.",
        "",
        f"- GitHub lists: {total_listed if total_listed is not None else 'unknown'} repositories",
        f"- scraped (unique): {len(table)}{short}",
    ]
    if enriched:
        lines += [
            f"- still resolvable: {len(resolved)} ({len(table) - len(resolved)} deleted, renamed away or private)",
            f"- forks: {sum(r['is_fork'] is True for r in resolved)}, archived: {sum(r['archived'] is True for r in resolved)}",
            f"- owners: {owner_types.get('Organization', 0)} organisations, {owner_types.get('User', 0)} users",
            f"- pushed within {ACTIVE_WITHIN.days} days: {len(active)}",
            f"- with >= 10 stars: {sum((r['stars'] or 0) >= 10 for r in originals)}, "
            f">= 100 stars: {sum((r['stars'] or 0) >= 100 for r in originals)} (forks excluded)",
        ]

    lines += ["", f"## Top {top} by stars (forks excluded)", ""]
    lines += [
        "| # | Repository | Stars | Owner | Language | Last push | Company |",
        "|---|---|---:|---|---|---|---|",
    ]
    for rank, r in enumerate(originals[:top], 1):
        archived = " (archived)" if r["archived"] is True else ""
        lines.append(
            f"| {rank} | {_link(r['full_name'])}{archived} | {r['stars']} | {r['owner_type']} | {r['language']} "
            f"| {r['pushed_at'][:10]} | {r['company']} |"
        )

    by_company: dict[str, list[dict]] = defaultdict(list)
    for r in table:
        if r["company"]:
            by_company[r["company"]].append(r)
    lines += ["", "## Companies", ""]
    lines += [
        "Evidence: `owner` = the owner login matches, `org` = the organisation's name or website matches, "
        "`user` = a personal account's profile names the company (weak).",
        "",
        "| Company | Repos | Stars | Repositories (evidence) |",
        "|---|---:|---:|---|",
    ]
    ordered = sorted(
        by_company.items(), key=lambda kv: (-sum(r["stars"] or 0 for r in kv[1]), kv[0])
    )
    for company, repos in ordered:
        listed = ", ".join(
            f"{_link(r['full_name'])} {r['stars']}★ `{r['company_evidence']}`{' fork' if r['is_fork'] is True else ''}"
            for r in repos
        )
        lines.append(
            f"| {company} | {len(repos)} | {sum(r['stars'] or 0 for r in repos)} | {listed} |"
        )

    if enriched:
        by_org: dict[str, list[dict]] = defaultdict(list)
        for r in table:
            if r["owner_type"] == "Organization":
                by_org[r["full_name"].split("/")[0]].append(r)
        lines += ["", f"## Organisations ({len(by_org)})", ""]
        lines += [
            "Every organisation owning a dependent, most starred first.",
            "",
            "| Organisation | Name | Repos | Stars | Most starred repository | Company |",
            "|---|---|---:|---:|---|---|",
        ]
        ranked = sorted(
            by_org.items(),
            key=lambda kv: (-sum(r["stars"] or 0 for r in kv[1]), kv[0].lower()),
        )
        for login, repos in ranked:
            best = max(repos, key=lambda r: r["stars"] or 0)
            lines.append(
                f"| [{login}](https://github.com/{login}) | {_md_escape(best['owner_name'])} | {len(repos)} "
                f"| {sum(r['stars'] or 0 for r in repos)} | {_link(best['full_name'])} | {best['company']} |"
            )

    if enriched:
        languages = Counter(r["language"] or "(none)" for r in resolved).most_common(10)
        lines += ["", "## Languages", "", "| Language | Repos |", "|---|---:|"]
        lines += [f"| {_md_escape(name)} | {count} |" for name, count in languages]
    return "\n".join(lines) + "\n"


# --------------------------------------------------------------------------- main


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.split("\n", 1)[0])
    parser.add_argument(
        "--repo", default=DEFAULT_REPO, help="owner/name (default: %(default)s)"
    )
    parser.add_argument(
        "--out",
        type=Path,
        help="output directory (default: tmp/dependents/<owner>_<name>)",
    )
    parser.add_argument(
        "--resume",
        action="store_true",
        help="continue an interrupted scrape and reuse its cache",
    )
    parser.add_argument(
        "--max-pages",
        type=int,
        help="stop scraping after this many pages (30 rows each)",
    )
    parser.add_argument(
        "--delay",
        type=float,
        default=1.0,
        help="seconds between page requests (default: %(default)s)",
    )
    parser.add_argument(
        "--skip-enrich",
        action="store_true",
        help="report on scraped stars only, without GraphQL",
    )
    parser.add_argument(
        "--top",
        type=int,
        default=50,
        help="rows in the most-starred table (default: %(default)s)",
    )
    args = parser.parse_args()

    out = args.out or OUT_ROOT / args.repo.replace("/", "_")
    out.mkdir(parents=True, exist_ok=True)
    if not args.resume:
        for stale in ("state.json", "enriched.json"):
            (out / stale).unlink(missing_ok=True)

    print(f"scraping dependents of {args.repo} into {out}", file=sys.stderr)
    rows = scrape(
        args.repo, out, resume=args.resume, max_pages=args.max_pages, delay=args.delay
    )
    total_listed = json.loads((out / "state.json").read_text()).get("total")

    enriched: dict[str, dict | None] = {}
    if not args.skip_enrich:
        print(f"enriching {len(rows)} dependents via GraphQL", file=sys.stderr)
        enriched = enrich(rows, out)

    table = build_table(rows, enriched)
    with (out / "dependents.csv").open("w", newline="") as fh:
        writer = csv.DictWriter(
            fh, fieldnames=list(table[0]) if table else ["full_name"]
        )
        writer.writeheader()
        writer.writerows(table)
    report = render_report(
        args.repo, table, total_listed, args.top, enriched=not args.skip_enrich
    )
    (out / "report.md").write_text(report)
    print(report)
    print(f"wrote {out / 'dependents.csv'} and {out / 'report.md'}", file=sys.stderr)


if __name__ == "__main__":
    main()
