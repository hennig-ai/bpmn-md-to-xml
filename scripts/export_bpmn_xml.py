"""Export BPMN process models from MD files to BPMN 2.0 XML format.

Loads the BPMN schema and hierarchy, then initializes the navigator
with the given data file. Exports all processes as .bpmn files.

Exit Codes:
    0: Export successful
    1: Export failed
    2: System error

Usage:
    python export_bpmn_xml.py <data_file> <output_dir>

Layout assumption:
    This script expects a ``references/`` directory at the project root
    containing ``bpmn-schema.md`` and ``bpmn-hierarchy.md``::

        bpmn-md-to-xml/
            scripts/
                export_bpmn_xml.py
            references/
                bpmn-schema.md
                bpmn-hierarchy.md

    ``<root>`` is derived as ``__file__/../../``; no absolute path or
    CLI argument for the metadata directory is required.
"""

import sys
import re
from pathlib import Path

from basic_framework import proc_frame_start, proc_frame_end
from basic_framework.proc_frame import log_and_raise
from bpmn_lib.navigator import create_navigator

from bpmn_xml_exporter import BpmnXmlExporter

SCHEMA_FILENAME: str = "bpmn-schema.md"
HIERARCHY_FILENAME: str = "bpmn-hierarchy.md"


def get_version() -> str:
    """Reads the project version from pyproject.toml.

    Locates pyproject.toml relative to this module and extracts the
    version from the [project] section using a regex pattern.

    Returns:
        The version number as string (e.g. "1.0.0")

    Raises:
        FileNotFoundError: If pyproject.toml is not found
        ValueError: If version cannot be extracted
    """
    project_root: Path = Path(__file__).parent.parent
    pyproject_path: Path = project_root / "pyproject.toml"

    if not pyproject_path.exists():
        log_and_raise(FileNotFoundError(f"pyproject.toml not found: {pyproject_path}"))

    content: str = pyproject_path.read_text(encoding="utf-8")
    match: re.Match[str] | None = re.search(r'^version\s*=\s*"([^"]+)"', content, re.MULTILINE)

    if match is None:
        log_and_raise(ValueError(f"version not found in {pyproject_path}"))

    return match.group(1)


def main() -> None:
    """Main function - initializes navigator and exports BPMN XML files."""
    proc_frame_start("export_bpmn_xml", get_version(), error_only=True)

    try:
        if len(sys.argv) < 3:
            log_and_raise(ValueError(
                "Usage: python export_bpmn_xml.py <data_file> <output_dir>"
            ))

        print("Exporting BPMN model...")

        data_file: str = sys.argv[1]
        output_dir: Path = Path(sys.argv[2])
        metadata_dir: Path = (Path(__file__).parent.parent / "references").resolve()
        schema_file: str = str(metadata_dir / SCHEMA_FILENAME)
        hierarchy_file: str = str(metadata_dir / HIERARCHY_FILENAME)

        navigator = create_navigator(
            schema_file=schema_file,
            data_file=data_file,
            hierarchy_file=hierarchy_file,
            report_target=sys.stdout,
        )

        exporter: BpmnXmlExporter = BpmnXmlExporter(navigator)
        exported_files: list[Path] = exporter.export(output_dir)

        print(f"Export successful. {len(exported_files)} file(s) written to {output_dir}")
        proc_frame_end()

    except Exception as e:
        print(f"Export failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
