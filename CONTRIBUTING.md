
# Contributing to cereon-sdk

Welcome! `cereon-sdk` is a Python package built to support FastAPI-based backends and typed Pydantic models used by the Cereon platform. This guide covers local setup, testing, linting, packaging and publishing.

## Local development

Prerequisites:
- Python 3.11+
- pipx / virtualenv / tox (recommended for isolation)

1. Create and activate a virtual environment:
	- python -m venv .venv
	- source .venv/bin/activate

2. Install development dependencies defined in `pyproject.toml` or `Pipfile`:
	- `pip install -e .[dev]` (if project supports extras)

3. Run quick checks:
	- Linting/formatting: `ruff .` and `black .`
	- Type checks: `mypy .` (if configured)

## Tests

- Run tests with `pytest -q` from the repository root or with `tox` if configured.
- Add unit tests for new models, routes, and utilities. Keep tests deterministic and fast.

## Linting & formatting

- Formatting: Black. Run `black .`.
- Linting: Ruff/Flake8. Run `ruff .`.
- Imports: isort (if configured).

## Packaging and publishing

Build a distributable locally:

1. Build wheel and sdist: `python -m build`
2. Inspect artifacts under `dist/`.
3. Upload to TestPyPI for verification: `twine upload --repository testpypi dist/*`.

Coordinate official PyPI releases with the repository maintainers. Follow semantic versioning for releases.

## Commits & PRs

- Use conventional commits to auto-generate changelogs and version bumps (e.g., `fix`, `feat`, `chore`).
- Open PRs with a clear description and test coverage for changes.

## Developer notes

- Keep Pydantic models stable; migrating model fields is a breaking change that must be documented and versioned.
- Where possible, add type hints and run mypy to keep typing quality high.

Thank you for contributing to cereon-sdk!
