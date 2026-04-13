"""Install git hooks for this repository.

Usage:
    python cowork/install_hooks.py
"""

from pathlib import Path

REPO_ROOT: Path = Path(__file__).resolve().parent.parent
HOOKS_DIR: Path = REPO_ROOT / ".git" / "hooks"
PRE_PUSH_HOOK: Path = HOOKS_DIR / "pre-push"

PRE_PUSH_CONTENT: str = """\
#!/bin/sh
# Pre-push reminders for main and cowork branches

branch=$(git symbolic-ref HEAD 2>/dev/null | sed 's|refs/heads/||')

if [ "$branch" = "cowork" ]; then
    version=$(grep '^version' pyproject.toml | sed 's/version = "//;s/"//')
    tag="cowork-v$version"
    existing=$(git tag -l "$tag")
    if [ -z "$existing" ]; then
        echo ""
        echo "   WARNING: No release tag found for version $version."
        echo "  Run 'python cowork/release.py' to create tag '$tag'."
        echo "  WITHOUT THIS TAG NO ZIP WILL BE BUILT AND NO GITHUB RELEASE WILL BE CREATED."
        echo ""
    fi
fi

if [ "$branch" = "main" ]; then
    missing=$(git log cowork-main-baseline..main --oneline 2>/dev/null)
    if [ -n "$missing" ]; then
        echo ""
        echo "  REMINDER: New commits on 'main' since last baseline — not yet on 'cowork':"
        echo "$missing" | sed 's/^/    /'
        echo "  To update the baseline run: git tag -f cowork-main-baseline"
        echo ""
    fi
fi

exit 0
"""


def main() -> None:
    PRE_PUSH_HOOK.write_text(PRE_PUSH_CONTENT, encoding="utf-8")
    PRE_PUSH_HOOK.chmod(0o755)
    print(f"Installed: {PRE_PUSH_HOOK}")


if __name__ == "__main__":
    main()
