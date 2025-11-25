from __future__ import annotations
import pathlib
from setuptools import setup, find_packages

HERE = pathlib.Path(__file__).parent


def read_text(path: pathlib.Path) -> str:
    try:
        return path.read_text(encoding="utf8")
    except Exception:
        return ""


long_description = read_text(HERE / "README.md")


def read_version() -> str:
    import re

    p = HERE / "cereon_sdk" / "_version.py"
    try:
        txt = p.read_text(encoding="utf8")
        m = re.search(r"^__version__\s*=\s*['\"]([^'\"]+)['\"]", txt, flags=re.M)
        if m:
            return m.group(1)
    except Exception:
        pass
    return "0.0.0"


setup(
    name="cereon_sdk",
    version=read_version(),
    description="Generic, typed, and streaming FastAPI backend for Cereon Dashboard cards.",
    long_description=long_description,
    long_description_content_type="text/markdown",
    author="Aditya Mishra",
    author_email="adimis.sde@gmail.com",
    url="https://github.com/adimis-ai/cereon-sdk",
    packages=find_packages(exclude=("tests", "tests.*")),
    include_package_data=True,
    install_requires=[
        "fastapi>=0.110.0",
        "pydantic>=2.6.0",
        "typing-extensions>=4.9.0",
    ],
    python_requires=">=3.10",
    classifiers=[
        "Programming Language :: Python :: 3",
        "Framework :: FastAPI",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
)
