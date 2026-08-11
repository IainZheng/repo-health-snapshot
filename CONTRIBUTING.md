# Contributing

Thank you for helping make repository-health discussions more transparent and reproducible.

## Before opening a change

1. Search existing issues and pull requests.
2. For behavior changes, open an issue describing the health signal and the public source that can support it.
3. Do not include private repository data, access tokens, personal contact information, unpublished material, or confidential text.

## Local workflow

```bash
python -m unittest discover -s tests -v
python -m compileall -q src
```

Changes should include focused tests. Network calls in tests are not allowed; use synthetic fixtures or a fake client.

## Design principles

- Prefer verifiable observations over composite scores or predictions.
- Label incomplete counts and unavailable permissions explicitly.
- Keep GitHub access read-only and least-privileged.
- Never infer project quality or maintainer authority from stars, forks, or upstream popularity.
- Avoid dependencies unless they materially improve safety or correctness.

## Pull requests

Keep pull requests small and explain:

- what snapshot behavior changes;
- why the source is authoritative;
- how privacy and rate limits are handled; and
- which tests verify the change.

By contributing, you agree that your contribution is licensed under the MIT License.
