import argparse
import json
import os
import re
import shutil
import subprocess
import sys
from importlib import resources
from importlib.metadata import version
from html.parser import HTMLParser
from pathlib import Path
from typing import Sequence


ARXIV_ID_PATTERN = re.compile(
    r"^(?:https?://(?:www\.)?arxiv\.org/(?:abs|html|pdf)/)?"
    r"(?P<base>\d{4}\.\d{4,5})\.?v(?P<version>\d+)"
    r"(?:\.pdf)?/?$"
)


class _TitleParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.in_title = False
        self.parts: list[str] = []

    def handle_starttag(
        self,
        tag: str,
        attrs: list[tuple[str, str | None]],
    ) -> None:
        if tag == "title":
            self.in_title = True

    def handle_endtag(self, tag: str) -> None:
        if tag == "title":
            self.in_title = False

    def handle_data(self, data: str) -> None:
        if self.in_title:
            self.parts.append(data)

    def title(self) -> str:
        return " ".join("".join(self.parts).split())


def parse_arxiv_id(value: str) -> str:
    match = ARXIV_ID_PATTERN.fullmatch(value)
    if not match:
        raise argparse.ArgumentTypeError(
            "expected a versioned arXiv ID or URL, for example 1706.03762v7"
        )
    return f"{match.group('base')}v{match.group('version')}"


def require_tool(name: str) -> str:
    configured = os.environ.get(name.upper(), name)
    executable = shutil.which(configured)
    if not executable:
        raise SystemExit(
            f"{name} is required but was not found; "
            f"install it or set {name.upper()}=/path/to/{name}"
        )
    return executable


def run(command: list[str], *, cwd: Path) -> None:
    subprocess.run(command, cwd=cwd, check=True)


def _download_html(arxiv_id: str, host: str, wget: str, output_dir: Path) -> Path:
    html_path = output_dir / host / "html" / f"{arxiv_id}.html"
    url = f"https://{host}/html/{arxiv_id}"
    completed = subprocess.run(
        [
            wget,
            "--page-requisites",
            "--convert-links",
            "--adjust-extension",
            "--no-parent",
            url,
        ],
        cwd=output_dir,
        text=True,
        capture_output=True,
    )
    if completed.returncode:
        raise subprocess.CalledProcessError(
            completed.returncode,
            completed.args,
            output=completed.stdout,
            stderr=completed.stderr,
        )
    if not html_path.is_file():
        raise SystemExit(f"wget completed without creating {html_path}")

    sys.stdout.write(completed.stdout)
    sys.stderr.write(completed.stderr)
    return html_path


def _show_download_error(error: subprocess.CalledProcessError) -> None:
    if error.stdout:
        sys.stdout.write(error.stdout)
    if error.stderr:
        sys.stderr.write(error.stderr)


def fetch_html(arxiv_id: str, wget: str, output_dir: Path) -> Path:
    arxiv_path = output_dir / "arxiv.org" / "html" / f"{arxiv_id}.html"
    ar5iv_path = output_dir / "ar5iv.labs.arxiv.org" / "html" / f"{arxiv_id}.html"
    for html_path in (arxiv_path, ar5iv_path):
        if html_path.exists():
            print(f"Using existing HTML: {html_path}")
            return html_path

    try:
        return _download_html(arxiv_id, "arxiv.org", wget, output_dir)
    except subprocess.CalledProcessError as error:
        if error.returncode != 8 or not re.search(r"(?:ERROR\s+|HTTP/\S+\s+)404\b", error.stderr or ""):
            _show_download_error(error)
            raise

    print(
        f"arXiv HTML is unavailable for {arxiv_id}; falling back to ar5iv.",
        file=sys.stderr,
    )
    try:
        return _download_html(arxiv_id, "ar5iv.labs.arxiv.org", wget, output_dir)
    except subprocess.CalledProcessError as error:
        _show_download_error(error)
        raise


