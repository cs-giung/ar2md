import json
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from ar2md.cli import (
    build_parser,
    extract_title,
    fetch_html,
    inspect_markdown,
    recover_foreign_object_content,
    update_index,
)


class FetchHtmlTests(unittest.TestCase):
    def test_falls_back_to_ar5iv_only_after_arxiv_404(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_dir:
            output_dir = Path(temporary_dir)
            calls: list[str] = []

            def run_download(command: list[str], **_: object) -> subprocess.CompletedProcess[str]:
                url = command[-1]
                calls.append(url)
                if url.startswith("https://arxiv.org/"):
                    return subprocess.CompletedProcess(command, 8, "", "ERROR 404: Not Found.\n")

                html_path = output_dir / "ar5iv.labs.arxiv.org/html/1503.02531v1.html"
                html_path.parent.mkdir(parents=True)
                html_path.write_text("<html><article>paper</article></html>")
                return subprocess.CompletedProcess(command, 0, "", "")

            with patch("ar2md.cli.subprocess.run", side_effect=run_download):
                html_path = fetch_html("1503.02531v1", "wget", output_dir)

            self.assertEqual(
                html_path,
                output_dir / "ar5iv.labs.arxiv.org/html/1503.02531v1.html",
            )
            self.assertEqual(
                calls,
                [
                    "https://arxiv.org/html/1503.02531v1",
                    "https://ar5iv.labs.arxiv.org/html/1503.02531v1",
                ],
            )

    def test_does_not_mask_non_404_download_errors(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_dir:
            failure = subprocess.CompletedProcess(
                ["wget"],
                4,
                "",
                "Network failure\n",
            )
            with (
                patch("ar2md.cli.subprocess.run", return_value=failure) as run_download,
                self.assertRaises(subprocess.CalledProcessError),
            ):
                fetch_html("1503.02531v1", "wget", Path(temporary_dir))

            run_download.assert_called_once()

    def test_reuses_cached_fallback_snapshot(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_dir:
            html_path = (
                Path(temporary_dir)
                / "ar5iv.labs.arxiv.org/html/1503.02531v1.html"
            )
            html_path.parent.mkdir(parents=True)
            html_path.write_text("<html><article>cached</article></html>")

            with patch("ar2md.cli.subprocess.run") as run_download:
                result = fetch_html("1503.02531v1", "wget", Path(temporary_dir))

            self.assertEqual(result, html_path)
            run_download.assert_not_called()


class HtmlRecoveryTests(unittest.TestCase):
    def test_recovers_foreign_object_content_from_ltx_picture(self) -> None:
        source = (
            '<svg class="ltx_picture"><g>'
            "<foreignObject><strong>Human</strong></foreignObject>"
            "<foreignObject><p>Recovered body.</p></foreignObject>"
            "</g></svg>"
            '<svg class="ordinary"><foreignObject>untouched</foreignObject></svg>'
        )

        recovered, count = recover_foreign_object_content(source)

        self.assertEqual(count, 1)
        self.assertIn("<strong>Human</strong>", recovered)
        self.assertIn("<p>Recovered body.</p>", recovered)
        self.assertNotIn('class="ltx_picture"', recovered)
        self.assertIn('class="ordinary"', recovered)


class MarkdownQualityTests(unittest.TestCase):
    def test_detects_conversion_quality_regressions(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_dir:
            markdown_path = Path(temporary_dir) / "paper.md"
            markdown_path.write_text(
                "\n".join(
                    [
                        "Damaged citations (**?**) and (*?*).",
                        "[Broken](#missing)",
                        '<a id="valid"></a>[Valid](#valid)',
                        "$$ $nested$ $$",
                        "![Missing](missing.png)",
                    ]
                )
            )

            self.assertEqual(
                inspect_markdown(markdown_path),
                [
                    {
                        "code": "unresolved_citation_placeholders",
                        "count": 2,
                    },
                    {
                        "code": "unresolved_internal_links",
                        "count": 1,
                    },
                    {
                        "code": "nested_math_delimiters",
                        "count": 1,
                    },
                    {
                        "code": "missing_local_images",
                        "count": 1,
                    },
                ],
            )


class OutputIndexTests(unittest.TestCase):
    def test_default_output_directory_is_ar2md(self) -> None:
        args = build_parser().parse_args(["1706.03762v7"])
        self.assertEqual(args.output_dir, Path("ar2md"))

    def test_extracts_html_title_and_removes_arxiv_prefix(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_dir:
            root = Path(temporary_dir)
            html_path = root / "paper.html"
            markdown_path = root / "paper.md"
            html_path.write_text(
                "<html><head><title>[1207.0580] A Paper &amp; Its Title</title></head></html>"
            )
            markdown_path.write_text("# Fallback Title\n")

            self.assertEqual(
                extract_title(html_path, markdown_path),
                "A Paper & Its Title",
            )

    def test_index_is_sorted_idempotent_and_preserves_provenance(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_dir:
            output_dir = Path(temporary_dir)
            arxiv_html = output_dir / "arxiv.org/html/1706.03762v7.html"
            arxiv_markdown = arxiv_html.with_suffix(".md")
            ar5iv_html = (
                output_dir
                / "ar5iv.labs.arxiv.org/html/1207.0580v1.html"
            )
            ar5iv_markdown = ar5iv_html.with_suffix(".md")
            for path in (arxiv_html, arxiv_markdown, ar5iv_html, ar5iv_markdown):
                path.parent.mkdir(parents=True, exist_ok=True)
                path.touch()

            update_index(
                output_dir,
                "1706.03762v7",
                "Attention Is All You Need",
                arxiv_html,
                arxiv_markdown,
                [],
            )
            update_index(
                output_dir,
                "1207.0580v1",
                "Improving neural networks",
                ar5iv_html,
                ar5iv_markdown,
                [
                    {
                        "code": "unresolved_citation_placeholders",
                        "count": 23,
                    }
                ],
            )
            index_path = update_index(
                output_dir,
                "1706.03762v7",
                "Attention Is All You Need — revised",
                arxiv_html,
                arxiv_markdown,
                [],
            )

            records = [
                json.loads(line)
                for line in index_path.read_text().splitlines()
            ]
            self.assertEqual(
                [record["id"] for record in records],
                ["1207.0580v1", "1706.03762v7"],
            )
            self.assertEqual(
                records[0],
                {
                    "id": "1207.0580v1",
                    "title": "Improving neural networks",
                    "source": "https://ar5iv.labs.arxiv.org/html/1207.0580v1",
                    "html": "ar5iv.labs.arxiv.org/html/1207.0580v1.html",
                    "markdown": "ar5iv.labs.arxiv.org/html/1207.0580v1.md",
                    "warnings": [
                        {
                            "code": "unresolved_citation_placeholders",
                            "count": 23,
                        }
                    ],
                },
            )
            self.assertEqual(
                records[1]["title"],
                "Attention Is All You Need — revised",
            )


if __name__ == "__main__":
    unittest.main()
