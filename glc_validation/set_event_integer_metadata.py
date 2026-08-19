#!/usr/bin/env python3
"""Declare ActLumus EVENT variables as integer codes."""

from __future__ import annotations

import argparse
import json
from pathlib import Path


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("datasets_json", type=Path)
    args = parser.parse_args()

    datasets = json.loads(args.datasets_json.read_text(encoding="utf-8"))
    updated = 0
    for dataset in datasets:
        for file_group in dataset.get("dataset_file", []):
            names = set(file_group.get("dataset_file_names", []))
            if not names or not all("/sensor/" in f"/{name}" for name in names):
                continue
            for variable in file_group.get("dataset_file_variables", []):
                if variable.get("dataset_file_variables_name") != "EVENT":
                    continue
                variable["dataset_file_variables_labels"] = "Event marker code"
                variable["dataset_file_variables_description"] = (
                    "Integer event-marker code exported by the ActLumus device; "
                    "code meanings require ActLumus documentation."
                )
                variable["dataset_file_variables_type"] = "integer"
                variable["dataset_file_variables_units"] = "{event_code}"
                variable.pop("dataset_file_variables_factor_levels", None)
                updated += 1

    if updated == 0:
        raise SystemExit("No ActLumus EVENT metadata entries found")
    args.datasets_json.write_text(
        json.dumps(datasets, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(f"Updated {updated} ActLumus EVENT metadata entries.")


if __name__ == "__main__":
    main()
