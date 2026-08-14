#!/usr/bin/env python3
"""Freeze a source-pinned ARC12 all-training transfer cohort from filenames only."""

from __future__ import annotations

import argparse
import sys

import freeze_arc12_filename_holdout as freezer


DEFAULT_ALLOCATION = {"training": 25}
DEFAULT_SALT = "arc123-filename-only-training-holdout-v1"
DEFAULT_ARTIFACT_ID = "ARC12-FILENAME-ONLY-TRAINING-HOLDOUT-001"
DEFAULT_TITLE = "ARC12 Fresh Filename-Only All-Training 25+25 Holdout"
DEFAULT_COHORT_KEY = "frozen_filename_only_training_50"
DEFAULT_CLAIM_BOUNDARY = (
    "This cohort is frozen before any selected task is parsed, visualized, scored, or used "
    "for operator design. Selection reads only benchmark labels, split names, and filenames. "
    "The all-training allocation is required because the remaining ARC-AGI-2 evaluation "
    "filenames cannot supply a new 25-task disjoint holdout. Selected source JSON bytes are "
    "read only as opaque SHA-256 integrity commitments; their JSON content is not decoded by "
    "this freezer."
)


def main() -> int:
    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument(
        "--per-benchmark-task-count",
        type=int,
        default=DEFAULT_ALLOCATION["training"],
    )
    arguments, forwarded_arguments = parser.parse_known_args()
    if arguments.per_benchmark_task_count < 1:
        raise ValueError("per-benchmark task count must be positive")
    settings = {
        "DEFAULT_ALLOCATION": {"training": arguments.per_benchmark_task_count},
        "DEFAULT_SALT": DEFAULT_SALT,
        "DEFAULT_ARTIFACT_ID": DEFAULT_ARTIFACT_ID,
        "DEFAULT_TITLE": DEFAULT_TITLE,
        "DEFAULT_COHORT_KEY": DEFAULT_COHORT_KEY,
        "DEFAULT_CLAIM_BOUNDARY": DEFAULT_CLAIM_BOUNDARY,
    }
    originals = {name: getattr(freezer, name) for name in settings}
    original_arguments = sys.argv
    try:
        sys.argv = [sys.argv[0], *forwarded_arguments]
        for name, value in settings.items():
            setattr(freezer, name, value)
        return freezer.main()
    finally:
        sys.argv = original_arguments
        for name, value in originals.items():
            setattr(freezer, name, value)


if __name__ == "__main__":
    raise SystemExit(main())
