from typing import Annotated
from urllib.parse import quote_plus

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