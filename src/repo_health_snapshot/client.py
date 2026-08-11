from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any, Mapping
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from .errors import GitHubAPIError, RateLimitError, RepoHealthError


API_ORIGIN = "https://api.github.com"


@dataclass(frozen=True)
class Page:
    data: Any
    has_next: bool


class GitHubClient:
    """Minimal read-only GitHub REST client with bounded pagination."""

    def __init__(
        self,
        *,
        token: str | None = None,
        timeout: float = 15.0,
        user_agent: str = "repo-health-snapshot/0.1.0",
    ) -> None:
        if timeout <= 0:
            raise ValueError("timeout must be positive")
        self._token = token or None
        self.timeout = timeout
        self.user_agent = user_agent

    @property
    def authenticated(self) -> bool:
        return self._token is not None

    def _build_url(self, path: str, params: Mapping[str, Any] | None = None) -> str:
        if not path.startswith("/") or "://" in path or "\x00" in path:
            raise ValueError("GitHub API path must be a relative absolute path")
        if any(part == ".." for part in path.split("/")):
            raise ValueError("GitHub API path cannot contain parent traversal")
        query = urlencode(params or {}, doseq=True)
        return f"{API_ORIGIN}{path}" + (f"?{query}" if query else "")

    def get_page(
        self,
        path: str,
        *,
        params: Mapping[str, Any] | None = None,
        allow_not_found: bool = False,
    ) -> Page | None:
        url = self._build_url(path, params)
        headers = {
            "Accept": "application/vnd.github+json",
            "User-Agent": self.user_agent,
            "X-GitHub-Api-Version": "2022-11-28",
        }
        if self._token:
            headers["Authorization"] = f"Bearer {self._token}"
        request = Request(url, headers=headers, method="GET")

        try:
            with urlopen(request, timeout=self.timeout) as response:
                payload = response.read().decode("utf-8")
                data = json.loads(payload)
                link = response.headers.get("Link", "")
                return Page(data=data, has_next='rel="next"' in link)
        except HTTPError as exc:
            if exc.code == 404 and allow_not_found:
                return None
            body = exc.read().decode("utf-8", errors="replace")
            message = _safe_api_message(body)
            remaining = exc.headers.get("X-RateLimit-Remaining", "")
            error_type = RateLimitError if exc.code in {403, 429} and remaining == "0" else GitHubAPIError
            raise error_type(exc.code, message, path) from None
        except URLError as exc:
            reason = str(exc.reason)[:240]
            raise RepoHealthError(f"Could not reach GitHub API: {reason}") from None
        except json.JSONDecodeError:
            raise RepoHealthError(f"GitHub API returned invalid JSON for {path}") from None

    def get(
        self,
        path: str,
        *,
        params: Mapping[str, Any] | None = None,
        allow_not_found: bool = False,
    ) -> Any:
        page = self.get_page(path, params=params, allow_not_found=allow_not_found)
        return None if page is None else page.data

    def paginate(
        self,
        path: str,
        *,
        params: Mapping[str, Any] | None = None,
        max_pages: int = 5,
    ) -> tuple[list[Any], bool]:
        if max_pages < 1:
            raise ValueError("max_pages must be at least one")

        collected: list[Any] = []
        base_params = dict(params or {})
        base_params.setdefault("per_page", 100)

        for page_number in range(1, max_pages + 1):
            page_params = dict(base_params)
            page_params["page"] = page_number
            page = self.get_page(path, params=page_params)
            assert page is not None
            if not isinstance(page.data, list):
                raise RepoHealthError(f"Expected a list response from {path}")
            collected.extend(page.data)
            if not page.has_next:
                return collected, False

        return collected, True


def _safe_api_message(body: str) -> str:
    try:
        parsed = json.loads(body)
        if isinstance(parsed, dict) and isinstance(parsed.get("message"), str):
            return parsed["message"][:240]
    except json.JSONDecodeError:
        pass
    return "request failed"
