# Portfolio — Tomas Xavier Santos

Personal website and CV, hosted on GitHub Pages.

## How it works

**`cv.md` is the single source of truth for the CV.** Edit that file, push to
`master`, and a GitHub Action automatically rebuilds:

- `cv/index.html` — the CV as a web page (served at `/cv/`)
- `cv/tomas-xavier-santos-cv.pdf` — a print-ready PDF generated from the same source

Never edit the generated files by hand; they are overwritten on every build.

## Repository layout

| Path | Purpose |
| --- | --- |
| `cv.md` | CV content in Markdown (the only file you edit) |
| `templates/cv-template.html` | HTML/CSS template for the web page and PDF |
| `build.py` | Build script: Markdown -> HTML (pandoc) -> PDF (WeasyPrint) |
| `.github/workflows/build-cv.yml` | CI that rebuilds on every change to the CV |
| `index.html` | Landing page |
| `cv/` | Generated output (web page + PDF) |

## Building locally

```sh
pip install weasyprint   # plus pandoc installed on your system
python3 build.py
```

The old LaTeX CV lives on in the archived `cv_latex` repository for reference.
