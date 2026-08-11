from __future__ import annotations

import argparse
import os
import sys
import tempfile
from pathlib import Path
from typing import Sequence

from . import __version__
from .client import GitHubClient
from .errors import RepoHealthError
from .renderers import render_json, render_markdown
from .scanner import scan_repository


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="repo-health-snapshot",
        description="Generate a reproducible health snapshot from public GitHub data.",
    )
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    subparsers = parser.add_subparsers(dest="command", required=True)

    scan = subparsers.add_parser("scan", help="scan one public GitHub repository")
    scan.add_argument("repository", help="repository in owner/name form")
    scan.add_argument("--maintainer", help="GitHub username whose role should be evaluated")
    scan.add_argument(
        "--lookback-days",
        type=_bounded_integer(1, 3650),
        default=365,
        help="activity window in days (default: 365)",
    )
    scan.add_argument(
        "--timeout",
        type=_bounded_float(1.0, 60.0),
        default=15.0,
        help="per-request timeout in seconds (default: 15)",
    )
    scan.add_argument("--json", type=Path, help="write the JSON snapshot to this path")
    scan.add_argument("--markdown", type=Path, help="write the Markdown snapshot to this path")
    scan.add_argument(
        "--stdout",
        choices=("markdown", "json", "none"),
        default=None,
        help="standard-output format; defaults to Markdown when no files are requested",
    )
    scan.add_argument("--force", action="store_true", help="replace existing local output files")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    if args.command != "scan":
        parser.error("a command is required")

    token = os.environ.get("GITHUB_TOKEN") or None
    client = GitHubClient(token=token, timeout=args.timeout)
    try:
        report = scan_repository(
            client,
            args.repository,
            maintainer=args.maintainer,
            lookback_days=args.lookback_days,
        )
        json_text = render_json(report)
        markdown_text = render_markdown(report)
        if args.json:
            _atomic_write(args.json, json_text, force=args.force)
        if args.markdown:
            _atomic_write(args.markdown, markdown_text, force=args.force)

        output_format = args.stdout
        if output_format is None:
            output_format = "none" if args.json or args.markdown else "markdown"
        if output_format == "json":
            sys.stdout.write(json_text)
        elif output_format == "markdown":
            sys.stdout.write(markdown_text)
        return 0
    except (RepoHealthError, OSError, ValueError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1


def _atomic_write(path: Path, content: str, *, force: bool) -> None:
    destination = path.expanduser()
    if destination.exists() and not force:
        raise FileExistsError(f"output exists: {destination}; pass --force to replace it")
    destination.parent.mkdir(parents=True, exist_ok=True)
    handle = tempfile.NamedTemporaryFile(
        mode="w",
        encoding="utf-8",
        newline="\n",
        dir=destination.parent,
        prefix=f".{destination.name}.",
        suffix=".tmp",
        delete=False,
    )
    temp_path = Path(handle.name)
    try:
        with handle:
            handle.write(content)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temp_path, destination)
    except BaseException:
        temp_path.unlink(missing_ok=True)
        raise


def _bounded_integer(minimum: int, maximum: int):
    def parse(value: str) -> int:
        try:
            number = int(value)
        except ValueError as exc:
            raise argparse.ArgumentTypeError("must be an integer") from exc
        if not minimum <= number <= maximum:
            raise argparse.ArgumentTypeError(f"must be between {minimum} and {maximum}")
        return number

    return parse


def _bounded_float(minimum: float, maximum: float):
    def parse(value: str) -> float:
        try:
            number = float(value)
        except ValueError as exc:
            raise argparse.ArgumentTypeError("must be a number") from exc
        if not minimum <= number <= maximum:
            raise argparse.ArgumentTypeError(f"must be between {minimum:g} and {maximum:g}")
        return number

    return parse
