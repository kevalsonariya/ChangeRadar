"""Scraper service using HTTPX and BeautifulSoup to extract readable text content."""

import httpx
from bs4 import BeautifulSoup
from typing import Tuple, Optional

DEFAULT_HEADERS = {
    "User-Agent": "ChangeRadar/0.1 (Webpage Content Monitor; College Project MVP)",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8"
}

async def fetch_webpage_content(url: str, selector: Optional[str] = None) -> Tuple[bool, str, str]:
    """
    Fetch webpage HTML using HTTPX and extract normalized clean text using BeautifulSoup.
    Returns: (success: bool, clean_text: str, error_message: str)
    """
    try:
        async with httpx.AsyncClient(headers=DEFAULT_HEADERS, timeout=15.0, follow_redirects=True) as client:
            response = await client.get(url)
            response.raise_for_status()
            html = response.text

        soup = BeautifulSoup(html, "html.parser")

        # Remove irrelevant non-content tags
        for element in soup(["script", "style", "noscript", "svg", "header", "footer"]):
            element.decompose()

        if selector:
            target_el = soup.select_one(selector)
            if target_el:
                soup = target_el

        # Extract text and normalize whitespace
        lines = [line.strip() for line in soup.get_text(separator="\n").splitlines()]
        clean_text = "\n".join(line for line in lines if line)
        return True, clean_text, ""
    except Exception as exc:
        return False, "", str(exc)
