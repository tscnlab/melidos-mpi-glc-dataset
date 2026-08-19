#!/usr/bin/env python3
"""Populate questionnaire collection datetimes from the best available evidence."""

from __future__ import annotations

import argparse
import csv
import json
import re
from datetime import datetime, timedelta
from pathlib import Path
from xml.etree import ElementTree
from zipfile import ZipFile


RECOVERABLE = {
    "acceptability": ("discharge", "mTFA", "acceptabi_timestamp"),
    "ase": ("discharge", "ASE", "your_sleep_environment_ase_timestamp"),
    "evaluation": ("discharge", "feedback", "light_glasses_evaluation_timestamp"),
    "leba": ("discharge", "LEBA", "your_light_behaviour_leba_timestamp"),
    "vlsq8": ("discharge", "VLSQ8", "your_light_sensitivity_vlsq8_timestamp"),
}

SCREENING_QUESTIONNAIRES = {"chronotype", "demographics", "health"}
PARTICIPANT_PATTERN = r"[A-Z][A-Z0-9]*_S\d+"
XML_NAMESPACE = {
    "m": "http://schemas.openxmlformats.org/spreadsheetml/2006/main"
}


def participant_id(dataset: dict) -> str:
    match = re.search(rf"({PARTICIPANT_PATTERN})$", dataset["dataset_internal_id"])
    if not match:
        raise ValueError(
            f"Cannot determine participant from {dataset['dataset_internal_id']!r}"
        )
    return match.group(1)


def file_group_type(file_group: dict) -> str | None:
    names = file_group.get("dataset_file_names", [])
    if len(names) != 1:
        return None
    match = re.match(rf"{PARTICIPANT_PATTERN}_(.+)\.csv$", Path(names[0]).name)
    return match.group(1) if match else None


def raw_export(raw_root: Path, participant: str, group_type: str) -> Path | None:
    directory, token, _ = RECOVERABLE[group_type]
    # MPI stores each end-of-study instrument in a group-level export.
    candidates = sorted((raw_root / "group" / directory).glob(f"*_{token}_*.csv"))
    if not candidates:
        return None
    if len(candidates) != 1:
        raise ValueError(
            f"Expected one raw {group_type} export for {participant}, "
            f"found {len(candidates)}"
        )
    return candidates[0]


def survey_timestamp(path: Path, timestamp_marker: str, participant: str) -> str:
    with path.open(encoding="utf-8-sig", newline="") as handle:
        sample = handle.read(8192)
        handle.seek(0)
        dialect = csv.Sniffer().sniff(sample, delimiters=",;")
        rows = [
            row for row in csv.DictReader(handle, dialect=dialect)
            if row.get("record_id", "").strip() == participant
        ]
    timestamp_columns = [
        name
        for name in (rows[0].keys() if rows else [])
        if isinstance(name, str) and timestamp_marker in name.lower()
    ]
    values = {
        row[name].strip()
        for row in rows
        for name in timestamp_columns
        if row.get(name, "").strip()
    }
    if len(values) != 1:
        raise ValueError(
            f"Expected one unique embedded survey timestamp in {path}, "
            f"found {sorted(values)!r}"
        )
    value = values.pop()
    for date_format in (
        "%Y-%m-%d %H:%M:%S",
        "%m/%d/%Y %H:%M",
        "%m/%d/%Y %H:%M:%S",
    ):
        try:
            return datetime.strptime(value, date_format).strftime("%Y-%m-%d %H:%M:%S")
        except ValueError:
            pass
    raise ValueError(f"Unsupported survey timestamp {value!r} in {path}")


