# repo-health-snapshot

[![CI](https://github.com/IainZheng/repo-health-snapshot/actions/workflows/ci.yml/badge.svg)](https://github.com/IainZheng/repo-health-snapshot/actions/workflows/ci.yml)

`repo-health-snapshot` is a read-only Python CLI for generating reproducible health snapshots from public GitHub repository data. It gives maintainers a dated baseline for release planning, community-file cleanup, governance reviews, and project retrospectives without reducing project health to a single score.

The tool reports observations, gaps, collection limits, and public source URLs. It does not rank repositories or predict project quality.

## Why this exists

Repository health is multidimensional. Recent commits can coexist with missing contribution guidance; high star counts can coexist with inactive releases; a fork can inherit popularity that says little about the fork's own maintenance. This tool keeps adoption, activity, community readiness, and optional maintainer context separate so teams can discuss the same observable baseline.

## Features

- Reads only public repository data from GitHub's REST API.
- Refuses to scan private repositories, even when a token can access them.
- Separates repository state, adoption, activity, releases, community files, and optional maintainer context.
- Detects forks and prevents inherited upstream popularity from being presented as local activity.
- Generates deterministic JSON plus a human-readable Markdown snapshot.
- Uses no runtime dependencies outside the Python standard library.
- Accepts an optional token only through `GITHUB_TOKEN`; tokens are never accepted as command-line arguments or written to reports.
- Bounds pagination and marks counts as truncated instead of pretending they are complete.

## Quick start

Python 3.11 or newer is required.

```bash
python -m pip install .

# Unauthenticated public scan. GitHub applies a low hourly rate limit.
repo-health-snapshot scan owner/repository \
  --maintainer username \
  --json snapshots/report.json \
  --markdown snapshots/report.md

# Optional: increase the GitHub API rate limit and verify permissions when allowed.
export GITHUB_TOKEN="your-fine-grained-read-token"
repo-health-snapshot scan owner/repository --maintainer username
```

If neither `--json` nor `--markdown` is supplied, the Markdown snapshot is printed to standard output. Existing output files are protected unless `--force` is given.

## Snapshot contents

- Repository identity, fork/archive status, license, timestamps, and canonical URL.
- Stars, forks, watchers, contributors, and bounded-count disclosures.
- Commits, pull requests, issues, and releases within a configurable lookback window.
- README, license, contributing guide, code of conduct, security policy, templates, CI workflow, and changelog presence.
- Optional maintainer owner-match, contributor commits, and collaborator permission.
- Findings labeled `pass`, `info`, or `warning`, followed by explicit caveats and public sources.

The default lookback window is 365 days. It is a reporting window, not a universal health threshold.

## Privacy and security boundaries

- The API host is fixed to `api.github.com`; repository input is validated as `owner/name`.
- Private repositories are rejected before activity or community data is collected.
- The tool never writes to GitHub, opens issues, changes settings, merges code, or publishes releases.
- Snapshots may contain public usernames and repository metadata. Review generated files before sharing them.
- Do not use the tool to claim authority over a repository you do not administer.

See [SECURITY.md](SECURITY.md) for vulnerability reporting.

## Development

```bash
python -m unittest discover -s tests -v
python -m compileall -q src
```

The test suite uses synthetic fixtures and does not require network access. See [CONTRIBUTING.md](CONTRIBUTING.md) for the contribution workflow and [CHANGELOG.md](CHANGELOG.md) for release history.

## Project status

Version `0.1.0` is the first public release. Planned work includes comparison snapshots, organization-level views, and package-registry adapters while preserving the same public-data and least-privilege boundaries.

## License

MIT
