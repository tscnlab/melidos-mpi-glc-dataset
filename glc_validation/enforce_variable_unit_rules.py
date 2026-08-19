#!/usr/bin/env python3
"""Apply GLC variable unit applicability rules to datasets metadata."""

import argparse
import json
from pathlib import Path


QUANTITATIVE_TYPES = {"numeric", "integer"}
PLACEHOLDER_UNITS = {"n/a", "na", "unknown"}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("datasets_json", type=Path)
    args = parser.parse_args()

    records = json.loads(args.datasets_json.read_text(encoding="utf-8"))
    removed = 0
    invalid_quantitative = []

    for dataset in records:
        dataset_id = dataset.get("dataset_internal_id", "<unknown>")
        for group_index, file_group in enumerate(dataset.get("dataset_file", []), start=1):
            for variable in file_group.get("dataset_file_variables", []):
                variable_type = variable.get("dataset_file_variables_type")
                name = variable.get("dataset_file_variables_name", "<unknown>")
                if variable_type not in QUANTITATIVE_TYPES:
                    if "dataset_file_variables_units" in variable:
                        del variable["dataset_file_variables_units"]
                        removed += 1
                    continue

                unit = str(variable.get("dataset_file_variables_units", "")).strip()
                if not unit or unit.lower() in PLACEHOLDER_UNITS:
                    invalid_quantitative.append(
                        f"{dataset_id} file group {group_index}, variable {name}"
                    )

    if invalid_quantitative:
        details = "\n".join(f"- {item}" for item in invalid_quantitative)
        raise SystemExit(f"Quantitative variables require meaningful units:\n{details}")

    args.datasets_json.write_text(
        json.dumps(records, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    print(f"Removed units from {removed} non-quantitative variable entries.")


if __name__ == "__main__":
    main()
