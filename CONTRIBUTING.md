# Contributing to cereon-sdk

Thanks for wanting to contribute — we appreciate improvements, bug reports, tests, documentation, and examples.

This document explains how to get the project running locally, the contribution workflow, coding standards, testing, and release guidance. Follow these guidelines to keep the project maintainable and pleasant to work on.

Quick links

- Repository: https://github.com/adimis-ai/cereon-sdk
- Issues: https://github.com/adimis-ai/cereon-sdk/issues

Table of contents

- Local development setup
- Coding standards
- Tests and CI
- Commit and PR process
- Reporting issues and feature requests
- Releasing
- Getting help

## Local development setup

Prerequisites

- Python 3.10 or newer (see `pyproject.toml`).
- Git and a GitHub account.
- Optional but recommended: `virtualenv`/`venv` or a tool like `pipx`.

Get the code and create an isolated environment:

```bash
git clone https://github.com/adimis-ai/cereon-sdk.git
cd cereon-sdk
python -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
```

Install in editable mode with development extras (this installs linters and test tools):

```bash
pip install -e .[dev]
```

If you will work on framework integrations, install the extras for those frameworks:

```bash
pip install -e .[fastapi]
pip install -e .[django]
```

Install and run pre-commit hooks (recommended):

```bash
pre-commit install
pre-commit run --all-files
```

## Coding standards

- Formatting: `black` (configured in `pyproject.toml`, line-length 100).
- Imports: `isort` (Black profile).
- Linting: `ruff` and optional `mypy` checks.
- Type hints: Prefer typed public APIs and follow existing package patterns.

Run formatters and linters before creating a PR:

```bash
black .
ruff check .
```

## Tests and CI

Tests use `pytest`. Run the full test suite with:

```bash
pytest -q
```

Run a subset of tests by path or marker to speed up feedback loops.

CI runs on GitHub Actions. PRs must pass the test and linting matrix before merging.

## Commit and PR process

- Create branches from `main` using a descriptive name: `feat/<summary>` or `fix/<summary>`.
- Keep commits focused and include a clear message. Use Conventional Commits when possible (`feat:`, `fix:`, `chore:`, etc.).
- Rebase or squash to maintain a clean history before merging.
- Open a PR to `main` with a detailed description and testing notes; link related issues.
- Request at least one review from a project maintainer.

### Merge checklist

- All CI checks pass.
- Changes are well-documented (README, docstrings, or CHANGELOG if applicable).
- Tests added for new behavior or bug fixes.

## Reporting issues and feature requests

- Provide a concise title and reproduction steps.
- Include environment details (Python version, OS) and traceback or logs.
- For feature requests, explain the use case and suggested API.

## Releasing

Releases use `hatchling` as the build backend. Typical steps (maintainers only):

1. Update the version in `pyproject.toml` and `cereon_sdk/_version.py`.
2. Update `CHANGELOG.md` with notable changes.
3. Create a release tag and push to GitHub. CI may publish distributions to PyPI.

If you do not have release access, open an issue requesting a release with the target version and changelog notes.

## Getting help

- Usage questions: open an issue.
- Design or breaking-change proposals: open a discussion or RFC-style issue and tag it `rfc`.

Thank you for contributing — your work improves Cereon for everyone!

# Contributing to cereon-sdk
