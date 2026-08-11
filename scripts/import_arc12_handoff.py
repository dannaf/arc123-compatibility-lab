#!/usr/bin/env python3
"""Import a source-pinned, live-safe ARC12 cohort index into ARC123."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPOSITORY_ROOT / "src"))

from arc123.arc12_import import (
    OUTPUT_NAME,
    validate_arc12_cohort_import,
    write_arc12_cohort_import,
)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--arc12-root", required=True, type=Path)
    parser.add_argument("--commit", required=True)
    parser.add_argument(
        "--source-repository",
        default="https://github.com/dannaf/arc12-compatibility-lab",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=REPOSITORY_ROOT / "research" / "cohorts" / OUTPUT_NAME,
    )
    arguments = parser.parse_args()
    payload = write_arc12_cohort_import(
        arguments.arc12_root,
        arguments.commit,
        arguments.source_repository,
        arguments.output,
    )
    print(json.dumps(validate_arc12_cohort_import(arguments.output), indent=2, sort_keys=True))
    print(json.dumps({"output": str(arguments.output), "artifact_id": payload["artifact_id"]}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
