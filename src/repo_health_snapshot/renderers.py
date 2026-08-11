from __future__ import annotations

import json

from .models import HealthReport


def render_json(report: HealthReport) -> str:
    return json.dumps(report.to_dict(), ensure_ascii=False, indent=2, sort_keys=False) + "\n"


def render_markdown(report: HealthReport) -> str:
    repo = report.repository
    adoption = report.adoption
    activity = report.activity
    community = report.community
    maintainer = report.maintainer
    lines = [
        f"# Repository health snapshot: {_escape(repo.slug)}",
        "",
        "> Read-only public GitHub snapshot. This report is not a quality score or prediction.",
        "",
        f"Generated: `{_escape(report.generated_at)}`  ",
        f"Lookback window: `{activity.lookback_days}` days, beginning `{_escape(activity.window_start)}`",
        "",
        "## Repository",
        "",
        "| Signal | Observed value |",
        "|---|---|",
        f"| URL | [{_escape(repo.url)}]({_escape(repo.url)}) |",
        f"| Description | {_escape(repo.description or 'Not provided')} |",
        f"| Source repository | {'No (fork)' if repo.is_fork else 'Yes'} |",
        f"| Archived | {'Yes' if repo.is_archived else 'No'} |",
        f"| License | `{_escape(repo.license or 'Not detected')}` |",
        f"| Default branch | `{_escape(repo.default_branch)}` |",
        f"| Created | `{_escape(repo.created_at)}` |",
        f"| Last push | `{_escape(repo.pushed_at or 'Not available')}` |",
        "",
        "## Adoption and participation",
        "",
        "| Signal | Count |",
        "|---|---:|",
        f"| Stars | {adoption.stars} |",
        f"| Downstream forks | {adoption.forks} |",
        f"| Watchers | {adoption.watchers} |",
        f"| Contributors | {_count(adoption.contributors, adoption.contributors_truncated)} |",
        "",
        "## Activity",
        "",
        "| Signal | Count in lookback window |",
        "|---|---:|",
        f"| Commits | {_count(activity.commits, activity.commits_truncated)} |",
        f"| Pull requests updated | {_count(activity.pull_requests_updated, activity.pull_requests_truncated)} |",
        f"| Pull requests merged | {_count(activity.merged_pull_requests, activity.pull_requests_truncated)} |",
        f"| Issues updated | {_count(activity.issues_updated, activity.issues_truncated)} |",
        f"| Issues closed | {_count(activity.closed_issues, activity.issues_truncated)} |",
        f"| Releases published | {_count(activity.releases_published, activity.releases_truncated)} |",
        "",
        "## Maintainer context",
        "",
        f"- Username: `{_escape(maintainer.username or 'Not supplied')}`",
        f"- Matches repository owner: `{_optional_bool(maintainer.owner_match)}`",
        f"- Contributor commits: `{maintainer.contributor_commits if maintainer.contributor_commits is not None else 'Not evaluated'}`",
        f"- Collaborator permission: `{_escape(maintainer.collaborator_permission or 'Not verified')}`",
        "",
        "## Community files",
        "",
    ]
    if community.health_percentage is not None:
        lines.append(f"GitHub community health: `{community.health_percentage}%`")
        lines.append("")
    labels = {
        "readme": "README",
        "license": "License",
        "contributing": "Contributing guide",
        "code_of_conduct": "Code of conduct",
        "security_policy": "Security policy",
        "issue_template": "Issue template",
        "pull_request_template": "Pull-request template",
        "ci_workflows": "CI workflow",
        "changelog": "Changelog",
    }
    for key, label in labels.items():
        lines.append(f"- [{'x' if community.files.get(key) else ' '}] {label}")

    lines.extend(["", "## Findings", ""])
    icons = {"pass": "✅", "info": "ℹ️", "warning": "⚠️"}
    for finding in report.findings:
        lines.append(f"- {icons.get(finding.level, '•')} **{_escape(finding.code)}** — {_escape(finding.message)}")

    lines.extend(["", "## Public sources", ""])
    for label, url in report.source_urls.items():
        lines.append(f"- [{_escape(label)}]({_escape(url)})")

    lines.extend(["", "## Caveats", ""])
    for caveat in report.caveats:
        lines.append(f"- {_escape(caveat)}")
    return "\n".join(lines) + "\n"


def _escape(value: str) -> str:
    return (
        str(value)
        .replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace("|", "\\|")
        .replace("\r", " ")
        .replace("\n", " ")
    )


def _count(value: int, truncated: bool) -> str:
    return f"{value}+" if truncated else str(value)


def _optional_bool(value: bool | None) -> str:
    if value is None:
        return "Not evaluated"
    return "Yes" if value else "No"
