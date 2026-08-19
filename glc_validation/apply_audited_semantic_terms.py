#!/usr/bin/env python3
"""Apply a reviewed resource-variable semantic-term mapping to datasets.json."""

from __future__ import annotations

import argparse
import csv
import json
import os
import re
from pathlib import Path


PARTICIPANT_PREFIX = re.compile(r"^(?:IZTECH|KNUST|BAUA|UCR|FUSPCEU|MPI)_S\d+_")
SPLIT_DEVICE_SUFFIX = re.compile(r"_AL\d+$")


def resource_name(path: str) -> str:
    stem = Path(os.path.basename(path)).stem
    stem = PARTICIPANT_PREFIX.sub("", stem)
    return SPLIT_DEVICE_SUFFIX.sub("", stem)


def load_mapping(path: Path) -> dict[tuple[str, str], tuple[str, str]]:
    mapping = {}
    with path.open(newline="", encoding="utf-8-sig") as handle:
        for row in csv.DictReader(handle):
            key = (row["resource"], row["variable"])
            value = (row["suggested_term"], row["other_variable_name"])
            if key in mapping and mapping[key] != value:
                raise ValueError(f"Conflicting mapping for {key}")
            mapping[key] = value
    return mapping


def term_label(term: str) -> str:
    abbreviations = {
        "ase": "ASE",
        "edi": "EDI",
        "leba": "LEBA",
        "meq": "MEQ",
        "vlsq8": "VLSQ-8",
        "who5": "WHO-5",
    }
    return " ".join(abbreviations.get(word, word.capitalize()) for word in term.split("_"))


def apply(records: list[dict], mapping: dict[tuple[str, str], tuple[str, str]]) -> int:
    updated = 0
    unmatched = set()
    for dataset in records:
        used_terms = set()
        for group in dataset.get("dataset_file", []):
            paths = group.get("dataset_file_names") or []
            if not paths:
                continue
            resources = {resource_name(path) for path in paths}
            if len(resources) != 1:
                raise ValueError(f"File group spans multiple resources: {sorted(resources)}")
            resource = resources.pop()
            for variable in group.get("dataset_file_variables", []):
                name = variable.get("dataset_file_variables_name", "")
                value = mapping.get((resource, name))
                if value is None:
                    if resource in {"acttrust_wrist", "MPI_ambient_rooftop"}:
                        existing = variable.get("dataset_file_variables_term", {}).get("variable_term")
                        if existing:
                            used_terms.add(existing)
                        continue
                    unmatched.add((resource, name))
                    continue
                term, other_name = value
                semantic = {"variable_term": term}
                if term == "other":
                    semantic["variable_name"] = other_name or name
                variable["dataset_file_variables_term"] = semantic
                used_terms.add(term)
                updated += 1
        dataset["dataset_variable_terms"] = [
            {"term": term, "label": term_label(term)}
            for term in sorted(used_terms)
        ]

    if unmatched:
        details = "\n".join(f"- {resource}.{variable}" for resource, variable in sorted(unmatched))
        raise ValueError(f"Variables missing from reviewed mapping:\n{details}")
    return updated


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("mapping_csv", type=Path)
    parser.add_argument("datasets_json", type=Path)
    args = parser.parse_args()

    records = json.loads(args.datasets_json.read_text(encoding="utf-8"))
    updated = apply(records, load_mapping(args.mapping_csv))
    args.datasets_json.write_text(
        json.dumps(records, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    print(f"Updated {updated} variable entries in {args.datasets_json}")


if __name__ == "__main__":
    main()
