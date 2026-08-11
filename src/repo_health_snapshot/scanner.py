from __future__ import annotations

import re
from datetime import datetime, timedelta, timezone
from typing import Any
from urllib.parse import quote

from .client import GitHubClient
from .errors import GitHubAPIError, InvalidRepositoryError, PrivateRepositoryError
from .models import (
    ActivitySnapshot,
    AdoptionSnapshot,
    CommunitySnapshot,
    HealthReport,
    Finding,
    MaintainerSnapshot,
    RepositorySnapshot,
)


REPOSITORY_PATTERN = re.compile(
    r"^[A-Za-z0-9](?:[A-Za-z0-9-]{0,38})/[A-Za-z0-9._-]{1,100}$"
)
USERNAME_PATTERN = re.compile(r"^[A-Za-z0-9](?:[A-Za-z0-9-]{0,38})$")


def validate_repository_slug(value: str) -> str:
    slug = value.strip()
    if not REPOSITORY_PATTERN.fullmatch(slug):
        raise InvalidRepositoryError("repository must be a safe owner/name slug")
    return slug


def validate_username(value: str) -> str:
    username = value.strip()
    if not USERNAME_PATTERN.fullmatch(username):
        raise InvalidRepositoryError("maintainer must be a valid GitHub username")
    return username


