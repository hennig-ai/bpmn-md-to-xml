"""Create a ZIP file for Claude.ai Cowork upload.

Builds the skill zip with:
- Cowork-specific SKILL.md (replaces the normal SKILL.md)
- Bundled wheels for offline installation
- Forward slashes for Linux compatibility
"""

import zipfile
import os
from pathlib import Path

# Paths relative to this script's location
SCRIPT_DIR: Path = Path(__file__).resolve().parent
REPO_ROOT: Path = SCRIPT_DIR.parent
SKILL_DIR: Path = REPO_ROOT
ZIP_OUTPUT: Path = REPO_ROOT / "bpmn-md-to-xml-skill.zip"
COWORK_SKILL_MD: Path = SCRIPT_DIR / "SKILL.md"
WHEELS: list[Path] = sorted(SCRIPT_DIR.glob("*.whl"))

ZIP_PREFIX: str = "bpmn-md-to-xml"
INCLUDE_DIRS: set[str] = {"references", "scripts"}
INCLUDE_FILES: set[str] = {"SKILL.md"}
ROOT_FILES: set[str] = {"pyproject.toml"}
EXCLUDE_DIRS: set[str] = {"__pycache__"}

if not WHEELS:
    raise FileNotFoundError(f"No .whl files found in {SCRIPT_DIR}")

with zipfile.ZipFile(ZIP_OUTPUT, "w", zipfile.ZIP_DEFLATED) as zf:
    # Pack skill files
    for filename in sorted(INCLUDE_FILES):
        filepath: Path = SKILL_DIR / filename
        arcname: str = f"{ZIP_PREFIX}/{filename}"
        if filename == "SKILL.md":
            zf.write(COWORK_SKILL_MD, arcname)
            print(f"  + {arcname} (from cowork/SKILL.md)")
        else:
            zf.write(filepath, arcname)
            print(f"  + {arcname}")

    # Pack root-level files
    for filename in sorted(ROOT_FILES):
        filepath = REPO_ROOT / filename
        arcname = f"{ZIP_PREFIX}/{filename}"
        zf.write(filepath, arcname)
        print(f"  + {arcname}")

    # Pack skill directories
    for dir_name in sorted(INCLUDE_DIRS):
        dir_path: Path = SKILL_DIR / dir_name
        for root, dirs, files in os.walk(dir_path):
            dirs[:] = [d for d in dirs if d not in EXCLUDE_DIRS]
            for filename in files:
                filepath = Path(root) / filename
                rel_path: str = str(filepath.relative_to(SKILL_DIR)).replace(os.sep, "/")
                arcname = f"{ZIP_PREFIX}/{rel_path}"
                zf.write(filepath, arcname)
                print(f"  + {arcname}")

    # Add wheels from cowork/
    for whl in WHEELS:
        arcname = f"{ZIP_PREFIX}/wheels/{whl.name}"
        zf.write(whl, arcname)
        print(f"  + {arcname}")

print(f"\nCreated: {ZIP_OUTPUT}")
