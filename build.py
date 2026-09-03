#!/usr/bin/env python3
"""Build the whole site from Markdown sources (single source of truth).

Usage:
    python3 build.py
    python3 build.py --template templates/site-template.html --output dist
    python3 build.py --watch

Pages (edit the .md, never the generated .html):
    index.md       -> index.html            (landing page)
    projects.md    -> projects/index.html
    blog.md        -> blog/index.html       (auto-generated post index)
    posts/*.md     -> blog/<slug>/index.html
    cv.md          -> cv/index.html + cv/tomas-xavier-santos-cv.pdf

Notes:
- The landing page's `{{ projects }}` marker is replaced with an
  auto-generated list of the `## headings` found in projects.md.
- Each file in posts/ is one blog post; the filename (without .md) is the
  URL slug, and `title:` / `date:` front matter is required. The blog
  index's `{{ posts }}` marker is replaced with an auto-generated list of
  linked post titles + dates, newest first.
- The CV gets a print-only text header (name + contact) generated from
  the cv.md front matter, so the PDF is ATS-friendly while the web page
  keeps the spec-table header. Contact values are real clickable links
  in the PDF (mailto:, tel:, https:) rendered as plain black text.
"""
import argparse
import logging
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).parent
PDF_NAME = "tomas-xavier-santos-cv.pdf"

# source -> output page (paths are resolved against --output at build time)
PAGES = {
    "index.md": Path("index.html"),
    "projects.md": Path("projects/index.html"),
    "blog.md": Path("blog/index.html"),
    "cv.md": Path("cv/index.html"),
}

# nav link ids that get a `{{ nav_<id> }}` -> ' class="active"' substitution;
# must match the `page:` front-matter value and the `{{ nav_<id> }}` markers
# used in templates/site-template.html
NAV_PAGES = ("home", "projects", "blog", "cv")

# order of the contact fields in the PDF header
CONTACT_ORDER = ("location", "email", "phone", "website", "linkedin", "github")

# one file per blog post; filename stem becomes the URL slug
POSTS_DIR = ROOT / "posts"

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
log = logging.getLogger("build")


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
    for heading in re.findall(r"^## (.+)$", projects_body, flags=re.MULTILINE):
        slug = re.sub(r"[^a-z0-9 -]", "", heading.lower()).replace(" ", "-")
        items.append(f'<li><a href="projects/#{slug}">{heading}</a></li>')
    return "<ul>\n" + "\n".join(items) + "\n</ul>"


def read_posts():
    """Parse every posts/*.md file into (slug, meta, body), newest first.

    Raises ValueError if a post is missing required `title`/`date`.
    """
    posts = []
    if not POSTS_DIR.is_dir():
        return posts
    for path in sorted(POSTS_DIR.glob("*.md")):
        meta, body = parse_front_matter(path.read_text(encoding="utf-8"))
        for key in ("title", "date"):
            if not meta.get(key):
                raise ValueError(f"{path.name}: missing required `{key}:` "
                                 "front matter")
        posts.append((path.stem, meta, body))
    # ISO dates sort lexicographically; newest first
    posts.sort(key=lambda p: p[1]["date"], reverse=True)
    return posts


def post_index(posts):
    """Blog index fragment: linked post titles + posted dates.

    Links are relative to blog/ (where the index page lives).
    """
    if not posts:
        return "<p>no posts yet.</p>"
    items = [
        f'<li><a href="{slug}/">{meta["title"]}</a> — {meta["date"]}</li>'
        for slug, meta, _ in posts
    ]
    return "<ul>\n" + "\n".join(items) + "\n</ul>"


def contact_href(key, value):
    """Return the clickable href for a contact field, or None."""
    if key == "email":
        return f"mailto:{value}"
    if key == "phone":
        return "tel:" + re.sub(r"[^+\d]", "", value)
    if key in ("website", "linkedin", "github"):
        return value if value.startswith("http") else f"https://{value}"
    return None


def cv_print_header(meta):
    """Plain-text name + contact header, visible in the PDF only."""
    parts = []
    for key in CONTACT_ORDER:
        value = meta.get(key, "")
        if not value:
            continue
        href = contact_href(key, value)
        parts.append(f'<a href="{href}">{value}</a>' if href else value)
    contact = " | ".join(parts)
    return (
        '<div class="print-only">'
        f'<h1 class="cv-name">{meta.get("name", "")}</h1>'
        f'<p class="cv-contact">{contact}</p>'
        "</div>"
    )