def recover_foreign_object_content(source: str) -> tuple[str, int]:
    svg_pattern = re.compile(
        r'<svg\b[^>]*\bltx_picture\b[^>]*>.*?</svg>',
        re.IGNORECASE | re.DOTALL,
    )
    foreign_object_pattern = re.compile(
        r"<foreignobject\b[^>]*>(.*?)</foreignobject>",
        re.IGNORECASE | re.DOTALL,
    )
    recovered_count = 0

    def recover(svg_match: re.Match[str]) -> str:
        nonlocal recovered_count
        fragments = foreign_object_pattern.findall(svg_match.group(0))
        if not fragments:
            return svg_match.group(0)
        recovered_count += 1
        return "\n".join(fragments)

    return svg_pattern.sub(recover, source), recovered_count


def convert_html(html_path: Path, pandoc: str) -> Path:
    output_path = html_path.with_suffix(".md")
    temporary_path = output_path.with_suffix(".md.tmp")
    prepared_path = html_path.with_suffix(".pandoc.html.tmp")
    temporary_path.unlink(missing_ok=True)
    prepared_path.unlink(missing_ok=True)

    source_path = html_path
    source = html_path.read_text(encoding="utf-8", errors="replace")
    recovered_source, recovered_count = recover_foreign_object_content(source)
    if recovered_count:
        prepared_path.write_text(recovered_source, encoding="utf-8")
        source_path = prepared_path

    filter_resource = resources.files("ar2md").joinpath("arxiv.lua")
    try:
        with resources.as_file(filter_resource) as filter_path:
            run(
                [
                    pandoc,
                    source_path.name,
                    "--from=html",
                    "--to=markdown+pipe_tables+tex_math_dollars",
                    "--wrap=none",
                    f"--lua-filter={filter_path}",
                    f"--output={temporary_path.name}",
                ],
                cwd=html_path.parent,
            )
        if not temporary_path.is_file() or temporary_path.stat().st_size == 0:
            raise SystemExit("pandoc did not produce a non-empty Markdown file")
        temporary_path.replace(output_path)
    finally:
        temporary_path.unlink(missing_ok=True)
        prepared_path.unlink(missing_ok=True)

    return output_path


def extract_title(html_path: Path, markdown_path: Path) -> str:
    parser = _TitleParser()
    parser.feed(html_path.read_text(encoding="utf-8", errors="replace"))
    title = re.sub(r"^\[[^\]]+\]\s*", "", parser.title())
    if title:
        return title

    markdown = markdown_path.read_text(encoding="utf-8")
    heading = re.search(r"^#\s+(.+?)\s*$", markdown, re.MULTILINE)
    if heading:
        return heading.group(1)
    raise SystemExit(f"could not determine the paper title from {html_path}")


def inspect_markdown(markdown_path: Path) -> list[dict[str, int]]:
    markdown = markdown_path.read_text(encoding="utf-8")
    warnings: list[dict[str, int]] = []

    citation_placeholders = len(re.findall(r"\*{1,3}\?\*{1,3}", markdown))
    if citation_placeholders:
        warnings.append(
            {
                "code": "unresolved_citation_placeholders",
                "count": citation_placeholders,
            }
        )

    internal_targets = set(re.findall(r"\]\(#([^)]+)\)", markdown))
    explicit_anchors = set(re.findall(r'<a id="([^"]+)"></a>', markdown))
    unresolved_targets = internal_targets - explicit_anchors
    if unresolved_targets:
        warnings.append(
            {
                "code": "unresolved_internal_links",
                "count": len(unresolved_targets),
            }
        )

    nested_math = len(re.findall(r"\$\$\s*\$", markdown))
    if nested_math:
        warnings.append(
            {
                "code": "nested_math_delimiters",
                "count": nested_math,
            }
        )

    image_targets = re.findall(r"!\[[^\]]*\]\(([^)]+)\)", markdown)
    missing_images = {
        target
        for target in image_targets
        if not re.match(r"^(?:https?://|data:)", target)
        and not (markdown_path.parent / target).is_file()
    }
    if missing_images:
        warnings.append(
            {
                "code": "missing_local_images",
                "count": len(missing_images),
            }
        )
    return warnings


