#!/usr/bin/env python3
"""Build the whole site from Markdown sources (single source of truth).

Usage:  python3 build.py

Pages (edit the .md, never the generated .html):
    index.md     -> index.html            (landing page)
    projects.md  -> projects/index.html
    cv.md        -> cv/index.html + cv/tomas-xavier-santos-cv.pdf

The landing page's `{{ projects }}` marker is replaced with an
auto-generated list of the `## headings` found in projects.md.
"""
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).parent
TEMPLATE = ROOT / "templates" / "site-template.html"
PDF_NAME = "tomas-xavier-santos-cv.pdf"

# source -> output page
PAGES = {
    "index.md": Path("index.html"),
    "projects.md": Path("projects/index.html"),
    "cv.md": Path("cv/index.html"),
}


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
    """Convert markdown to an HTML fragment using pandoc."""
    result = subprocess.run(
        ["pandoc", "--from", "markdown", "--to", "html"],
        input=markdown_text, capture_output=True, text=True, check=True,
    )
    return result.stdout


def project_links(projects_body):
    """Extract `## heading` titles from projects.md as a linked HTML list."""
    items = []
    for heading in re.findall(r"^## (.+)$", projects_body, flags=re.M):
        slug = re.sub(r"[^a-z0-9 -]", "", heading.lower()).replace(" ", "-")
        items.append(f'<li><a href="projects/#{slug}">{heading}</a></li>')
    return "<ul>\n" + "\n".join(items) + "\n</ul>"


def render(template, meta, content_html, extra=None):
    html = template
    for key, value in meta.items():
        html = html.replace("{{ " + key + " }}", value)
    html = html.replace("{{ content }}", content_html)
    html = html.replace("{{ pdf_name }}", PDF_NAME)
    # nav active state: {{ nav_cv }} etc. -> ' class="active"' on current page
    page = meta.get("page", "")
    for nav in ("home", "projects", "cv"):
        html = html.replace("{{ nav_" + nav + " }}",
                            ' class="active"' if nav == page else "")
    for key, value in (extra or {}).items():
        # pandoc wraps the lone marker in a paragraph; replace it wholesale
        html = html.replace("<p>{{ " + key + " }}</p>", value)
        html = html.replace("{{ " + key + " }}", value)
    return html


def main():
    template = TEMPLATE.read_text(encoding="utf-8")

    projects_body = parse_front_matter(
        (ROOT / "projects.md").read_text(encoding="utf-8"))[1]

    for source, out in PAGES.items():
        meta, body = parse_front_matter(
            (ROOT / source).read_text(encoding="utf-8"))
        content_html = md_to_html(body)
        extra = {}
        if source == "index.md":
            extra["projects"] = project_links(projects_body)
        html = render(template, meta, content_html, extra)

        out_path = ROOT / out
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(html, encoding="utf-8")
        print(f"built {out_path}")

        if source == "cv.md":
            pdf = out_path.parent / PDF_NAME
            subprocess.run(
                [sys.executable, "-m", "weasyprint", str(out_path), str(pdf)],
                check=True)
            print(f"built {pdf}")


if __name__ == "__main__":
    main()
