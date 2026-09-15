import asyncio
import json
import re
from typing import Annotated
from urllib.parse import parse_qs, quote_plus, unquote, urlparse

import httpx
from agents import function_tool
from pydantic import Field


@function_tool
async def search_web(
    query: Annotated[str, Field(min_length=3, max_length=300)],
) -> str:
    """Search the public web and return result titles, URLs, and snippets.

    Use this only for public business discovery. Do not bypass authentication,
    robots controls, or platform restrictions.
    """
    url = f"https://html.duckduckgo.com/html/?q={quote_plus(query)}"
    headers = {"User-Agent": "TheSocialGirlSalesAgent/0.1 (+research)"}
    try:
        async with httpx.AsyncClient(timeout=20, follow_redirects=True) as client:
            response = await client.get(url, headers=headers)
            response.raise_for_status()
    except httpx.HTTPError as exc:
        return f"Search unavailable: {exc.__class__.__name__}"

    from bs4 import BeautifulSoup

    soup = BeautifulSoup(response.text, "html.parser")
    results: list[str] = []
    for result in soup.select(".result")[:10]:
        title = result.select_one(".result__title")
        link = result.select_one(".result__a")
        snippet = result.select_one(".result__snippet")
        if title and link:
            results.append(f"{title.get_text(' ', strip=True)} | {link.get('href', '')} | {snippet.get_text(' ', strip=True) if snippet else ''}")
    return "\n".join(results) or "No public results found."


@function_tool
async def fetch_public_website(
    url: Annotated[str, Field(min_length=8, max_length=500)],
) -> str:
    """Fetch readable text from one public HTTP(S) business website."""
    if not url.startswith(("http://", "https://")):
        return "Rejected: only HTTP(S) URLs are supported."
    try:
        async with httpx.AsyncClient(timeout=20, follow_redirects=True) as client:
            response = await client.get(url, headers={"User-Agent": "TheSocialGirlSalesAgent/0.1 (+research)"})
            response.raise_for_status()
    except httpx.HTTPError as exc:
        return f"Website unavailable: {exc.__class__.__name__}"

    from bs4 import BeautifulSoup

    text = BeautifulSoup(response.text, "html.parser").get_text(" ", strip=True)
    return text[:12000]


async def _fetch_candidate(candidate: dict[str, str]) -> dict[str, object]:
    text = await fetch_public_website.__wrapped__(candidate["url"])
    emails = sorted(set(re.findall(r"[\w.+-]+@[\w-]+\.[\w.-]+", text, flags=re.IGNORECASE)))

    instagram_match = re.search(r"https?://(?:www\.)?instagram\.com/[\w.-]+/?", text, flags=re.IGNORECASE)
    linkedin_match = re.search(r"https?://(?:www\.)?linkedin\.com/(?:in|company)/[\w.-]+/?", text, flags=re.IGNORECASE)
    facebook_match = re.search(r"https?://(?:www\.)?facebook\.com/[\w.-]+/?", text, flags=re.IGNORECASE)
    maps_match = re.search(r"https?://(?:www\.)?google\.com/maps/[^\s\"']+", text, flags=re.IGNORECASE)

    clean_url = lambda m: m.group(0).rstrip(".,;") if m else None

    return {
        **candidate,
        "email": emails[0] if emails else None,
        "instagram": clean_url(instagram_match) or candidate.get("instagram"),
        "linkedin": clean_url(linkedin_match) or candidate.get("linkedin"),
        "facebook": clean_url(facebook_match) or candidate.get("facebook"),
        "google_maps": clean_url(maps_match) or candidate.get("google_maps"),
        "website_text": text[:4000],
    }


def build_discovery_queries(niche: str, location: str, country: str) -> list[dict[str, str]]:
    """Construct PDF-aligned search patterns."""
    return [
        {"query": f"{location} {niche} official website social media", "purpose": "Primary business discovery"},
        {"query": f"{location} {niche} business contact email", "purpose": "Contact & email discovery"},
        {"query": f"{location} {niche} hiring expansion growth", "purpose": "Growth signal discovery"},
        {"query": f"{location} {niche} {country} instagram linkedin facebook", "purpose": "Social profile discovery"},
    ]


@function_tool
async def collect_campaign_evidence(
    niche: Annotated[str, Field(min_length=2, max_length=120)],
    location: Annotated[str, Field(min_length=2, max_length=120)],
    country: Annotated[str, Field(min_length=2, max_length=120)],
    requested_leads: Annotated[int, Field(ge=1, le=100)],
) -> str:
    """Run bounded public-web discovery and return evidence for the research agent.

    This tool owns search and fetching limits so the model cannot loop through
    one search or candidate indefinitely.
    """
    plan = build_discovery_queries(niche, location, country)
    search_results = await asyncio.gather(*(search_web.__wrapped__(item["query"]) for item in plan))

    candidates: dict[str, dict[str, str]] = {}
    url_pattern = re.compile(r"(?:https?:)?//[^\s|]+")
    queries_recorded: list[dict[str, object]] = []

    for item, result_text in zip(plan, search_results):
        found_in_query = 0
        for line in result_text.splitlines():
            urls = url_pattern.findall(line)
            if not urls:
                continue
            url = urls[0].rstrip(".,)")
            if url.startswith("//"):
                url = f"https:{url}"
            parsed = urlparse(url)
            redirect_target = parse_qs(parsed.query).get("uddg", [None])[0]
            url = unquote(redirect_target) if redirect_target else url
            parsed = urlparse(url)
            domain = parsed.netloc.lower().removeprefix("www.")
            if domain not in {"html.duckduckgo.com", "duckduckgo.com"}:
                found_in_query += 1
                entry = candidates.setdefault(domain, {"name": line.split(" | ", 1)[0][:200], "url": url})
                if "instagram.com" in domain:
                    entry["instagram"] = url
                elif "linkedin.com" in domain:
                    entry["linkedin"] = url
                elif "facebook.com" in domain:
                    entry["facebook"] = url
        queries_recorded.append({
            "provider": "duckduckgo",
            "query": item["query"],
            "purpose": item["purpose"],
            "result_count": found_in_query,
        })

    selected = list(candidates.values())[: min(max(requested_leads + 5, 10), 15)]
    evidence = await asyncio.gather(*(_fetch_candidate(candidate) for candidate in selected), return_exceptions=True)
    usable = [item for item in evidence if isinstance(item, dict)]
    return json.dumps({"candidates": usable, "queries": queries_recorded}, ensure_ascii=True)