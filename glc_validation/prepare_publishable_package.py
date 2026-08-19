#!/usr/bin/env python3
"""Reorganize a built MeLiDos package into its publishable repository layout."""

from __future__ import annotations

import argparse
import json
import shutil
from pathlib import Path, PurePosixPath


def destination_for(relative_path: Path) -> Path:
    if relative_path.parts[0] == "light":
        return Path("data/files/sensor") / Path(*relative_path.parts[1:])
    if relative_path.parts[0] == "continuous":
        return Path("data/files/longitudinal-reports") / Path(
            *relative_path.parts[1:]
        )
    if relative_path.parts[0] == "environmental":
        return Path("data/files/environmental") / Path(*relative_path.parts[1:])
    if relative_path.name.endswith("_trial_times.csv"):
        return Path("data/files/study-timing") / relative_path.name
    return Path("data/files/questionnaires") / relative_path.name


def normalized_source(name: str) -> PurePosixPath:
    parts = [part for part in PurePosixPath(name).parts if part != "."]
    return PurePosixPath(*parts)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("package_root", type=Path)
    args = parser.parse_args()

    root = args.package_root.resolve()
    imported = root / "data" / "imported"
    datasets_path = root / "data" / "datasets.json"
    if not imported.is_dir() or not datasets_path.is_file():
        raise SystemExit("Expected data/imported/ and data/datasets.json")

    mapping: dict[str, str] = {}
    source_files = sorted(
        path
        for path in imported.rglob("*")
        if path.is_file() and path.name != ".DS_Store"
    )
    for source in source_files:
        relative = source.relative_to(imported)
        destination_relative = destination_for(relative)
        destination = root / destination_relative
        destination.parent.mkdir(parents=True, exist_ok=True)
        if destination.exists():
            raise FileExistsError(destination)
        shutil.move(source, destination)
        old = str(PurePosixPath("data/imported") / PurePosixPath(relative.as_posix()))
        mapping[old] = destination_relative.as_posix()

    datasets = json.loads(datasets_path.read_text(encoding="utf-8"))
    references_updated = 0
    for dataset in datasets:
        for file_group in dataset.get("dataset_file", []):
            names = []
            for name in file_group.get("dataset_file_names", []):
                normalized = normalized_source(name).as_posix()
                if normalized not in mapping:
                    raise KeyError(f"No new path for referenced file {name!r}")
                names.append(mapping[normalized])
                references_updated += 1
            file_group["dataset_file_names"] = names

    datasets_path.write_text(
        json.dumps(datasets, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )

    for unwanted in sorted(imported.rglob(".DS_Store")):
        unwanted.unlink()
    for directory in sorted(imported.rglob("*"), reverse=True):
        if directory.is_dir():
            directory.rmdir()
    imported.rmdir()

    missing = [
        name
        for dataset in datasets
        for file_group in dataset.get("dataset_file", [])
        for name in file_group.get("dataset_file_names", [])
        if not (root / name).is_file()
    ]
    if missing:
        raise FileNotFoundError(f"Missing reorganized files: {missing}")

    print(f"Moved {len(source_files)} dataset files.")
    print(f"Updated {references_updated} metadata references.")


if __name__ == "__main__":
    main()