def scan_repository(
    client: GitHubClient,
    repository: str,
    *,
    maintainer: str | None = None,
    lookback_days: int = 365,
    now: datetime | None = None,
) -> HealthReport:
    slug = validate_repository_slug(repository)
    maintainer_name = validate_username(maintainer) if maintainer else None
    if not 1 <= lookback_days <= 3650:
        raise ValueError("lookback_days must be between 1 and 3650")

    generated = _as_utc(now or datetime.now(timezone.utc))
    cutoff = generated - timedelta(days=lookback_days)
    cutoff_text = cutoff.isoformat().replace("+00:00", "Z")
    encoded_slug = "/".join(quote(part, safe="") for part in slug.split("/"))
    root = f"/repos/{encoded_slug}"

    repo = client.get(root)
    if not isinstance(repo, dict):
        raise GitHubAPIError(500, "unexpected repository response", root)
    if repo.get("private") is True:
        raise PrivateRepositoryError("private repositories are outside this tool's scope")

    contributors, contributors_truncated = client.paginate(
        f"{root}/contributors", params={"anon": "true"}, max_pages=3
    )
    commits, commits_truncated = client.paginate(
        f"{root}/commits", params={"since": cutoff_text}, max_pages=5
    )
    pulls, pulls_truncated = client.paginate(
        f"{root}/pulls",
        params={"state": "all", "sort": "updated", "direction": "desc"},
        max_pages=5,
    )
    issues, issues_truncated = client.paginate(
        f"{root}/issues",
        params={"state": "all", "sort": "updated", "direction": "desc", "since": cutoff_text},
        max_pages=5,
    )
    releases, releases_truncated = client.paginate(
        f"{root}/releases", max_pages=3
    )

    recent_pulls = [item for item in pulls if _within(item.get("updated_at"), cutoff)]
    merged_pulls = [item for item in recent_pulls if _within(item.get("merged_at"), cutoff)]
    recent_issues = [
        item
        for item in issues
        if "pull_request" not in item and _within(item.get("updated_at"), cutoff)
    ]
    closed_issues = [item for item in recent_issues if _within(item.get("closed_at"), cutoff)]
    recent_releases = [
        item
        for item in releases
        if not item.get("draft") and _within(item.get("published_at"), cutoff)
    ]

    community_raw = client.get(f"{root}/community/profile", allow_not_found=True)
    community = community_raw if isinstance(community_raw, dict) else {}
    community_files = community.get("files") if isinstance(community.get("files"), dict) else {}
    workflows = client.get(f"{root}/contents/.github/workflows", allow_not_found=True)
    changelog = client.get(f"{root}/contents/CHANGELOG.md", allow_not_found=True)
    files = {
        "readme": bool(community_files.get("readme")),
        "license": bool(community_files.get("license") or repo.get("license")),
        "contributing": bool(community_files.get("contributing")),
        "code_of_conduct": bool(
            community_files.get("code_of_conduct") or community_files.get("code_of_conduct_file")
        ),
        "security_policy": bool(community_files.get("security")),
        "issue_template": bool(community_files.get("issue_template")),
        "pull_request_template": bool(community_files.get("pull_request_template")),
        "ci_workflows": isinstance(workflows, list) and bool(workflows),
        "changelog": changelog is not None,
    }

    owner = str((repo.get("owner") or {}).get("login") or "")
    owner_match = maintainer_name.casefold() == owner.casefold() if maintainer_name else None
    contributor_commits = _contributor_commits(contributors, maintainer_name)
    permission, permission_verified = _permission(client, root, maintainer_name)

    repository_snapshot = RepositorySnapshot(
        slug=str(repo.get("full_name") or slug),
        name=str(repo.get("name") or slug.split("/", 1)[1]),
        owner=owner,
        url=str(repo.get("html_url") or f"https://github.com/{slug}"),
        description=repo.get("description") if isinstance(repo.get("description"), str) else None,
        default_branch=str(repo.get("default_branch") or ""),
        is_fork=bool(repo.get("fork")),
        is_archived=bool(repo.get("archived")),
        license=_license_id(repo.get("license")),
        created_at=str(repo.get("created_at") or ""),
        pushed_at=str(repo["pushed_at"]) if repo.get("pushed_at") else None,
        updated_at=str(repo.get("updated_at") or ""),
    )
    adoption = AdoptionSnapshot(
        stars=_integer(repo.get("stargazers_count")),
        forks=_integer(repo.get("forks_count")),
        # GitHub's watchers_count is a legacy alias for stars. subscribers_count
        # is the number shown by the repository's Watch control.
        watchers=_integer(repo.get("subscribers_count")),
        contributors=len(contributors),
        contributors_truncated=contributors_truncated,
    )
    activity = ActivitySnapshot(
        lookback_days=lookback_days,
        window_start=cutoff_text,
        commits=len(commits),
        commits_truncated=commits_truncated,
        pull_requests_updated=len(recent_pulls),
        merged_pull_requests=len(merged_pulls),
        pull_requests_truncated=pulls_truncated,
        issues_updated=len(recent_issues),
        closed_issues=len(closed_issues),
        issues_truncated=issues_truncated,
        releases_published=len(recent_releases),
        releases_truncated=releases_truncated,
    )
    community_snapshot = CommunitySnapshot(
        health_percentage=_optional_integer(community.get("health_percentage")),
        files=files,
    )
    maintainer_snapshot = MaintainerSnapshot(
        username=maintainer_name,
        owner_match=owner_match,
        contributor_commits=contributor_commits,
        collaborator_permission=permission,
        permission_verified=permission_verified,
    )
    findings = _build_findings(
        repository_snapshot,
        adoption,
        activity,
        community_snapshot,
        maintainer_snapshot,
        cutoff,
    )

    html_root = repository_snapshot.url.rstrip("/")
    source_urls = {
        "repository": html_root,
        "commits": f"{html_root}/commits/{repository_snapshot.default_branch}",
        "pull_requests": f"{html_root}/pulls",
        "issues": f"{html_root}/issues",
        "releases": f"{html_root}/releases",
        "contributors": f"{html_root}/graphs/contributors",
        "community": f"{html_root}/community",
        "api": f"https://api.github.com/repos/{slug}",
    }
    caveats = (
        "This is a read-only snapshot of public GitHub data, not a quality score or prediction.",
        "GitHub stars, forks, and contributor counts need project context and should not be treated as quality measures.",
        "Activity and contributor enumeration is bounded; a count marked as truncated is a lower bound.",
        "Collaborator permission is reported only when GitHub returns it to the authenticated caller.",
        "Metrics can change after the generated timestamp and should be refreshed before use.",
    )
    return HealthReport(
        schema_version="1.0",
        generated_at=generated.isoformat().replace("+00:00", "Z"),
        repository=repository_snapshot,
        adoption=adoption,
        activity=activity,
        community=community_snapshot,
        maintainer=maintainer_snapshot,
        findings=tuple(findings),
        source_urls=source_urls,
        caveats=caveats,
    )


def _permission(
    client: GitHubClient, root: str, maintainer: str | None
) -> tuple[str | None, bool]:
    if not maintainer or not client.authenticated:
        return None, False
    try:
        response = client.get(
            f"{root}/collaborators/{quote(maintainer, safe='')}/permission",
            allow_not_found=True,
        )
    except GitHubAPIError as exc:
        if exc.status in {403, 404}:
            return None, False
        raise
    if not isinstance(response, dict) or not isinstance(response.get("permission"), str):
        return None, False
    return response["permission"], True


