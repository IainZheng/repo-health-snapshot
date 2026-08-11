import json
import unittest
from dataclasses import replace

from tests.test_scanner import FakeClient, NOW
from repo_health_snapshot.renderers import render_json, render_markdown
from repo_health_snapshot.scanner import scan_repository


class RendererTests(unittest.TestCase):
    def setUp(self):
        self.report = scan_repository(
            FakeClient(),
            "acme/widget",
            maintainer="acme",
            now=NOW,
        )

    def test_json_is_valid_and_versioned(self):
        payload = json.loads(render_json(self.report))

        self.assertEqual(payload["schema_version"], "1.0")
        self.assertEqual(payload["repository"]["slug"], "acme/widget")
        self.assertIn("source_urls", payload)

    def test_markdown_contains_disclaimer_sources_and_metrics(self):
        markdown = render_markdown(self.report)

        self.assertIn("not a quality score or prediction", markdown)
        self.assertIn("| Stars | 12 |", markdown)
        self.assertIn("## Public sources", markdown)
        self.assertIn("https://github.com/acme/widget", markdown)

    def test_markdown_escapes_untrusted_repository_description(self):
        report = replace(
            self.report,
            repository=replace(self.report.repository, description="<script>|unsafe&text"),
        )

        markdown = render_markdown(report)

        self.assertIn("&lt;script&gt;\\|unsafe&amp;text", markdown)
        self.assertNotIn("<script>", markdown)


if __name__ == "__main__":
    unittest.main()
