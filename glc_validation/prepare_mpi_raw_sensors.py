#!/usr/bin/env python3
"""Prepare MPI raw-only ActTrust and rooftop ActLumus streams for GLC packaging."""

import csv
import re
import sys
from datetime import datetime, timedelta
from pathlib import Path


FINAL_IDS = [
    f"MPI_S{number:03d}"
    for number in (201, 202, 204, 205, 206, 208, 209, 210, 212, 213, 214,
                   215, 216, 218, 219, 221, 222, 223, 224, 225, 226, 227,
                   228, 229, 230, 231)
]


def excel_datetime(value):
    return datetime(1899, 12, 30) + timedelta(days=float(value))


def read_windows(path):
    with path.open(newline="", encoding="utf-8-sig") as handle:
        rows = list(csv.DictReader(handle))
    if len(rows) != len(FINAL_IDS):
        raise ValueError(f"Expected 26 trial-time rows, found {len(rows)}")
    return {
        final_id: (excel_datetime(row["datetime_trial_start"]),
                   excel_datetime(row["datetime_trial_end"]))
        for final_id, row in zip(FINAL_IDS, rows)
    }


def parse_condor(path):
    lines = path.read_text(encoding="utf-8-sig", errors="replace").splitlines()
    header_index = next(i for i, line in enumerate(lines) if line.startswith("DATE/TIME;"))
    reader = csv.DictReader(lines[header_index:], delimiter=";")
    for row in reader:
        if not row.get("DATE/TIME"):
            continue
        timestamp = datetime.strptime(row["DATE/TIME"], "%d/%m/%Y %H:%M:%S")
        yield timestamp, row


def normalized(row, participant_id=""):
    output = {"file.name": row.pop("__source_file")}
    if participant_id:
        output = {"Id": participant_id, **output}
    output["Datetime"] = row.pop("DATE/TIME")
    rename = {
        "EXT TEMPERATURE": "EXT.TEMPERATURE",
        "AMB LIGHT": "AMB.LIGHT",
        "RED LIGHT": "RED.LIGHT",
        "GREEN LIGHT": "GREEN.LIGHT",
        "BLUE LIGHT": "BLUE.LIGHT",
        "IR LIGHT": "IR.LIGHT",
        "UVA LIGHT": "UVA.LIGHT",
        "UVB LIGHT": "UVB.LIGHT",
        "MELANOPIC EDI": "MEDI",
    }
    output.update({rename.get(key, key): value for key, value in row.items()})
    return output


def write_rows(path, rows):
    path.parent.mkdir(parents=True, exist_ok=True)
    if not rows:
        raise ValueError(f"No rows prepared for {path}")
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def main():
    if len(sys.argv) != 4:
        raise SystemExit("Usage: prepare_mpi_raw_sensors.py SOURCE_ROOT BUILD_ROOT STUDY_DATES_CSV")
    source, build, study_dates = map(Path, sys.argv[1:])
    windows = read_windows(study_dates)
    manifest_path = build / "split_manifest.csv"
    with manifest_path.open(newline="", encoding="utf-8-sig") as handle:
        manifest = list(csv.DictReader(handle))

    acttrust_dir = source / "data/raw/group/acttrust"
    files_by_id = {}
    for path in acttrust_dir.glob("*.txt"):
        match = re.match(r"(\d+)_acttrust", path.name.replace("acttrust_ ", "acttrust_"))
        if match:
            files_by_id[f"MPI_S{int(match.group(1)):03d}"] = path

    for participant_id in FINAL_IDS:
        source_path = files_by_id.get(participant_id)
        if not source_path:
            raise FileNotFoundError(f"No ActTrust source for {participant_id}")
        start, end = windows[participant_id]
        rows = []
        for timestamp, row in parse_condor(source_path):
            if start <= timestamp <= end:
                row["DATE/TIME"] = timestamp.strftime("%Y-%m-%d %H:%M:%S")
                row["__source_file"] = source_path.name
                rows.append(normalized(row, participant_id))
        relative = Path("data/imported/light") / f"{participant_id}_acttrust_wrist.csv"
        write_rows(build / relative, rows)
        manifest.append({
            "source_file": str(source_path.relative_to(source)),
            "source_object": "raw_ActTrust2_log",
            "participant_id": participant_id,
            "output_file": str(relative),
            "rows": str(len(rows)),
            "columns": str(len(rows[0])),
        })

    ambient_rows = []
    ambient_dir = source / "data/raw/individual/ambient"
    for source_path in sorted(ambient_dir.glob("*.txt")):
        if source_path.name.endswith("_Report.txt"):
            continue
        for timestamp, row in parse_condor(source_path):
            row["DATE/TIME"] = timestamp.strftime("%Y-%m-%d %H:%M:%S")
            row["__source_file"] = source_path.name
            ambient_rows.append(normalized(row))
    ambient_rows.sort(key=lambda row: (row["Datetime"], row["file.name"]))
    write_rows(build / "data/imported/environmental/MPI_ambient_rooftop.csv", ambient_rows)

    with manifest_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(manifest[0]))
        writer.writeheader()
        writer.writerows(manifest)
    print(f"Prepared 26 ActTrust files and {len(ambient_rows)} rooftop ambient rows")


if __name__ == "__main__":
    main()
