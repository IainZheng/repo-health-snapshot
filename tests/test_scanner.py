from __future__ import annotations

import unittest
from datetime import datetime, timezone
from typing import Any

from repo_health_snapshot.errors import InvalidRepositoryError, PrivateRepositoryError
from repo_health_snapshot.scanner import scan_repository, validate_repository_slug


NOW = datetime(2026, 8, 11, 12, 0, tzinfo=timezone.utc)


class FakeClient:
    def __init__(self, *, private: bool = False, fork: bool = False, authenticated: bool = True):
        self.authenticated = authenticated
        self.private = private
        self.fork = fork
        self.calls: list[tuple[str, str]] = []

    def get(self, path: str, *, params=None, allow_not_found: bool = False) -> Any:
        self.calls.append(("get", path))
        if path == "/repos/acme/widget":
            return {
                "full_name": "acme/widget",
                "name": "widget",
                "owner": {"login": "acme"},
                "html_url": "https://github.com/acme/widget",
                "description": "A synthetic public widget.",
                "default_branch": "main",
                "private": self.private,
                "fork": self.fork,
                "archived": False,
                "license": {"spdx_id": "MIT"},
                "created_at": "2024-01-01T00:00:00Z",
                "pushed_at": "2026-08-10T00:00:00Z",
                "updated_at": "2026-08-10T00:00:00Z",
                "stargazers_count": 12,
                "forks_count": 3,
                "watchers_count": 12,
                "subscribers_count": 2,
            }
        if path.endswith("/community/profile"):
            return {
                "health_percentage": 88,
                "files": {
                    "readme": {"url": "public"},
                    "license": {"url": "public"},
                    "contributing": {"url": "public"},
                    "code_of_conduct": {"url": "public"},
                    "security": {"url": "public"},
                    "issue_template": {"url": "public"},
                    "pull_request_template": {"url": "public"},
                },
            }
        if path.endswith("/contents/.github/workflows"):
            return [{"name": "ci.yml"}]
        if path.endswith("/contents/CHANGELOG.md"):
            return {"name": "CHANGELOG.md"}
        if path.endswith("/collaborators/acme/permission"):
            return {"permission": "admin"}
        return None

    def paginate(self, path: str, *, params=None, max_pages: int = 5):
        self.calls.append(("paginate", path))
        if path.endswith("/contributors"):
            return [
                {"login": "acme", "contributions": 42},
                {"login": "helper", "contributions": 3},
            ], False
        if path.endswith("/commits"):
            return [{"sha": "a"}, {"sha": "b"}], False
        if path.endswith("/pulls"):
            return [
                {
                    "updated_at": "2026-08-01T00:00:00Z",
                    "merged_at": "2026-08-02T00:00:00Z",
                },
                {
                    "updated_at": "2024-01-01T00:00:00Z",
                    "merged_at": None,
                },
            ], False
        if path.endswith("/issues"):
            return [
                {
                    "updated_at": "2026-07-01T00:00:00Z",
                    "closed_at": "2026-07-02T00:00:00Z",
                },
                {
                    "updated_at": "2026-07-01T00:00:00Z",
                    "closed_at": None,
                    "pull_request": {"url": "public"},
                },
            ], False
        if path.endswith("/releases"):
            return [
                {"published_at": "2026-06-01T00:00:00Z", "draft": False},
                {"published_at": "2026-07-01T00:00:00Z", "draft": True},
            ], False
        raise AssertionError(f"unexpected pagination path: {path}")


class ScannerTests(unittest.TestCase):
    def test_scan_separates_repository_activity_and_maintainer_context(self):
        report = scan_repository(
            FakeClient(),
            "acme/widget",
            maintainer="acme",
            lookback_days=365,
            now=NOW,
        )

        self.assertEqual(report.repository.slug, "acme/widget")
        self.assertFalse(report.repository.is_fork)
        self.assertEqual(report.adoption.stars, 12)
        self.assertEqual(report.adoption.watchers, 2)
        self.assertEqual(report.adoption.contributors, 2)
        self.assertEqual(report.activity.commits, 2)
        self.assertEqual(report.activity.pull_requests_updated, 1)
        self.assertEqual(report.activity.merged_pull_requests, 1)
        self.assertEqual(report.activity.issues_updated, 1)
        self.assertEqual(report.activity.closed_issues, 1)
        self.assertEqual(report.activity.releases_published, 1)
        self.assertEqual(report.maintainer.collaborator_permission, "admin")
        self.assertTrue(report.maintainer.permission_verified)
        self.assertTrue(report.community.files["ci_workflows"])
        self.assertTrue(report.community.files["changelog"])
        self.assertIn("not a quality score or prediction", report.caveats[0].lower())

    def test_private_repository_is_rejected_before_secondary_collection(self):
        client = FakeClient(private=True)

        with self.assertRaises(PrivateRepositoryError):
            scan_repository(client, "acme/widget", now=NOW)

        self.assertEqual(client.calls, [("get", "/repos/acme/widget")])

    def test_fork_is_reported_as_warning(self):
        report = scan_repository(FakeClient(fork=True), "acme/widget", now=NOW)

        finding = next(item for item in report.findings if item.code == "source-repository")
        self.assertEqual(finding.level, "warning")
        self.assertIn("upstream popularity", finding.message)

    def test_permission_is_not_claimed_without_authentication(self):
        report = scan_repository(
            FakeClient(authenticated=False),
            "acme/widget",
            maintainer="helper",
            now=NOW,
        )

        self.assertFalse(report.maintainer.permission_verified)
        self.assertIsNone(report.maintainer.collaborator_permission)
        self.assertEqual(report.maintainer.contributor_commits, 3)

    def test_invalid_repository_slug_is_rejected(self):
        for invalid in ("acme", "../private", "https://github.com/acme/widget", "acme/widget/extra"):
            with self.subTest(invalid=invalid):
                with self.assertRaises(InvalidRepositoryError):
                    validate_repository_slug(invalid)


if __name__ == "__main__":
    unittest.main()
