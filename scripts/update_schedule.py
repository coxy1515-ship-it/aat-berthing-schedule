#!/usr/bin/env python3
"""
Fetches AAT's berthing schedule page, downloads the current Appleton
Dock and Webb Dock West PDFs into docs/, and rewrites docs/index.html
to display our own copies.

Serving the PDFs ourselves (rather than hotlinking or routing through
Google's viewer) means no third-party viewer to fail and no
cross-origin framing restrictions.
"""

import datetime
import re
import sys
from pathlib import Path
from urllib.parse import urljoin

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
DOCS_DIR = ROOT / "docs"
OUTPUT_PATH = DOCS_DIR / "index.html"

APPLETON_PDF = "appleton-dock.pdf"
WEBB_PDF = "webb-dock-west.pdf"


def fetch_links():
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


def download_pdf(url, dest_name):
    resp = requests.get(url, headers=HEADERS, timeout=60)
    resp.raise_for_status()
    data = resp.content
    if not data.startswith(b"%PDF"):
        raise RuntimeError(f"{url} did not return a PDF (got {len(data)} bytes).")
    DOCS_DIR.mkdir(parents=True, exist_ok=True)
    (DOCS_DIR / dest_name).write_bytes(data)
    print(f"Saved {dest_name} ({len(data):,} bytes)")


def render(appleton_source, webb_source):
    template = TEMPLATE_PATH.read_text(encoding="utf-8")
    stamp = datetime.datetime.now(datetime.timezone.utc).strftime("%d %b %Y, %H:%M UTC")

    html = (
        template.replace("{{APPLETON_PDF}}", APPLETON_PDF)
        .replace("{{WEBB_PDF}}", WEBB_PDF)
        .replace("{{APPLETON_SOURCE}}", appleton_source)
        .replace("{{WEBB_SOURCE}}", webb_source)
        .replace("{{UPDATED_STAMP}}", stamp)
    )
    OUTPUT_PATH.write_text(html, encoding="utf-8")


def main():
    try:
        appleton_url, _, webb_url, _ = fetch_links()
        download_pdf(appleton_url, APPLETON_PDF)
        download_pdf(webb_url, WEBB_PDF)
    except Exception as exc:  # noqa: BLE001
        print(f"ERROR: {exc}", file=sys.stderr)
        sys.exit(1)

    render(appleton_url, webb_url)
    print(f"Appleton source: {appleton_url}")
    print(f"Webb Dock West source: {webb_url}")
    print("docs/index.html updated.")


if __name__ == "__main__":
    main()
