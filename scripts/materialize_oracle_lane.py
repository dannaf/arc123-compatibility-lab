#!/usr/bin/env python3
"""Materialize source-pinned offline ARC12/ARC3 IHL GT artifacts."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPOSITORY_ROOT / "src"))

from arc123.oracles import materialize_oracle_lane


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--arc12-root", required=True, type=Path)
    parser.add_argument("--arc12-commit", required=True)
    parser.add_argument("--singularityml-root", required=True, type=Path)
    parser.add_argument("--singularityml-commit", required=True)
    parser.add_argument(
        "--output-root",
        type=Path,
        default=REPOSITORY_ROOT / "research" / "oracle_materializations",
    )
    arguments = parser.parse_args()
    result = materialize_oracle_lane(
        arguments.arc12_root,
        arguments.arc12_commit,
        arguments.singularityml_root,
        arguments.singularityml_commit,
        arguments.output_root,
    )
    print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
