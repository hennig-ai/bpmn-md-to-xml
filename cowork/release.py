"""Create and push a cowork release tag from the version in pyproject.toml.

Usage:
    python cowork/release.py
"""

import re
import subprocess
from pathlib import Path


REPO_ROOT: Path = Path(__file__).resolve().parent.parent
PYPROJECT: Path = REPO_ROOT / "pyproject.toml"
TAG_PREFIX: str = "cowork-v"


def read_version() -> str:
    content: str = PYPROJECT.read_text(encoding="utf-8")
    match = re.search(r'^version\s*=\s*"([^"]+)"', content, re.MULTILINE)
    if match is None:
        raise ValueError(f"No version found in {PYPROJECT}")
    return match.group(1)


def run(cmd: list[str]) -> None:
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(f"Command failed: {' '.join(cmd)}\n{result.stderr}")
    if result.stdout.strip():
        print(result.stdout.strip())


def main() -> None:
    version: str = read_version()
    tag: str = f"{TAG_PREFIX}{version}"

    print(f"Version : {version}")
    print(f"Tag     : {tag}")
    print()

    run(["git", "tag", tag])
    print(f"Created tag: {tag}")

    run(["git", "push", "origin", tag])
    print(f"Pushed tag:  {tag}")
    print()
    print("GitHub Actions workflow is now running.")
    print(f"https://github.com/hennig-ai/bpmn-md-to-xml-private/releases/tag/{tag}")


if __name__ == "__main__":
    main()
