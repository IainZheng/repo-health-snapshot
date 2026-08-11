import contextlib
import io
import tempfile
import unittest
from pathlib import Path

from repo_health_snapshot.cli import _atomic_write, build_parser, main


class CliTests(unittest.TestCase):
    def test_parser_accepts_bounded_scan_options(self):
        args = build_parser().parse_args(
            ["scan", "acme/widget", "--maintainer", "acme", "--lookback-days", "90"]
        )

        self.assertEqual(args.repository, "acme/widget")
        self.assertEqual(args.maintainer, "acme")
        self.assertEqual(args.lookback_days, 90)

    def test_invalid_slug_fails_before_network_request(self):
        stderr = io.StringIO()

        with contextlib.redirect_stderr(stderr):
            result = main(["scan", "https://example.com/private"])

        self.assertEqual(result, 1)
        self.assertIn("owner/name", stderr.getvalue())

    def test_atomic_write_protects_existing_output(self):
        with tempfile.TemporaryDirectory() as directory:
            destination = Path(directory) / "report.md"
            _atomic_write(destination, "first\n", force=False)

            with self.assertRaises(FileExistsError):
                _atomic_write(destination, "second\n", force=False)

            _atomic_write(destination, "second\n", force=True)
            self.assertEqual(destination.read_text(encoding="utf-8"), "second\n")


if __name__ == "__main__":
    unittest.main()
