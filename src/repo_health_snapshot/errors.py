class RepoHealthError(Exception):
    """Base class for expected command failures."""


class GitHubAPIError(RepoHealthError):
    """A GitHub API request failed."""

    def __init__(self, status: int, message: str, path: str) -> None:
        self.status = status
        self.message = message
        self.path = path
        super().__init__(f"GitHub API returned {status} for {path}: {message}")


class RateLimitError(GitHubAPIError):
    """GitHub rejected a request because the current rate limit was exhausted."""


class PrivateRepositoryError(RepoHealthError):
    """The requested repository is private and outside this tool's scope."""


class InvalidRepositoryError(RepoHealthError):
    """The repository identifier is not a safe owner/name slug."""
