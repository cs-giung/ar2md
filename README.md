# ar2md

Download a versioned arXiv paper as HTML and convert it to LLM-ready Markdown with Pandoc. Native arXiv HTML is preferred; papers without it fall back to ar5iv.

## Requirements

- GNU Wget
- Pandoc 3.x

Set `WGET` or `PANDOC` to an executable path when either tool is not on `PATH`.

## Run without installing

```bash
uvx ar2md 1706.03762v7
```

## Install as a uv tool

```bash
uv tool install ar2md
ar2md 1706.03762v7
```

The PyPI distribution and installed executable are both named `ar2md`.

To run an unreleased commit directly from GitHub:

```bash
uvx --from git+https://github.com/cs-giung/ar2md ar2md 1706.03762v7
uv tool install git+https://github.com/cs-giung/ar2md
```

A version is required so that the local reference is reproducible. For convenience, the common extra-dot spelling `1706.03762.v7` is accepted and normalized to `1706.03762v7`. Versioned arXiv `abs`, `html`, and `pdf` URLs are also accepted.

## Output

The default mirror root is `./ar2md`. Files retain their source hostname:

```text
ar2md/
├── index.jsonl
├── arxiv.org/                 # preferred source
│   ├── html/
│   │   ├── 1706.03762v7.html
│   │   ├── 1706.03762v7.md
│   │   └── 1706.03762v7/
│   └── static/
└── ar5iv.labs.arxiv.org/      # created only for fallback papers
    ├── html/
    │   ├── 1503.02531v1.html
    │   └── 1503.02531v1.md
    └── assets/
```

Choose another mirror root with `--output-dir`:

```bash
ar2md 1706.03762v7 --output-dir papers
```

An existing HTML snapshot is reused, while Markdown is regenerated atomically on each invocation.

`index.jsonl` contains one JSON object per versioned paper ID. Records are sorted by ID and replaced, rather than duplicated, when a paper is regenerated. The index is written atomically after successful conversion:

```json
{"id": "1207.0580v1", "title": "Improving neural networks by preventing co-adaptation of feature detectors", "source": "https://ar5iv.labs.arxiv.org/html/1207.0580v1", "html": "ar5iv.labs.arxiv.org/html/1207.0580v1.html", "markdown": "ar5iv.labs.arxiv.org/html/1207.0580v1.md", "warnings": [{"code": "unresolved_citation_placeholders", "count": 24}]}
```

The `html` and `markdown` paths are relative to the mirror root. The `source` field records whether the HTML came from arXiv or ar5iv. `warnings` is empty for a clean conversion.

After conversion, `ar2md` checks for unresolved citation placeholders, unresolved internal links, nested display-math delimiters, and missing local images. Findings are printed to stderr and stored as structured warning counts in the index. The tool does not fabricate content that is already missing from the source HTML.

## ar5iv fallback

The downloader first requests `https://arxiv.org/html/<versioned-id>`. An HTTP 404 triggers a request to `https://ar5iv.labs.arxiv.org/html/<versioned-id>`; network failures and other HTTP errors do not silently switch sources. For example:

```bash
ar2md 1503.02531v1
```

The resulting HTML and Markdown are stored under `ar2md/ar5iv.labs.arxiv.org/`, making the alternate provenance explicit. A cached fallback snapshot is reused on later runs. ar5iv is a LaTeXML conversion service rather than an arXiv archival endpoint, so retain the downloaded snapshot when exact reproducibility matters.

## Local development

```bash
uvx --from . ar2md 1706.03762v7
uv tool install .
```

## Conversion

The bundled Lua filter keeps the paper body while removing arXiv UI, preserves TeX math and figures, uses figure captions as descriptive image alt text, reconstructs algorithm code blocks, normalizes footnotes and equation blocks, and rewrites internal citations to valid local anchors.

## Publishing

Build and validate the distributions locally:

```bash
uv lock --check
uv run python -m unittest discover -s tests -v
uv build
uvx twine check dist/*
```

Publishing uses PyPI Trusted Publishing. In the PyPI project or pending-publisher settings, configure:

- PyPI project: `ar2md`
- GitHub owner: `cs-giung`
- GitHub repository: `ar2md`
- workflow: `publish.yml`
- environment: `pypi`

Then create a GitHub release from a tag matching `v<project.version>`, such as `v0.1.0`. The release workflow checks the tag against `pyproject.toml`, runs the test suite, validates both distributions, and publishes without a long-lived API token.

## License

MIT
