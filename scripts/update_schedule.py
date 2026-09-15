#!/usr/bin/env python3
"""
Fetches AAT's berthing schedule resource page, finds the current
Appleton Dock and Webb Dock West PDF links, and rewrites docs/index.html
to embed whatever the two current PDFs are.

This does NOT download or parse the PDFs themselves - it just finds
today's PDF URLs and points a couple of <iframe>s at them, so the page
always shows whatever AAT currently has published, in AAT's own format.

Run manually:  python scripts/update_schedule.py
Run on a schedule via .github/workflows/update.yml
"""

import datetime
import re
import sys
from pathlib import Path
from urllib.parse import urljoin, quote

import requests
from bs4 import BeautifulSoup

SOURCE_URL = (
    "https://www.aaterminals.com.au/resource/"
    "?dc=berthingschedules&loc=appletondock%2Cwebbdockwest"
)
HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
    )
}

ROOT = Path(__file__).resolve().parent.parent
TEMPLATE_PATH = ROOT / "scripts" / "template.html"
OUTPUT_PATH = ROOT / "docs" / "index.html"

DATE_RE = re.compile(r"\d{1,2}[./]\d{1,2}[./]\d{2,4}")


def fetch_links():
    """Return (appleton_url, appleton_label, webb_url, webb_label)."""
    resp = requests.get(SOURCE_URL, headers=HEADERS, timeout=30)
    resp.raise_for_status()
    soup = BeautifulSoup(resp.text, "html.parser")

    appleton = None
    webb = None

    for a in soup.find_all("a", href=True):
        href = urljoin(SOURCE_URL, a["href"])
        if not href.lower().endswith(".pdf"):
            continue
        text = a.get_text(" ", strip=True)
        low = text.lower()
        if "berth" not in low:
            # Only interested in berthing schedule links
            continue
        if "appleton" in low and appleton is None:
            appleton = (href, text)
        elif ("webb" in low or "wdw" in low) and webb is None:
            webb = (href, text)

    if not appleton or not webb:
        missing = []
        if not appleton:
            missing.append("Appleton Dock")
        if not webb:
            missing.append("Webb Dock West")
        raise RuntimeError(
            f"Could not find current PDF link(s) for: {', '.join(missing)}. "
            "AAT may have changed their page layout - check SOURCE_URL manually."
        )

    return appleton[0], appleton[1], webb[0], webb[1]


def render(appleton_url, appleton_label, webb_url, webb_label):
    template = TEMPLATE_PATH.read_text(encoding="utf-8")
    now = datetime.datetime.now(datetime.timezone.utc)
    stamp = now.strftime("%d %b %Y, %H:%M UTC")

    def embed_url(pdf_url):
        # AAT's server blocks its PDFs from being iframed directly
        # (X-Frame-Options), so route through Google's viewer instead,
        # which fetches and renders the PDF itself.
        return "https://docs.google.com/viewer?embedded=true&url=" + quote(
            pdf_url, safe=""
        )

    html = (
        template.replace("{{APPLETON_URL}}", appleton_url)
        .replace("{{APPLETON_EMBED_URL}}", embed_url(appleton_url))
        .replace("{{APPLETON_LABEL}}", appleton_label)
        .replace("{{WEBB_URL}}", webb_url)
        .replace("{{WEBB_EMBED_URL}}", embed_url(webb_url))
        .replace("{{WEBB_LABEL}}", webb_label)
        .replace("{{UPDATED_STAMP}}", stamp)
    )
    OUTPUT_PATH.write_text(html, encoding="utf-8")


def main():
    try:
        appleton_url, appleton_label, webb_url, webb_label = fetch_links()
    except Exception as exc:  # noqa: BLE001
        print(f"ERROR: {exc}", file=sys.stderr)
        sys.exit(1)

    render(appleton_url, appleton_label, webb_url, webb_label)
    print(f"Appleton: {appleton_url}")
    print(f"Webb Dock West: {webb_url}")
    print("docs/index.html updated.")


if __name__ == "__main__":
    main()


