#!/usr/bin/env python3
"""Reconstruct the split manifest from verified participant CSV outputs."""

import csv
import re
import sys
from pathlib import Path


def main() -> None:
    root = Path(sys.argv[1])
    imported = root / "data" / "imported"
    records = []
    for path in sorted(imported.rglob("MPI_S*_*.csv")):
        match = re.match(r"(MPI_S\d{3})_(.+)\.csv$", path.name)
        if not match:
            continue
        participant, stem = match.groups()
        with path.open(newline="", encoding="utf-8-sig") as handle:
            reader = csv.reader(handle)
            header = next(reader)
            rows = sum(1 for _ in reader)
        relative_dir = path.parent.relative_to(imported)
        source_relative = Path("data/imported") / relative_dir / f"{stem}.RData"
        records.append({
            "source_file": source_relative.as_posix(),
            "source_object": "sleepdiary" if stem == "sleepdiaries" else stem,
            "participant_id": participant,
            "output_file": path.relative_to(root).as_posix(),
            "rows": rows,
            "columns": len(header),
        })
    if not records:
        raise SystemExit("No participant CSV files found")
    with (root / "split_manifest.csv").open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(records[0]))
        writer.writeheader()
        writer.writerows(records)
    print(f"Reconstructed manifest for {len(records)} participant CSV files.")


if __name__ == "__main__":
    main()