def screening_datetimes(workbook: Path) -> dict[str, str]:
    """Read participant screening timestamps from the study-dates XLSX workbook."""
    with ZipFile(workbook) as archive:
        shared_xml = ElementTree.fromstring(
            archive.read("xl/sharedStrings.xml")
        )
        shared_strings = [
            "".join(
                node.text or ""
                for node in item.findall(".//m:t", XML_NAMESPACE)
            )
            for item in shared_xml.findall("m:si", XML_NAMESPACE)
        ]
        sheet_xml = ElementTree.fromstring(
            archive.read("xl/worksheets/sheet1.xml")
        )

    rows: list[dict[str, str]] = []
    for row in sheet_xml.findall(".//m:sheetData/m:row", XML_NAMESPACE):
        values: dict[str, str] = {}
        for cell in row.findall("m:c", XML_NAMESPACE):
            column = re.match(r"[A-Z]+", cell.attrib["r"]).group()
            value_node = cell.find("m:v", XML_NAMESPACE)
            value = "" if value_node is None else value_node.text or ""
            if cell.attrib.get("t") == "s" and value:
                value = shared_strings[int(value)]
            values[column] = value
        rows.append(values)

    header = {column: value for column, value in rows[0].items()}
    column_for = {name: column for column, name in header.items()}
    required = {"subjectID_device", "datetime_inperson_screen"}
    if not required.issubset(column_for):
        return {}

    result: dict[str, str] = {}
    for row in rows[1:]:
        subject_device = row.get(column_for["subjectID_device"], "")
        match = re.match(rf"({PARTICIPANT_PATTERN})_", subject_device)
        serial = row.get(column_for["datetime_inperson_screen"], "")
        if not match or not serial:
            continue
        timestamp = datetime(1899, 12, 30) + timedelta(days=float(serial))
        rendered = timestamp.strftime("%Y-%m-%d %H:%M:%S")
        participant = match.group(1)
        previous = result.setdefault(participant, rendered)
        if previous != rendered:
            raise ValueError(
                f"Conflicting screening datetimes for {participant}: "
                f"{previous!r} and {rendered!r}"
            )
    return result


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("raw_root", type=Path)
    parser.add_argument("study_dates_xlsx", type=Path)
    parser.add_argument("datasets_json", type=Path)
    args = parser.parse_args()

    datasets = json.loads(args.datasets_json.read_text(encoding="utf-8"))
    screening_by_participant = screening_datetimes(args.study_dates_xlsx)
    recovered = 0
    screening_assigned = 0

    for dataset in datasets:
        participant = participant_id(dataset)
        for file_group in dataset.get("dataset_file", []):
            group_type = file_group_type(file_group)
            if group_type in RECOVERABLE:
                _, _, timestamp_marker = RECOVERABLE[group_type]
                export = raw_export(args.raw_root, participant, group_type)
                if export is None:
                    continue
                timestamp = survey_timestamp(
                    export,
                    timestamp_marker,
                    participant,
                )
                file_group["dataset_file_datetime"] = {
                    "dataset_file_datetime_source": "collection",
                    "dataset_file_datetime_date": timestamp,
                    "dataset_file_datetime_dateformat": "YYYY-MM-DD HH:mm:ss",
                }
                recovered += 1
            elif group_type in SCREENING_QUESTIONNAIRES:
                timestamp = screening_by_participant.get(participant)
                if not timestamp:
                    continue
                file_group["dataset_file_datetime"] = {
                    "dataset_file_datetime_source": "collection",
                    "dataset_file_datetime_date": timestamp,
                    "dataset_file_datetime_dateformat": "YYYY-MM-DD HH:mm:ss",
                }
                file_group["dataset_file_description"] = (
                    "This questionnaire was part of participant screening and "
                    "contains no embedded completion timestamp. Its collection "
                    "datetime is represented by the participant's in-person "
                    "screening timestamp recorded in the study-dates workbook."
                )
                screening_assigned += 1

    args.datasets_json.write_text(
        json.dumps(datasets, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(f"Recovered {recovered} questionnaire datetimes.")
    print(
        f"Assigned {screening_assigned} screening-questionnaire datetimes "
        "from datetime_inperson_screen; existing fallbacks were retained "
        "where that field was unavailable."
    )


if __name__ == "__main__":
    main()
