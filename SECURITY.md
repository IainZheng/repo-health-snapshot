# Security Policy

## Supported versions

Security fixes are provided for the latest released minor version.

## Reporting a vulnerability

Use GitHub's private vulnerability reporting or a private security advisory for this repository when available. Do not place tokens, private-repository metadata, proof-of-concept secrets, or personal data in a public issue.

If private reporting is unavailable, open a public issue that contains only a short request for a private contact channel. Do not disclose the vulnerability details in that issue.

## Security boundaries

- The CLI is read-only and uses the fixed GitHub API origin `https://api.github.com`.
- Repository identifiers are validated before they are used in a request path.
- Tokens are read only from the `GITHUB_TOKEN` environment variable and are never included in reports.
- Private repositories are rejected even if the supplied token can read them.
- Output paths are local and never uploaded automatically.

Reports can contain public usernames and metadata. Users are responsible for reviewing reports before sharing them.

