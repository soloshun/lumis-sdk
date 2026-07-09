# Contributing to OpenARIA

Thanks for contributing. OpenARIA is a small, safety-focused research proof of concept, so small, well-tested changes are preferred.

## Before you contribute

- Discuss substantial changes in an issue before investing in a pull request.
- Use only original code, public documentation, and synthetic or public data.
- Never submit credentials, private logs, customer information, employer/client code, runbooks, or architecture material.
- Keep v0.1 focused on diagnosis and recommendations; production remediation is out of scope.

## Local setup

```bash
uv sync --all-groups
uv run ruff format --check .
uv run ruff check .
uv run mypy src
uv run pytest
```

## Pull requests

- Keep the pull request focused and explain the user-visible behavior.
- Add or update tests for code changes.
- Update documentation and examples when behavior changes.
- Do not add secrets to commits, fixtures, screenshots, or issue text.

We welcome contributions to code, examples, cookbook recipes, and documentation. Changes to homepage messaging, branding, roadmap, sponsorship links, or product positioning are controlled by maintainers and may require prior discussion.