def report_warnings(warnings: list[dict[str, int]]) -> None:
    messages = {
        "unresolved_citation_placeholders": (
            "unresolved citation placeholders; the source HTML likely "
            "contains damaged citations"
        ),
        "unresolved_internal_links": "unresolved internal link targets",
        "nested_math_delimiters": "nested display-math delimiters",
        "missing_local_images": "missing local image targets",
    }
    for warning in warnings:
        print(
            f"Warning: {warning['count']} {messages[warning['code']]}.",
            file=sys.stderr,
        )


def update_index(
    output_dir: Path,
    arxiv_id: str,
    title: str,
    html_path: Path,
    markdown_path: Path,
    warnings: list[dict[str, int]],
) -> Path:
    index_path = output_dir / "index.jsonl"
    records: dict[str, dict[str, object]] = {}
    if index_path.exists():
        for line_number, line in enumerate(
            index_path.read_text(encoding="utf-8").splitlines(),
            start=1,
        ):
            if not line.strip():
                continue
            try:
                record = json.loads(line)
            except json.JSONDecodeError as error:
                raise SystemExit(
                    f"invalid JSON in {index_path} at line {line_number}: {error.msg}"
                ) from error
            if not isinstance(record, dict) or not isinstance(record.get("id"), str):
                raise SystemExit(
                    f"invalid record in {index_path} at line {line_number}: "
                    'expected an object with a string "id"'
                )
            records[record["id"]] = record

    relative_html = html_path.relative_to(output_dir)
    relative_markdown = markdown_path.relative_to(output_dir)
    host = relative_html.parts[0]
    records[arxiv_id] = {
        "id": arxiv_id,
        "title": title,
        "source": f"https://{host}/html/{arxiv_id}",
        "html": relative_html.as_posix(),
        "markdown": relative_markdown.as_posix(),
        "warnings": warnings,
    }

    temporary_path = index_path.with_suffix(".jsonl.tmp")
    temporary_path.unlink(missing_ok=True)
    try:
        content = "".join(
            json.dumps(records[record_id], ensure_ascii=False) + "\n"
            for record_id in sorted(records)
        )
        temporary_path.write_text(content, encoding="utf-8")
        temporary_path.replace(index_path)
    finally:
        temporary_path.unlink(missing_ok=True)
    return index_path


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="ar2md",
        description="Download versioned arXiv HTML (with ar5iv fallback) and convert it to Markdown.",
    )
    parser.add_argument("paper", type=parse_arxiv_id, help="versioned arXiv ID or URL")
    parser.add_argument(
        "-o",
        "--output-dir",
        type=Path,
        default=Path("ar2md"),
        help="mirror root (default: ./ar2md)",
    )
    parser.add_argument("--version", action="version", version=f"%(prog)s {version('ar2md')}")
    return parser


def main(argv: Sequence[str] | None = None) -> None:
    parser = build_parser()
    args = parser.parse_args(argv)

    wget = require_tool("wget")
    pandoc = require_tool("pandoc")
    output_dir = args.output_dir.expanduser().resolve()
    output_dir.mkdir(parents=True, exist_ok=True)

    try:
        html_path = fetch_html(args.paper, wget, output_dir)
        markdown_path = convert_html(html_path, pandoc)
        title = extract_title(html_path, markdown_path)
        warnings = inspect_markdown(markdown_path)
        report_warnings(warnings)
        index_path = update_index(
            output_dir,
            args.paper,
            title,
            html_path,
            markdown_path,
            warnings,
        )
    except subprocess.CalledProcessError as error:
        command = Path(error.cmd[0]).name
        parser.exit(error.returncode or 1, f"ar2md: {command} failed\n")

    print(f"HTML: {html_path}")
    print(f"Markdown: {markdown_path}")
    print(f"Index: {index_path}")
