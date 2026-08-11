from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any


@dataclass(frozen=True)
class RepositorySnapshot:
    slug: str
    name: str
    owner: str
    url: str
    description: str | None
    default_branch: str
    is_fork: bool
    is_archived: bool
    license: str | None
    created_at: str
    pushed_at: str | None
    updated_at: str


@dataclass(frozen=True)
class AdoptionSnapshot:
    stars: int
    forks: int
    watchers: int
    contributors: int
    contributors_truncated: bool


@dataclass(frozen=True)
class ActivitySnapshot:
    lookback_days: int
    window_start: str
    commits: int
    commits_truncated: bool
    pull_requests_updated: int
    merged_pull_requests: int
    pull_requests_truncated: bool
    issues_updated: int
    closed_issues: int
    issues_truncated: bool
    releases_published: int
    releases_truncated: bool


@dataclass(frozen=True)
class CommunitySnapshot:
    health_percentage: int | None
    files: dict[str, bool]


@dataclass(frozen=True)
class MaintainerSnapshot:
    username: str | None
    owner_match: bool | None
    contributor_commits: int | None
    collaborator_permission: str | None
    permission_verified: bool


@dataclass(frozen=True)
class Finding:
    code: str
    level: str
    message: str


@dataclass(frozen=True)
class HealthReport:
    schema_version: str
    generated_at: str
    repository: RepositorySnapshot
    adoption: AdoptionSnapshot
    activity: ActivitySnapshot
    community: CommunitySnapshot
    maintainer: MaintainerSnapshot
    findings: tuple[Finding, ...] = field(default_factory=tuple)
    source_urls: dict[str, str] = field(default_factory=dict)
    caveats: tuple[str, ...] = field(default_factory=tuple)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)
