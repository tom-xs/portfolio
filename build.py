#!/usr/bin/env python3
"""Build the CV web page and PDF from cv.md (single source of truth).

Usage:  python3 build.py
Output: cv/index.html  and  cv/tomas-xavier-santos-cv.pdf
"""
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).parent
CV_MD = ROOT / "cv.md"
TEMPLATE = ROOT / "templates" / "cv-template.html"
OUT_DIR = ROOT / "cv"
PDF_NAME = "tomas-xavier-santos-cv.pdf"


def parse_front_matter(text):
    """Split simple `key: value` front matter from the markdown body."""
    meta = {}
    body = text
    if text.startswith("---"):
        _, fm, body = text.split("---", 2)
        for line in fm.strip().splitlines():
            if ":" in line:
                key, value = line.split(":", 1)
                meta[key.strip()] = value.strip()
    return meta, body.strip()


def md_to_html(markdown_text):
    """Convert markdown body to an HTML fragment using pandoc."""
    result = subprocess.run(
        ["pandoc", "--from", "markdown", "--to", "html"],
        input=markdown_text, capture_output=True, text=True, check=True,
    )
    return result.stdout


def main():
    meta, body = parse_front_matter(CV_MD.read_text(encoding="utf-8"))
    content_html = md_to_html(body)

    template = TEMPLATE.read_text(encoding="utf-8")
    html = template
    for key, value in meta.items():
        html = html.replace("{{ " + key + " }}", value)
    html = html.replace("{{ content }}", content_html)
    html = html.replace("{{ pdf_name }}", PDF_NAME)

    OUT_DIR.mkdir(exist_ok=True)
    page = OUT_DIR / "index.html"
    page.write_text(html, encoding="utf-8")
    print(f"built {page}")

    pdf = OUT_DIR / PDF_NAME
    subprocess.run(
        [sys.executable, "-m", "weasyprint", str(page), str(pdf)],
        check=True,
    )
    print(f"built {pdf}")


if __name__ == "__main__":
    main()
