#!/usr/bin/env python3
"""Apply reviewed variable_dictionary.csv metadata to GLC datasets.json."""

import argparse
import csv
import json
import re
from collections import Counter
from pathlib import Path

from apply_audited_semantic_terms import apply as apply_semantic_terms
from apply_audited_semantic_terms import load_mapping as load_semantic_mapping


QUANTITATIVE_TYPES = {"numeric", "integer"}
PARTICIPANT_PREFIX = re.compile(r"^[A-Z][A-Z0-9]*_S\d+_")
SPLIT_DEVICE_SUFFIX = re.compile(r"_AL\d+$")


def clean_text(value: str) -> str:
    return (
        str(value or "")
        .replace("<U+00A0>", " ")
        .replace("<U+FB01>", "fi")
        .strip()
    )


def source_table_from_file_group(file_group: dict) -> str:
    names = file_group.get("dataset_file_names") or []
    if not names:
        raise ValueError("File group has no dataset_file_names")
    stems = set()
    for name in names:
        stem = Path(name).stem
        stem = PARTICIPANT_PREFIX.sub("", stem)
        stem = SPLIT_DEVICE_SUFFIX.sub("", stem)
        stems.add(stem)
    if len(stems) != 1:
        raise ValueError(f"File group maps to multiple source tables: {sorted(stems)}")
    return stems.pop()


def load_dictionary(path: Path) -> dict:
    rows = {}
    with path.open(newline="", encoding="utf-8-sig") as handle:
        for row in csv.DictReader(handle):
            key = (row["source_table"], row["variable_name"])
            if key in rows:
                raise ValueError(f"Duplicate dictionary key: {key}")
            rows[key] = row
    return rows


def factor_levels(row: dict) -> list[dict]:
    labels = [
        clean_text(value)
        for value in row.get("factor_levels", "").split(" | ")
        if clean_text(value)
    ]
    source = row["source_table"]
    name = row["variable_name"]
    coded_device_factor = (
        source in {"light_chest", "light_glasses", "light_wrist"}
        and name in {"ORIENTATION", "STATE"}
    )
    # Genuine R factors are exported to CSV as their one-based internal
    # positions. Numeric device-code columns remain represented by the
    # actual codes already present in their source data.
    values = labels if coded_device_factor else [
        str(index) for index in range(1, len(labels) + 1)
    ]
    return [
        {
            "value": value,
            "label": f"Code {value}" if coded_device_factor else label,
            **(
                {"description": "Code meaning requires confirmation from ActLumus documentation."}
                if coded_device_factor
                else {}
            ),
        }
        for value, label in zip(values, labels)
    ]


def term_label(term: str) -> str:
    replacements = {
        "edi": "EDI",
        "meq": "MEQ",
        "vlsq8": "VLSQ-8",
        "ase": "ASE",
    }
    words = term.split("_")
    return " ".join(replacements.get(word, word.capitalize()) for word in words)


def apply_dictionary(records: list, dictionary: dict) -> tuple[Counter, list[str]]:
    counts = Counter()
    unresolved_units = []
    unmatched = []

    for dataset in records:
        used_terms = set()
        for group_index, file_group in enumerate(dataset.get("dataset_file", []), start=1):
            source_table = source_table_from_file_group(file_group)
            for variable in file_group.get("dataset_file_variables", []):
                name = variable.get("dataset_file_variables_name")
                row = dictionary.get((source_table, name))
                if row is None:
                    if source_table in {"acttrust_wrist", "MPI_ambient_rooftop"}:
                        continue
                    unmatched.append(
                        f"{dataset.get('dataset_internal_id')} file group {group_index}: "
                        f"{source_table}.{name}"
                    )
                    continue

                label = clean_text(row["proposed_label"])
                description = clean_text(row.get("proposed_description", ""))
                variable_type = row["proposed_type"]
                unit = clean_text(row.get("proposed_unit", ""))
                term = row["proposed_semantic_term"]

                variable["dataset_file_variables_labels"] = label
                if description:
                    variable["dataset_file_variables_description"] = description
                else:
                    variable.pop("dataset_file_variables_description", None)

                variable["dataset_file_variables_type"] = variable_type
                if variable_type in QUANTITATIVE_TYPES:
                    if unit:
                        variable["dataset_file_variables_units"] = unit
                    else:
                        variable.pop("dataset_file_variables_units", None)
                        unresolved_units.append(
                            f"{dataset.get('dataset_internal_id')} file group {group_index}: "
                            f"{source_table}.{name}"
                        )
                else:
                    variable.pop("dataset_file_variables_units", None)

                if variable_type == "factor":
                    levels = factor_levels(row)
                    if not levels:
                        raise ValueError(f"Factor has no levels: {source_table}.{name}")
                    variable["dataset_file_variables_factor_levels"] = levels
                else:
                    variable.pop("dataset_file_variables_factor_levels", None)

                variable["dataset_file_variables_term"] = {"variable_term": term}
                if term == "other":
                    variable["dataset_file_variables_term"]["variable_name"] = label
                used_terms.add(term)
                counts["updated"] += 1
                counts[f"type:{variable_type}"] += 1
                counts[f"term:{term}"] += 1

        if unmatched:
            continue
        dataset["dataset_variable_terms"] = [
            {"term": term, "label": term_label(term)}
            for term in sorted(used_terms)
        ]

    if unmatched:
        details = "\n".join(f"- {item}" for item in unmatched)
        raise ValueError(f"Unmatched metadata variables:\n{details}")
    return counts, unresolved_units


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("dictionary_csv", type=Path)
    parser.add_argument("datasets_json", type=Path)
    parser.add_argument(
        "--allow-unresolved-units",
        action="store_true",
        help="Write metadata even when quantitative units remain unresolved.",
    )
    args = parser.parse_args()

    dictionary = load_dictionary(args.dictionary_csv)
    records = json.loads(args.datasets_json.read_text(encoding="utf-8"))
    counts, unresolved_units = apply_dictionary(records, dictionary)

    if unresolved_units and not args.allow_unresolved_units:
        unique = sorted(
            {
                item.split(": ", 1)[1]
                for item in unresolved_units
            }
        )
        details = "\n".join(f"- {item}" for item in unique)
        raise SystemExit(
            "Quantitative variables with unresolved units remain. "
            "No file was written:\n"
            f"{details}"
        )

    semantic_mapping_path = Path(__file__).resolve().parent / "semantic_term_mapping.csv"
    semantic_updates = apply_semantic_terms(
        records,
        load_semantic_mapping(semantic_mapping_path),
    )

    args.datasets_json.write_text(
        json.dumps(records, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    print(f"Applied {semantic_updates} reviewed semantic-term mappings.")
    print(f"Updated {counts['updated']} variable entries.")
    print(
        "Types: "
        + ", ".join(
            f"{key.removeprefix('type:')}={value}"
            for key, value in sorted(counts.items())
            if key.startswith("type:")
        )
    )
    print(f"Unresolved quantitative-unit entries: {len(unresolved_units)}")


if __name__ == "__main__":
    main()
