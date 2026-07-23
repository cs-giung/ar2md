# Converter comparison

This document compares `ar2md` with two similarly named PyPI projects discussed during repository setup:

- local `ar2md` 0.1.0
- [`arxiv-md` 0.1.0](https://pypi.org/project/arxiv-md/)
- [`arxiv2markdown` 0.1.0](https://pypi.org/project/arxiv2markdown/)

Every unqualified tool name below refers to these exact versions; future releases may produce different results.

The comparison was executed on 2026-07-23 against three versioned papers:

- [`1207.0580v1`](https://arxiv.org/abs/1207.0580v1), *Improving neural networks by preventing co-adaptation of feature detectors*
- [`1706.03762v7`](https://arxiv.org/abs/1706.03762v7), *Attention Is All You Need*
- [`2512.14575v1`](https://arxiv.org/abs/2512.14575v1), *Extremal descendant integrals on moduli spaces of curves: An inequality discovered and proved in collaboration with AI*

These papers exercise different retrieval and conversion paths. arXiv returns 404 for the HTML version of `1207.0580v1`, so HTML-based tools must use ar5iv. arXiv serves conventional native HTML for `1706.03762v7`. The native HTML for `2512.14575v1` embeds most prose inside SVG `foreignObject` elements generated for custom human/AI attribution environments.

## Scope and method

The tools use different source representations, so this is an end-to-end comparison rather than a converter-only benchmark:

| Tool | Input used by the tool | External runtime |
| --- | --- | --- |
| `ar2md` 0.1.0 | arXiv HTML; ar5iv after an arXiv HTML 404 | GNU Wget and Pandoc 3.10.1 |
| `arxiv-md` 0.1.0 | arXiv TeX source bundle | None for core conversion; `[assets]` was installed for default figure rasterization |
| `arxiv2markdown` 0.1.0 | arXiv HTML; ar5iv after an arXiv HTML 404 | Python dependencies |

Commands used:

```bash
# Local checkout
uv run ar2md --version  # ar2md 0.1.0
PANDOC=/path/to/pandoc uv run ar2md 1207.0580v1 \
  --output-dir /tmp/ar2md-comparison/ar2md-0.1.0
PANDOC=/path/to/pandoc uv run ar2md 1706.03762v7 \
  --output-dir /tmp/ar2md-comparison/ar2md-0.1.0
PANDOC=/path/to/pandoc uv run ar2md 2512.14575v1 \
  --output-dir /tmp/ar2md-comparison/ar2md-0.1.0

# TeX-source converter
uvx --from 'arxiv-md[assets]==0.1.0' arxiv-to-md 1207.0580v1 \
  --outdir /tmp/ar2md-comparison/arxiv-md-0.1.0 --json
uvx --from 'arxiv-md[assets]==0.1.0' arxiv-to-md 1706.03762v7 \
  --outdir /tmp/ar2md-comparison/arxiv-md-0.1.0 --json
uvx --from 'arxiv-md[assets]==0.1.0' arxiv-to-md 2512.14575v1 \
  --outdir /tmp/ar2md-comparison/arxiv-md-0.1.0 --json

# HTML parser
uvx --from 'arxiv2markdown==0.1.0' arxiv2md 1207.0580v1 \
  -o /tmp/ar2md-comparison/arxiv2markdown-0.1.0/1207.0580v1.md
uvx --from 'arxiv2markdown==0.1.0' arxiv2md 1706.03762v7 \
  -o /tmp/ar2md-comparison/arxiv2markdown-0.1.0/1706.03762v7.md
uvx --from 'arxiv2markdown==0.1.0' arxiv2md 2512.14575v1 \
  -o /tmp/ar2md-comparison/arxiv2markdown-0.1.0/2512.14575v1.md

```

Network and installation timings are intentionally excluded. The services, uv cache state, and amount of downloaded media differ too much for the observed wall times to be meaningful.
The generated outputs are committed as benchmark snapshots:

```text
tests/
├── ar2md-0.1.0/
│   ├── index.jsonl
│   ├── arxiv.org/
│   │   ├── html/
│   │   │   ├── 1706.03762v7.{html,md}
│   │   │   └── 2512.14575v1.{html,md}
│   │   ├── static/
│   │   └── robots.txt
│   └── ar5iv.labs.arxiv.org/
│       ├── html/
│       │   └── 1207.0580v1.{html,md}
│       ├── assets/
│       └── robots.txt
├── arxiv-md-0.1.0/
│   ├── 1207.0580v1/{conversion.json,document.md,images/}
│   ├── 1706.03762v7/{conversion.json,document.md,images/}
│   └── 2512.14575v1/{conversion.json,document.md}
└── arxiv2markdown-0.1.0/
    ├── 1207.0580v1.md
    ├── 1706.03762v7.md
    └── 2512.14575v1.md
```

These files total about 5.82 MB (5.55 MiB). They are deliberately part of the source repository for direct inspection, so repository clones and Git-based `uv` installs fetch them. Hatch excludes `/tests` from both the wheel and source distribution; PyPI installations therefore do not include the snapshots. The commands above reproduce the same comparison layout under `/tmp`.


The quantitative checks below use UTF-8 byte size, `\b\w+\b` word counting, ATX heading counting, Markdown image syntax, and direct filesystem checks for relative image targets. A nested display-math block means an invalid form such as `$$ $formula$ $$`. Source-ID links are links such as `](#S3.F1)` whose target must be emitted as an explicit HTML anchor; normal renderer-generated heading slugs are not included in this check.

## Case 1: `1207.0580v1`

### Retrieval result

| Tool | Result | Actual source |
| --- | --- | --- |
| `ar2md` 0.1.0 | Success | ar5iv fallback; HTML, Markdown, CSS, and images mirrored locally |
| `arxiv-md` 0.1.0 | Success | arXiv TeX source bundle |
| `arxiv2markdown` 0.1.0 | Command succeeded, but output was incomplete | ar5iv fallback |

### Measured output

| Metric | `ar2md` 0.1.0 | `arxiv-md` 0.1.0 | `arxiv2markdown` 0.1.0 |
| --- | ---: | ---: | ---: |
| Markdown bytes | 49,121 | 45,780 | 29,927 |
| Heuristic words | 7,869 | 7,535 | 4,935 |
| ATX headings | 22 | 22 | 22 |
| Markdown images | 10 | 10 | 0 |
| Referenced local images present | 10/10 | 10/10 | 0/0 |
| Plain figure-path labels | 0 | 0 | 3 |
| Display-math blocks | 1 | 4 | 4 |
| Nested display-math blocks | 0 | 0 | 4 |
| Unresolved citation placeholders | 24 | 0 | 5 |
| Main pre-appendix body present | Yes | Yes | **No** |
| Unresolved unique source-ID links | 0 | 0 | 4 |
| arXiv/ar5iv UI or data-URI noise | 0 | 0 | 0 |

### `ar2md` 0.1.0

`ar2md` correctly detected the native arXiv HTML 404, fetched ar5iv, and preserved the complete body, appendices, and all 10 paper images as working relative Markdown links. All images use their figure captions as descriptive alt text instead of the source's generic `Refer to caption` label. All 13 emitted internal-link occurrences resolve to explicit local anchors. The output contains no ar5iv UI or embedded data-URI noise.

The principal defect is inherited from the ar5iv rendering: 24 citations in the body became visible `?` placeholders. For example, the opening discussion contains `(**?**)` instead of a reference number. The bibliography itself is present, but those damaged citations cannot be reconnected by the Pandoc filter because the source HTML no longer contains their keys. `ar2md` 0.1.0 reports the count on stderr and stores it in the `index.jsonl` record as an `unresolved_citation_placeholders` warning.

Verdict: best of the two HTML-based tools for completeness and local archiving, but not reliable for citations on this paper.

### `arxiv-md` 0.1.0

The TeX-source converter preserves the complete body, all 10 figures, and 23 citation keys in Pandoc-style forms such as `[@RHW]`. It therefore has materially better citation fidelity than either ar5iv-based result.

Its `conversion.json` reports two warnings: the `sciabstract` and `scilastnote` environments are unknown and retained as fenced raw LaTeX. This is visible in the output: the abstract and final note are present but less immediately readable than ordinary Markdown.

Verdict: strongest result for this older paper when citation semantics matter; weaker than `ar2md` for clean, immediately rendered Markdown.

### `arxiv2markdown` 0.1.0

The command reports success and 21 sections, but the produced Markdown starts at `References and Notes`, followed by the appendices. The abstract and the entire main pre-reference body are absent; the sentence `A feedforward, artificial neural network uses layers`, present in both complete outputs, does not occur.

No Markdown images are emitted. Three figure paths appear as plain labels, four emitted display equations use nested dollar delimiters, and four unique source-ID links (`A1.F5`, `A1.SS1`, `A2.F6`, and `A3.F7`) have no corresponding anchors.

Verdict: not usable for this paper without a completeness check.

## Case 2: `1706.03762v7`

### Retrieval result

| Tool | Result | Actual source |
| --- | --- | --- |
| `ar2md` 0.1.0 | Success | Native arXiv HTML; page requirements mirrored locally |
| `arxiv-md` 0.1.0 | Success | arXiv TeX source bundle |
| `arxiv2markdown` 0.1.0 | Success | Native arXiv HTML |

### Measured output

| Metric | `ar2md` 0.1.0 | `arxiv-md` 0.1.0 | `arxiv2markdown` 0.1.0 |
| --- | ---: | ---: | ---: |
| Markdown bytes | 55,209 | 57,521 | 40,708 |
| Heuristic words | 7,149 | 9,218 | 6,357 |
| ATX headings | 31 | 31 | 31 |
| Markdown images | 8 | 8 | 0 |
| Referenced local images present | 8/8 | 8/8 | 0/0 |
| Plain figure-path labels | 0 | 0 | 5 |
| Tables retained | 4 grid tables | 4 raw HTML tables | 4 pipe tables |
| Display-math blocks | 3 | 5 | 5 |
| Nested display-math blocks | 0 | 0 | 5 |
| Pandoc citation markers | 0 | 63 | 0 |
| Internal-link occurrences | 93 | 0 | 17 |
| Unresolved unique source-ID links | 0 | 0 | 9 |
| arXiv UI or data-URI noise | 0 | 0 | 0 |

### `ar2md` 0.1.0

The native-HTML path is the strongest `ar2md` case. The complete body, four tables, three displayed equation groups, bibliography, and all eight paper images are retained. Each image now uses its figure caption as descriptive alt text. Citation, equation, figure, table, and section links account for 93 internal-link occurrences; every unique target resolves to an explicit anchor. Math delimiters are valid, and the output has no arXiv UI or data-URI noise.

Pandoc emits the complex tables as grid tables rather than pipe tables. They preserve merged headers and cell structure, but are wider and less convenient to edit manually. Author/frontmatter formatting also follows the source HTML closely and is less compact than the alternatives.

Verdict: strongest standalone offline artifact and strongest internal navigation.

### `arxiv-md` 0.1.0

The TeX-source result preserves the full body and all eight figures. Its sidecar reports eight resolved figures, four HTML tables, and no warnings. Display math uses valid delimiters and retains TeX environments such as `align*`.

The output keeps 63 citations as Pandoc citation keys, which is useful for a later citeproc stage but is not clickable in a plain Markdown renderer. Tables are retained as verbose raw HTML, contributing to the larger word and byte counts. Some TeX normalization is lossy in prose: for example, `Łukasz` appears as `ukasz`, and several inline formulas are converted to Unicode forms rather than retained uniformly as TeX.

Verdict: strongest source-oriented representation, especially when a downstream Pandoc/citeproc pipeline is available; less clean as a directly consumed Markdown file.

### `arxiv2markdown` 0.1.0

This is the most compact successful output and the only result with pipe tables. It includes the complete section tree and main text, making it substantially better on native arXiv HTML than on the ar5iv case.

The conversion does not emit Markdown image syntax or local assets. Five figures are represented by caption text plus plain paths. All five displayed equation groups are wrapped as nested `$$ $...$ $$`, which is invalid in common math renderers. Nine unique source-ID targets (`S3.F1`, `S3.F2`, `S3.SS2`, `S3.SS2.SSS2`, `S4.T1`, `S5.SS4`, `S6.T2`, `S6.T3`, and `S6.T4`) are linked but never emitted as anchors.

Verdict: compact and convenient for text-only prompting, but not a self-contained local reference and not safe for math or internal navigation without post-processing.

## Case 3: `2512.14575v1`

### Retrieval result

| Tool | Result | Actual source |
| --- | --- | --- |
| `ar2md` 0.1.0 | Success after recovering embedded HTML prose | Native arXiv HTML; page requirements mirrored locally |
| `arxiv-md` 0.1.0 | Success, with most content retained as raw LaTeX | arXiv TeX source bundle |
| `arxiv2markdown` 0.1.0 | Command succeeded, but output was incomplete | Native arXiv HTML |

### Measured output

| Metric | `ar2md` 0.1.0 | `arxiv-md` 0.1.0 | `arxiv2markdown` 0.1.0 |
| --- | ---: | ---: | ---: |
| Markdown bytes | 49,725 | 51,106 | 9,899 |
| Heuristic words | 8,391 | 7,858 | 1,329 |
| ATX headings | 42 | 9 | 91 |
| Markdown images | 0 | 0 | 0 |
| Display-math blocks | 32 | 1 | 0 |
| Internal-link occurrences | 78 | 0 | 0 |
| Explicit source-ID anchors | 41 | 0 | 0 |
| Unresolved unique source-ID links | 0 | 0 | 0 |
| Main proof body present | Yes | Yes, inside raw LaTeX fences | **No** |
| arXiv UI or data-URI noise | 0 | 0 | 0 |

### `ar2md` 0.1.0

The source uses custom human/AI attribution environments that LaTeXML rendered as HTML inside 17 `foreignObject` elements nested in `svg.ltx_picture` containers. Pandoc normally treats each outer SVG as a graphic and discards its embedded document subtree. `ar2md` now replaces those specific SVG containers with their `foreignObject` HTML before conversion. This recovers the abstract, introduction, proofs, appendices, and bibliography without modifying ordinary paper figures.

The result contains 8,391 heuristic words, all 42 article headings, 32 display-math blocks, and the sentence `We prove that among all`, used here as the main-proof completeness sentinel. All 78 internal-link occurrences resolve through 41 explicit anchors. External HTML-fragment links remain external instead of being incorrectly rewritten as local targets.

The visible `Human` and `AI` labels are retained as semantic text. Some source-specific attribution styling also survives inside TeX as `\color`, `\definecolor`, and `\uwave`; this is less polished than ordinary paper math but preserves more information than deleting the annotations.

Verdict: the only complete, immediately readable Markdown result for this paper.

### `arxiv-md` 0.1.0

The TeX-source conversion retains the complete prose, but custom environments including `altabstract`, `authornote`, `humanparagraph`, and `aiparagraph` are emitted as large fenced `latex` blocks. Consequently, only nine structural headings become Markdown headings and most equations and references remain embedded LaTeX rather than directly rendered Markdown.

Verdict: complete and source-faithful, but primarily a raw-TeX preservation artifact for this paper rather than LLM-ready Markdown.

### `arxiv2markdown` 0.1.0

The command reports 41 sections, but the output consists mainly of repeated headings and the bibliography. It has 1,329 heuristic words versus 8,391 in the complete `ar2md` result, and the main proof sentence `We prove that among all` is absent.

Verdict: not usable for this paper without a completeness check.

## Overall assessment

| Requirement | Best observed choice | Reason |
| --- | --- | --- |
| Versioned local HTML and asset archive | `ar2md` 0.1.0 | Mirrors source HTML, page requirements, figures, and provenance-specific paths |
| Native arXiv HTML converted to immediately renderable Markdown | `ar2md` 0.1.0 | Complete content, descriptive image alt text, valid math delimiters, local figures, and resolved internal links |
| Native HTML with article prose inside SVG `foreignObject` | `ar2md` 0.1.0 | Recovers the embedded HTML before Pandoc while preserving ordinary SVG figures |
| Older paper with damaged ar5iv citations | `arxiv-md` 0.1.0 | TeX source retained all citation keys while both ar5iv-based outputs contained `?` placeholders |
| TeX semantics for downstream Pandoc processing | `arxiv-md` 0.1.0 | Pandoc citation keys, raw TeX fallbacks, conversion sidecar, and asset diagnostics |
| Compact text-only extraction | `arxiv2markdown` 0.1.0 on native arXiv HTML | Smallest complete native-HTML output and pipe tables |

`ar2md` is not uniformly better than a TeX-source converter. Its intended advantage is a reproducible local web snapshot with a clean Markdown projection. The three cases establish a practical boundary:

1. Conventional native arXiv HTML (`1706.03762v7`) gives a complete, self-contained `ar2md` result with the best link integrity.
2. ar5iv fallback (`1207.0580v1`) preserves the paper and figures, but upstream conversion damage can make citations unrecoverable. For this class of paper, `arxiv-md` should be preferred when source-level citation fidelity matters.
3. Native HTML generated from custom document environments (`2512.14575v1`) may place real article content inside SVG `foreignObject` elements. Recovering those elements makes `ar2md` complete where the other HTML parser loses the body and the TeX-source converter falls back to raw LaTeX.

`ar2md` 0.1.0 implements the resulting quality gate: it checks citation placeholders, internal-link targets, nested math delimiters, and local image targets after every conversion, prints warnings, and records structured warning counts in `index.jsonl`. It deliberately warns rather than inventing citations that are already absent from the ar5iv HTML.
