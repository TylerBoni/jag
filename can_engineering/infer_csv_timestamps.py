#!/usr/bin/env python3
"""Fill missing CAN CSV timestamps using the observed aggregate frame rate."""

from __future__ import annotations

import argparse
import os
import tempfile
from pathlib import Path


DEFAULT_FRAME_RATE = 1172.25


def timestamp_is_missing(value: str) -> bool:
    try:
        return not value.strip() or float(value) == 0
    except ValueError:
        return False


def file_needs_timestamps(path: Path) -> bool:
    with path.open("r", encoding="utf-8", newline="") as source:
        header = source.readline()
        if header.split(",", 1)[0].strip().lower() != "time stamp":
            raise ValueError(f"{path}: first column is not 'Time Stamp'")

        found_row = False
        for line in source:
            if not line.strip():
                continue
            found_row = True
            if not timestamp_is_missing(line.split(",", 1)[0]):
                return False
        return found_row


def infer_timestamps(path: Path, frame_rate: float) -> bool:
    if not file_needs_timestamps(path):
        return False

    fd, temporary_name = tempfile.mkstemp(
        dir=path.parent, prefix=f".{path.name}.", suffix=".tmp"
    )
    try:
        with (
            path.open("r", encoding="utf-8", newline="") as source,
            os.fdopen(fd, "w", encoding="utf-8", newline="") as destination,
        ):
            destination.write(source.readline())
            frame_index = 0
            for line in source:
                if not line.strip():
                    destination.write(line)
                    continue
                _, separator, remainder = line.partition(",")
                if not separator:
                    raise ValueError(f"{path}: malformed row {frame_index + 2}")
                destination.write(f"{frame_index / frame_rate:.6f},{remainder}")
                frame_index += 1

        os.replace(temporary_name, path)
        return True
    except BaseException:
        try:
            os.unlink(temporary_name)
        except FileNotFoundError:
            pass
        raise


def default_csv_paths() -> list[Path]:
    return sorted(Path("gm_can_bus").rglob("*.csv"))


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Infer elapsed timestamps for CAN CSVs whose timestamp column is all zero."
    )
    parser.add_argument("paths", nargs="*", type=Path, help="CSV files (default: gm_can_bus/**/*.csv)")
    parser.add_argument(
        "--frame-rate",
        type=float,
        default=DEFAULT_FRAME_RATE,
        help=f"aggregate CAN frames per second (default: {DEFAULT_FRAME_RATE})",
    )
    args = parser.parse_args()

    if args.frame_rate <= 0:
        parser.error("--frame-rate must be greater than zero")

    paths = args.paths or default_csv_paths()
    for path in paths:
        changed = infer_timestamps(path, args.frame_rate)
        print(f"{'updated' if changed else 'kept'} {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