def _contributor_commits(contributors: list[Any], maintainer: str | None) -> int | None:
    if not maintainer:
        return None
    for contributor in contributors:
        if not isinstance(contributor, dict):
            continue
        login = contributor.get("login")
        if isinstance(login, str) and login.casefold() == maintainer.casefold():
            return _integer(contributor.get("contributions"))
    return 0


def _build_findings(
    repository: RepositorySnapshot,
    adoption: AdoptionSnapshot,
    activity: ActivitySnapshot,
    community: CommunitySnapshot,
    maintainer: MaintainerSnapshot,
    cutoff: datetime,
) -> list[Finding]:
    findings: list[Finding] = []
    if repository.is_fork:
        findings.append(Finding("source-repository", "warning", "Repository is a fork; upstream popularity does not establish maintenance of this fork."))
    else:
        findings.append(Finding("source-repository", "pass", "Repository is a source repository rather than a fork."))

    if repository.is_archived:
        findings.append(Finding("repository-current", "warning", "Repository is archived and read-only."))
    else:
        findings.append(Finding("repository-current", "pass", "Repository is not archived."))

    if _within(repository.pushed_at, cutoff):
        findings.append(Finding("recent-push", "pass", f"Repository was pushed within the {activity.lookback_days}-day window."))
    else:
        findings.append(Finding("recent-push", "warning", f"No repository push was observed within the {activity.lookback_days}-day window."))

    if activity.commits:
        findings.append(Finding("recent-commits", "pass", f"Observed {_display_count(activity.commits, activity.commits_truncated)} commits in the lookback window."))
    else:
        findings.append(Finding("recent-commits", "warning", "No commits were observed in the lookback window."))

    if activity.releases_published:
        findings.append(Finding("recent-releases", "pass", f"Observed {_display_count(activity.releases_published, activity.releases_truncated)} published releases in the lookback window."))
    else:
        findings.append(Finding("recent-releases", "info", "No published release was observed in the lookback window; release cadence varies by project type."))

    for key, label in (("readme", "README"), ("license", "license")):
        level = "pass" if community.files.get(key) else "warning"
        verb = "is present" if community.files.get(key) else "was not detected"
        findings.append(Finding(f"community-{key}", level, f"A {label} {verb}."))

    for key, label in (
        ("security_policy", "security policy"),
        ("contributing", "contributing guide"),
        ("ci_workflows", "CI workflow"),
    ):
        level = "pass" if community.files.get(key) else "info"
        verb = "is present" if community.files.get(key) else "was not detected"
        findings.append(Finding(f"community-{key}", level, f"A {label} {verb}."))

    if adoption.stars == 0 and adoption.forks == 0 and adoption.contributors <= 1:
        findings.append(Finding("visible-adoption", "warning", "No independent adoption signal is visible in stars, downstream forks, or additional contributors."))
    else:
        findings.append(Finding("visible-adoption", "info", "Visible adoption metrics were collected; interpret them with project context."))

    if maintainer.username is None:
        findings.append(Finding("maintainer-role", "info", "No maintainer username was supplied, so maintainer context was not evaluated."))
    elif maintainer.permission_verified and maintainer.collaborator_permission in {"admin", "maintain", "write"}:
        findings.append(Finding("maintainer-role", "pass", f"GitHub verified {maintainer.collaborator_permission} permission for @{maintainer.username}."))
    elif maintainer.owner_match:
        findings.append(Finding("maintainer-role", "pass", f"@{maintainer.username} matches the repository owner; ongoing responsibilities still require separate evidence."))
    else:
        findings.append(Finding("maintainer-role", "warning", f"Maintainer permission for @{maintainer.username} was not verified."))
    return findings


def _within(value: Any, cutoff: datetime) -> bool:
    if not isinstance(value, str) or not value:
        return False
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return False
    return _as_utc(parsed) >= cutoff


def _as_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def _integer(value: Any) -> int:
    return value if isinstance(value, int) and not isinstance(value, bool) else 0


def _optional_integer(value: Any) -> int | None:
    return value if isinstance(value, int) and not isinstance(value, bool) else None


def _license_id(value: Any) -> str | None:
    if not isinstance(value, dict):
        return None
    spdx = value.get("spdx_id")
    return spdx if isinstance(spdx, str) and spdx != "NOASSERTION" else None


def _display_count(value: int, truncated: bool) -> str:
    return f"at least {value}" if truncated else str(value)