def render(template, meta, content_html, extra=None):
    html = template
    for key, value in meta.items():
        html = html.replace("{{ " + key + " }}", value)
    html = html.replace("{{ content }}", content_html)
    html = html.replace("{{ pdf_name }}", PDF_NAME)
    # nav active state: {{ nav_cv }} etc. -> ' class="active"' on current page
    page = meta.get("page", "")
    for nav in NAV_PAGES:
        html = html.replace("{{ nav_" + nav + " }}",
                            ' class="active"' if nav == page else "")
    for key, value in (extra or {}).items():
        # pandoc wraps the lone marker in a paragraph; replace it wholesale
        html = html.replace("<p>{{ " + key + " }}</p>", value)
        html = html.replace("{{ " + key + " }}", value)
    return html


def build(template_path, output_dir):
    """Run one full build pass. Raises on unrecoverable errors."""
    try:
        template = template_path.read_text(encoding="utf-8")
    except FileNotFoundError:
        log.error("template not found: %s", template_path)
        raise

    try:
        projects_body = parse_front_matter(
            (ROOT / "projects.md").read_text(encoding="utf-8"))[1]
    except FileNotFoundError:
        log.error("projects.md not found (required for the project list)")
        raise

    try:
        posts = read_posts()
    except ValueError as e:
        log.error("%s", e)
        raise

    # individual blog post pages: posts/<slug>.md -> blog/<slug>/index.html
    for slug, meta, body in posts:
        try:
            post_html = md_to_html(body)
        except subprocess.CalledProcessError as e:
            log.error("pandoc failed on posts/%s.md: %s", slug, e.stderr.strip())
            raise
        html = render(template, meta, post_html)
        post_out = output_dir / "blog" / slug / "index.html"
        post_out.parent.mkdir(parents=True, exist_ok=True)
        post_out.write_text(html, encoding="utf-8")
        print(f"built {post_out}")

    for source, out in PAGES.items():
        source_path = ROOT / source
        if not source_path.exists():
            log.warning("skipping %s: file not found", source)
            continue

        meta, body = parse_front_matter(source_path.read_text(encoding="utf-8"))

        try:
            content_html = md_to_html(body)
        except subprocess.CalledProcessError as e:
            log.error("pandoc failed on %s: %s", source, e.stderr.strip())
            raise
        except FileNotFoundError:
            log.error("pandoc not found on PATH -- install it and retry")
            raise

        extra = {}
        if source == "index.md":
            extra["projects"] = project_links(projects_body)
        if source == "blog.md":
            extra["posts"] = post_index(posts)
        if source == "cv.md":
            content_html = cv_print_header(meta) + content_html

        html = render(template, meta, content_html, extra)

        out_path = output_dir / out
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(html, encoding="utf-8")
        print(f"built {out_path}")

        if source == "cv.md":
            pdf = out_path.parent / PDF_NAME
            try:
                subprocess.run(
                    [sys.executable, "-m", "weasyprint", str(out_path), str(pdf)],
                    check=True, capture_output=True, text=True,
                )
            except subprocess.CalledProcessError as e:
                log.error("weasyprint failed on %s: %s", out_path, e.stderr.strip())
                raise
            except FileNotFoundError:
                log.error("weasyprint not installed -- `pip install weasyprint`")
                raise
            print(f"built {pdf}")


def parse_args():
    parser = argparse.ArgumentParser(description="Build the portfolio site.")
    parser.add_argument(
        "--template", default=str(ROOT / "templates" / "site-template.html"),
        help="path to the HTML template (default: templates/site-template.html)")
    parser.add_argument(
        "--output", default=str(ROOT),
        help="output directory for generated files (default: repo root)")
    parser.add_argument(
        "--watch", action="store_true",
        help="rebuild automatically when .md or template files change "
             "(requires the optional `watchdog` package)")
    return parser.parse_args()


def watch(template_path, output_dir):
    try:
        from watchdog.events import FileSystemEventHandler
        from watchdog.observers import Observer
    except ImportError:
        log.error("--watch requires the `watchdog` package: pip install watchdog")
        sys.exit(1)

    import time

    class RebuildHandler(FileSystemEventHandler):
        def on_modified(self, event):
            if event.is_directory:
                return
            if event.src_path.endswith((".md", ".html")):
                log.info("change detected (%s), rebuilding...", event.src_path)
                try:
                    build(template_path, output_dir)
                except (OSError, subprocess.CalledProcessError):
                    log.error("build failed, waiting for next change")

    build(template_path, output_dir)
    observer = Observer()
    observer.schedule(RebuildHandler(), str(ROOT), recursive=True)
    observer.start()
    log.info("watching for changes (Ctrl+C to stop)...")
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        observer.stop()
    observer.join()


def main():
    args = parse_args()
    template_path = Path(args.template)
    output_dir = Path(args.output)

    if args.watch:
        watch(template_path, output_dir)
        return

    try:
        build(template_path, output_dir)
    except (OSError, subprocess.CalledProcessError):
        log.error("build failed")
        sys.exit(1)


if __name__ == "__main__":
    main()
