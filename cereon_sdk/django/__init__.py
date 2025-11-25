"""Django integration helpers for cereon-sdk.

This module intentionally keeps imports lightweight and side-effect free so
it is safe to import at Django startup (e.g. in `INSTALLED_APPS` or
`settings`). Public submodules are made available for convenience.

Typical usage:

	from cereon_sdk.django import views, consumers

Only import submodules when accessed to avoid expensive imports during
application startup.
"""

from importlib import import_module
from typing import Any

__all__ = ["consumers", "serializers", "utils", "views", "__version__"]


def __getattr__(name: str) -> Any:
	"""Lazily import submodules on attribute access.

	This keeps `import cereon_sdk.django` cheap while allowing
	`cereon_sdk.django.views` and friends to be accessed normally.
	"""
	if name in {"consumers", "serializers", "utils", "views"}:
		module = import_module(f"{__package__}.{name}")
		globals()[name] = module
		return module

	if name == "__version__":
		try:
			# Prefer top-level package version if available
			pkg = import_module("cereon_sdk")
			version = getattr(pkg, "__version__", None)
			if version is not None:
				globals()["__version__"] = version
				return version
		except Exception:
			pass
		# Fallback when not available
		globals()["__version__"] = "0.0.0"
		return "0.0.0"

	raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


def __dir__() -> list[str]:
	return sorted(list(globals().keys()) + ["consumers", "serializers", "utils", "views", "__version__"])

