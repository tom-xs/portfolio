# Portfolio — Tomas Xavier Santos

Personal site, projects and CV, hosted on GitHub Pages. Monospace-web aesthetic,
generated from Markdown.

## How it works

**Markdown files are the single source of truth.** Edit them, push to `master`,
and a GitHub Action rebuilds the site automatically:

| Source | Generated |
| --- | --- |
| `index.md` | `index.html` (landing page) |
| `projects.md` | `projects/index.html` |
| `cv.md` | `cv/index.html` + `cv/tomas-xavier-santos-cv.pdf` |

Never edit the generated HTML/PDF by hand; they are overwritten on every build.

## Adding a project

Add a section to `projects.md`:

```md
## my-project

What it does, why it's interesting.

- tech: Python · Selenium
- code: [github.com/tom-xs/my-project](https://github.com/tom-xs/my-project)
```

The landing page's project list is generated automatically from the
`## headings` in `projects.md` — no other file needs to change.

## Repository layout

| Path | Purpose |
| --- | --- |
| `index.md`, `projects.md`, `cv.md` | Content (the only files you edit) |
| `templates/site-template.html` | Shared monospace HTML shell (screen + print CSS) |
| `build.py` | Build script: Markdown -> HTML (pandoc) -> PDF (WeasyPrint) |
| `.github/workflows/build-cv.yml` | CI that rebuilds on every content change |
| `.nojekyll` | Disables Jekyll so Pages serves the files as-is |

## Building locally

```sh
pip install weasyprint   # plus pandoc installed on your system
python3 build.py
```

The old LaTeX CV lives on in the archived `cv_latex` repository for reference.
