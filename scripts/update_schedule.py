#!/usr/bin/env python3
"""
Fetches AAT's berthing schedule page, downloads the current Appleton
Dock and Webb Dock West PDFs into docs/, renders each page to a PNG,
and rewrites docs/index.html to show the images.

Images are used because mobile browsers won't draw PDFs inside a web
page - images display on every device and can be pinch-zoomed.
"""

import datetime
import sys
from pathlib import Path
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup
import pypdfium2 as pdfium

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
RENDER_SCALE = 2.5  # higher = sharper when zoomed, bigger files


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
        low = a.get_text(" ", strip=True).lower()
        if "berth" not in low:
            continue
        if "appleton" in low and appleton is None:
            appleton = href
        elif ("webb" in low or "wdw" in low) and webb is None:
            webb = href

    if not appleton or not webb:
        missing = [n for n, v in (("Appleton Dock", appleton), ("Webb Dock West", webb)) if not v]
        raise RuntimeError(
            f"Could not find current PDF link(s) for: {', '.join(missing)}. "
            "AAT may have changed their page layout - check SOURCE_URL manually."
        )
    return appleton, webb


def download_pdf(url, dest_name):
    resp = requests.get(url, headers=HEADERS, timeout=60)
    resp.raise_for_status()
    data = resp.content
    if not data.startswith(b"%PDF"):
        raise RuntimeError(f"{url} did not return a PDF (got {len(data)} bytes).")
    DOCS_DIR.mkdir(parents=True, exist_ok=True)
    (DOCS_DIR / dest_name).write_bytes(data)
    print(f"Saved {dest_name} ({len(data):,} bytes)")


def render_pages(pdf_name):
    """Render every page of the PDF to PNG. Returns the image filenames."""
    stem = Path(pdf_name).stem
    for old in DOCS_DIR.glob(f"{stem}-p*.png"):
        old.unlink()
    pdf = pdfium.PdfDocument(str(DOCS_DIR / pdf_name))
    names = []
    for i in range(len(pdf)):
        name = f"{stem}-p{i + 1}.png"
        pdf[i].render(scale=RENDER_SCALE).to_pil().save(DOCS_DIR / name, optimize=True)
        names.append(name)
    pdf.close()
    print(f"Rendered {pdf_name} -> {', '.join(names)}")
    return names


def img_tags(names, version, alt):
    return "\n".join(
        f'<a href="{n}?v={version}" target="_blank" rel="noopener">'
        f'<img src="{n}?v={version}" alt="{alt} page {i + 1}" loading="lazy"></a>'
        for i, n in enumerate(names)
    )


def render_html(appleton_source, webb_source, appleton_imgs, webb_imgs):
    now = datetime.datetime.now(datetime.timezone.utc)
    stamp = now.strftime("%d %b %Y, %H:%M UTC")
    version = now.strftime("%Y%m%d%H%M")  # cache-buster so phones fetch fresh images

    html = (
        TEMPLATE_PATH.read_text(encoding="utf-8")
        .replace("{{APPLETON_IMAGES}}", img_tags(appleton_imgs, version, "Appleton Dock schedule"))
        .replace("{{WEBB_IMAGES}}", img_tags(webb_imgs, version, "Webb Dock West schedule"))
        .replace("{{APPLETON_PDF}}", f"{APPLETON_PDF}?v={version}")
        .replace("{{WEBB_PDF}}", f"{WEBB_PDF}?v={version}")
        .replace("{{APPLETON_SOURCE}}", appleton_source)
        .replace("{{WEBB_SOURCE}}", webb_source)
        .replace("{{UPDATED_STAMP}}", stamp)
    )
    OUTPUT_PATH.write_text(html, encoding="utf-8")


def main():
    try:
        appleton_url, webb_url = fetch_links()
        download_pdf(appleton_url, APPLETON_PDF)
        download_pdf(webb_url, WEBB_PDF)
        appleton_imgs = render_pages(APPLETON_PDF)
        webb_imgs = render_pages(WEBB_PDF)
    except Exception as exc:  # noqa: BLE001
        print(f"ERROR: {exc}", file=sys.stderr)
        sys.exit(1)

    render_html(appleton_url, webb_url, appleton_imgs, webb_imgs)
    print(f"Appleton source: {appleton_url}")
    print(f"Webb Dock West source: {webb_url}")
    print("docs/index.html updated.")


if __name__ == "__main__":
    main()
