import unittest

from repo_health_snapshot.client import GitHubClient


class GitHubClientTests(unittest.TestCase):
    def test_build_url_uses_fixed_origin_and_encodes_query(self):
        client = GitHubClient()

        url = client._build_url("/repos/acme/widget", {"state": "all", "page": 2})

        self.assertEqual(
            url,
            "https://api.github.com/repos/acme/widget?state=all&page=2",
        )

    def test_build_url_rejects_absolute_url(self):
        client = GitHubClient()

        with self.assertRaises(ValueError):
            client._build_url("https://example.com/private")

    def test_build_url_rejects_parent_traversal(self):
        client = GitHubClient()

        with self.assertRaises(ValueError):
            client._build_url("/repos/acme/../private")

    def test_authenticated_reflects_token_presence(self):
        self.assertFalse(GitHubClient().authenticated)
        self.assertTrue(GitHubClient(token="synthetic-test-token").authenticated)


if __name__ == "__main__":
    unittest.main()
