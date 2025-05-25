from __future__ import annotations

import os


def main() -> None:
    cwd = os.path.dirname(__file__)
    package_dir = os.path.abspath(os.path.join(cwd, ".."))
    os.system(f"cookiecutter {package_dir}")  # noqa: S605 | No injection, retrieving path in OS
