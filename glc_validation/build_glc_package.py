#!/usr/bin/env python3
"""Build GLC Schema 3.0.2 metadata around MPI participant-split CSV files."""

import csv
import json
import os
import shutil
import sys
from collections import defaultdict
from datetime import date, timedelta
from pathlib import Path

SCHEMA_VERSION = "3.0.2"
STUDY_ID = "MELIDOS_MPI_2025"
PARTICIPANT_PREFIX = "MPI"
_FRAMEWORK_ROOT = Path("/Users/salmathalji/Documents/Projects/GLEE/GLC/glc-framework")
VALIDATOR = Path(
    os.getenv(
        "GLC_VALIDATOR_ROOT",
        _FRAMEWORK_ROOT / "glc-metadata-validator"
        if (_FRAMEWORK_ROOT / "glc-metadata-validator").exists()
        else _FRAMEWORK_ROOT / "glee-metadata-validator",
    )
)
SOURCE_REPOSITORY = Path(
    os.getenv("MELIDOS_SOURCE_ROOT", Path(__file__).resolve().parents[2])
).resolve()
STUDY_DATES_WORKBOOK = SOURCE_REPOSITORY / "data" / "Study_dates_MeLiDos_MPI.xlsx"

QUESTIONNAIRES = {
    "acceptability": "Acceptability questionnaire",
    "ase": "Assessment of Sleep Environment (ASE)",
    "chronotype": "Chronotype questionnaires",
    "currentconditions": "Current conditions questionnaire",
    "demographics": "Demographics questionnaire",
    "evaluation": "Study evaluation questionnaire",
    "health": "Health questionnaire",
    "leba": "Light Exposure Behaviour Assessment (LEBA)",
    "vlsq8": "Visual Light Sensitivity Questionnaire (VLSQ-8)",
}
DIARIES = {
    "exercisediary": "Exercise diary",
    "experiencelog": "Experience log",
    "lightexposurediary": "Light exposure diary",
    "sleepdiaries": "Sleep diary",
    "wellbeingdiary": "WHO-5 wellbeing diary",
}
DATETIME_COLUMNS = {
    "currentconditions": ("Datetime", "YYYY-MM-DD HH:mm:ss"),
    "exercisediary": ("Date", "YYYY-MM-DD"),
    "experiencelog": ("Datetime", "YYYY-MM-DD HH:mm:ss"),
    "lightexposurediary": ("Date", "YYYY-MM-DD"),
    "sleepdiaries": ("bedtime", "YYYY-MM-DD HH:mm:ss"),
    "wearlog": ("start", "YYYY-MM-DD HH:mm:ss"),
    "wellbeingdiary": ("Date", "YYYY-MM-DD"),
    "light_chest": ("Datetime", "YYYY-MM-DD HH:mm:ss"),
    "light_glasses": ("Datetime", "YYYY-MM-DD HH:mm:ss"),
    "light_wrist": ("Datetime", "YYYY-MM-DD HH:mm:ss"),
    "trial_times": ("start", "YYYY-MM-DD HH:mm:ss"),
}
PARTICIPANT_CHARACTERISTIC_FIELDS = {
    "vlsq8": ("VLSQ8",),
    "chronotype": ("meq_type", "meq", "msf_sc", "sjl", "so_w", "so_f", "sd_w", "sd_f", "msw", "msf", "sd_week", "outdoor"),
    "demographics": ("native_language", "employment_status"),
    "health": ("medication", "tobacco", "drugs", "disorder", "gen_health", "visual_acuity"),
    "evaluation": ("glasses_use",),
    "ase": ("ASE",),
}
FILE_GROUP_INSTRUCTIONS = {
    "acceptability": "Complete the light-glasses acceptability questionnaire at the end of the study.",
    "ase": "Complete the Assessment of Sleep Environment questionnaire at the end of the study.",
    "chronotype": "Complete the chronotype questionnaires at baseline.",
    "currentconditions": "Complete the scheduled momentary assessment at 11:00, 14:00, 17:00, and 20:00 during the monitoring period.",
    "demographics": "Complete the demographic questionnaire at baseline.",
    "evaluation": "Complete the light-glasses evaluation at the end of the study.",
    "exercisediary": "Complete the physical-activity diary in the evening.",
    "experiencelog": "Use the smartphone application throughout monitoring to report experiences with the light loggers.",
    "health": "Complete the health screening questionnaire at baseline.",
    "leba": "Complete the Light Exposure Behaviour Assessment at the end of the study.",
    "lightexposurediary": "In the evening, retrospectively document the primary light source and activity context for each hour; photograph and upload the paper diary daily.",
    "sleepdiaries": "Complete the sleep diary after awakening each morning.",
    "trial_times": "Study staff record the start and end of the participant's monitoring period.",
    "vlsq8": "Complete the Visual Light Sensitivity Questionnaire-8 at the end of the study.",
    "wearlog": "Use the mobile wear log throughout monitoring to document device removals and related non-wear information.",
    "wellbeingdiary": "Complete the wellbeing questionnaire in the evening.",
}
SENSOR_INSTRUCTIONS = (
    "Wear the assigned light-monitoring device continuously during waking hours. During sleep, place it facing upward on a bedside surface near head level. "
    "During waking non-wear, place it in the provided opaque black bag and document the removal in the wear log."
)
CHRONOTYPE_CHARACTERISTIC_METADATA = {
    "meq_type": ("", "Derived MEQ chronotype category."),
    "meq": ("score", "Calculated Morningness-Eveningness Questionnaire score."),
    "msf_sc": ("seconds after midnight", "Calculated sleep-corrected midpoint of sleep on free days."),
    "sjl": ("hours", "Calculated social jetlag."),
    "so_w": ("seconds after midnight", "Calculated sleep onset on working days."),
    "so_f": ("seconds after midnight", "Calculated sleep onset on free days."),
    "sd_w": ("hours", "Calculated sleep duration on working days."),
    "sd_f": ("hours", "Calculated sleep duration on free days."),
    "msw": ("seconds after midnight", "Calculated midpoint of sleep on working days."),
    "msf": ("seconds after midnight", "Calculated midpoint of sleep on free days."),
    "sd_week": ("hours", "Calculated average weekly sleep duration."),
    "outdoor": ("minutes", "Calculated average time spent outside."),
}


def read_csv(path):
    with path.open(newline="", encoding="utf-8-sig") as handle:
        return list(csv.DictReader(handle))


def write_json(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def workbook_device_map(workbook_extract):
    mapping = defaultdict(dict)
    for path in (SOURCE_REPOSITORY / "data/raw/group/actlumus").glob("*.txt"):
        participant, serial = path.name.split("_", 1)[0], path.name.split("Log_", 1)[1].split("_", 1)[0]
        mapping[f"MPI_S{int(participant):03d}"]["head"] = f"MPI_AL_{int(serial):04d}"
    for path in (SOURCE_REPOSITORY / "data/raw/group/acttrust").glob("*.txt"):
        participant, serial = path.name.split("_", 1)[0], path.name.split("Log_", 1)[1].split("_", 1)[0]
        mapping[f"MPI_S{int(participant):03d}"]["wrist"] = f"MPI_AT_{int(serial):04d}"
    return mapping


def workbook_devices(workbook_extract):
    mapping = workbook_device_map(workbook_extract)
    trial_starts = read_csv(workbook_extract / "study_dates.csv")
    final_ids = [f"MPI_S{number:03d}" for number in (201,202,204,205,206,208,209,210,212,213,214,215,216,218,219,221,222,223,224,225,226,227,228,229,230,231)]
    earliest = {}
    for participant, row in zip(final_ids, trial_starts):
        deployed = (date(1899, 12, 30) + timedelta(days=int(float(row["datetime_trial_start"])))).isoformat()
        for device_id in mapping[participant].values():
            earliest[device_id] = min(deployed, earliest.get(device_id, deployed))
    output = []
    for device_id in sorted({value for participant in mapping.values() for value in participant.values()} | {"MPI_AL_1431"}):
        acttrust = "_AT_" in device_id
        serial = device_id.rsplit("_", 1)[1]
        calibration_date = earliest.get(device_id, "2023-08-14")
        device = {
            "schema_version": SCHEMA_VERSION,
            "device_internal_id": device_id,
            "device_manufacturer": "Condor Instruments",
            "device_model": "ActTrust2" if acttrust else "ActLumus AL0101",
            "device_serial_number": serial,
            "device_calibration_date": calibration_date,
            "device_datasheet_id": "acttrust2" if acttrust else "actlumus-al0101",
            "device_sensors": [
                {"device_sensor_type": "spectral, photopic, and melanopic light sensor"},
                {"device_sensor_type": "triaxial accelerometer"},
                {"device_sensor_type": "temperature sensor"},
                {"device_sensor_type": "capacitive off-wrist sensor"},
            ],
        }
        output.append(device)
    return output


def participants_from_split(root):
    output = []
    included = sorted(
        path.stem.removesuffix("_acceptability")
        for path in (root / "data" / "imported").glob(f"{PARTICIPANT_PREFIX}_S*_acceptability.csv")
    )
    for participant_id in included:
        path = root / "data" / "imported" / f"{participant_id}_demographics.csv"
        row = read_csv(path)[0]
        output.append({
            "participant_internal_id": row["Id"],
            "participant_age": row["age"],
            "participant_sex": row["sex"],
            "participant_gender": row["gender"],
        })
    return output


def write_participants(path, participants):
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(participants[0]))
        writer.writeheader()
        writer.writerows(participants)


def write_participant_characteristics(root, path, participant_ids):
    fields = [
        "participant_internal_id",
        "participant_characteristic_name",
        "participant_characteristic_value",
        "participant_characteristic_unit",
        "participant_characteristic_description",
    ]
    rows = []
    for participant_id in participant_ids:
        for source, selected_fields in PARTICIPANT_CHARACTERISTIC_FIELDS.items():
            source_path = root / "data" / "imported" / f"{participant_id}_{source}.csv"
            if not source_path.is_file():
                continue
            source_rows = read_csv(source_path)
            source_row = source_rows[0]
            for name in selected_fields:
                value = source_row[name]
                unit = ""
                description = f"Source: {source}.RData; original column: {name}."
                if source == "chronotype":
                    unit, phenotype_description = CHRONOTYPE_CHARACTERISTIC_METADATA[name]
                    description = (
                        f"Derived phenotype measure calculated during source-data preprocessing. "
                        f"{phenotype_description} Source: {source}.RData; original column: {name}."
                    )
                rows.append({
                    "participant_internal_id": participant_id,
                    "participant_characteristic_name": name,
                    "participant_characteristic_value": value,
                    "participant_characteristic_unit": unit,
                    "participant_characteristic_description": description,
                })
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def preprocessing_descriptions(base_stem, participant_id):
    descriptions = []

    if base_stem.startswith("light_"):
        descriptions.extend([
            "Imported from the raw ActLumus logs and restricted to the participant-specific trial interval.",
            "Timestamps were regularized and implicit gaps were expanded into explicit rows by the source preprocessing pipeline.",
        ])
        descriptions.append("The study-date workbook used sequential enrolment IDs; packaging applies the explicit, serial-number-verified mapping to the final retained participant IDs.")
    elif base_stem == "acttrust_wrist":
        descriptions.extend([
            "Decoded from the raw ActTrust2 log because this stream was not included in the source repository's imported RData files.",
            "Restricted to the participant-specific trial interval using the explicit, serial-number-verified mapping from workbook rows to final retained participant IDs.",
            "No synthetic gap rows, resampling, or aggregation were introduced during GLC packaging.",
        ])
    elif base_stem == "chronotype":
        descriptions.extend([
            "Imported from REDCap/MyCap and recoded using the repository codebook.",
            "Chronotype scores and phenotype measures were derived by the source import script.",
            "For the source MCTQ overview calculation, alarm_f was forced to FALSE; the source script states that participants who used an alarm on free days must be excluded from formal analyses of the affected chronotype measures.",
        ])
    elif base_stem == "health":
        descriptions.append(
            "Imported from REDCap and recoded using the repository codebook."
        )
    elif base_stem in {"exercisediary", "lightexposurediary", "wellbeingdiary"}:
        descriptions.extend([
            "Imported from REDCap/MyCap and recoded using the repository codebook.",
            "Diary records completed between 00:00 and 13:59 were assigned to the preceding diary date.",
        ])
    elif base_stem == "currentconditions":
        descriptions.append(
            "Imported from REDCap/MyCap, restricted to completed records with a start timestamp, and recoded using the repository codebook."
        )
    elif base_stem == "sleepdiaries":
        descriptions.extend([
            "Imported from REDCap/MyCap and recoded using the repository codebook.",
            "The source correction log documents 41 corrections across 13 participant sleep-diary files, including wrong dates, AM/PM errors, switched bedtime/sleep fields, and mistyped times.",
            "Sleep onset and duration fields were derived; awake duration was set to zero when no awakenings were reported.",
        ])
    elif base_stem == "experiencelog":
        descriptions.extend([
            "Imported from REDCap/MyCap, with checkbox responses combined and past/current timestamps reshaped into event rows.",
            "Rows without an event timestamp were omitted; English free-text translations were loaded from the repository's AI_translations table.",
        ])
    elif base_stem == "wearlog":
        descriptions.extend([
            "Imported from REDCap/MyCap and reshaped from past/current responses into wear-event rows.",
            "Event sequences underwent the repository's plausibility checks; durations were derived and only plausible non-zero intervals were retained. English free-text translations were loaded from the repository's AI_translations table.",
        ])
    elif base_stem == "trial_times":
        descriptions.append(
            "Imported from the site study-date workbook and assigned Europe/Berlin time. Sequential enrolment IDs were converted to final retained participant IDs with an explicit mapping verified against ActLumus serial numbers."
        )
    else:
        descriptions.append(
            "Imported from REDCap/MyCap, with empty repeat-instance rows removed where applicable and variables recoded using the repository codebook."
        )

    descriptions.append(
        "Converted from the repository's processed RData table to UTF-8 CSV and split by participant; this final packaging step did not intentionally alter rows or variables."
    )
    return descriptions


def file_group(root, record, trial_start, screening_datetime, device_map):
    path = root / record["output_file"]
    stem = path.stem.removeprefix(record["participant_id"] + "_")
    base_stem = stem.removesuffix("_AL03").removesuffix("_AL04")
    with path.open(newline="", encoding="utf-8-sig") as handle:
        headers = next(csv.reader(handle))

    if base_stem.startswith("light_") or base_stem == "acttrust_wrist":
        modality = ["light", "accelerometry", "temperature"]
    elif base_stem in QUESTIONNAIRES:
        modality = ["questionnaire"]
    elif base_stem in DIARIES:
        modality = ["diary"]
    elif base_stem == "wearlog":
        modality = ["wear_log"]
    else:
        modality = ["other"]

    group = {
        "dataset_file_modality": modality,
        "dataset_file_temporal_resolution": {"resolution_type": "fixed_interval", "value": 60 if base_stem == "acttrust_wrist" else 10, "unit": "second"} if (base_stem.startswith("light_") or base_stem == "acttrust_wrist") else {"resolution_type": "event_based"},
        "dataset_file_instructions": SENSOR_INSTRUCTIONS if (base_stem.startswith("light_") or base_stem == "acttrust_wrist") else FILE_GROUP_INSTRUCTIONS[base_stem],
        "dataset_file_names": [record["output_file"]],
        "dataset_file_format": "csv",
        "dataset_file_encoding": ["UTF-8"],
        "dataset_file_timezone": "Europe/Berlin",
        "dataset_file_role": "primary" if base_stem == "light_glasses" else "supporting",
        "dataset_file_data_state": "processed",
        "dataset_file_header_row": 1,
        "dataset_file_preprocessing": {
            "dataset_file_preprocessing_bol": True,
            "dataset_file_preprocessing_desc": preprocessing_descriptions(base_stem, record["participant_id"]),
        },
        "dataset_file_variables": [{
            "dataset_file_variables_name": name,
            "dataset_file_variables_labels": name,
            "dataset_file_variables_type": "string",
            "dataset_file_variables_term": {"variable_term": "other", "variable_name": name},
        } for name in headers],
    }
    if group["dataset_file_role"] == "primary":
        group["primary_variables"] = ["MEDI"]

    if modality == ["other"]:
        group["dataset_file_modality_other"] = "study timing records"
        group["dataset_file_modality_other_type"] = "non_device"
    if base_stem in QUESTIONNAIRES or base_stem in DIARIES or base_stem == "wearlog":
        instrument_type = "questionnaire" if base_stem in QUESTIONNAIRES else "diary" if base_stem in DIARIES else "wear_log"
        collection_method = "paper" if base_stem == "lightexposurediary" else "software"
        group["dataset_file_instrument"] = {
            "instrument_type": instrument_type,
            "instrument_name": QUESTIONNAIRES.get(base_stem, DIARIES.get(base_stem, "Study wear log")),
            "collection_method": collection_method,
            "recorded_by": "participant" if stem != "trial_times" else "study_staff",
        }
        if collection_method == "software":
            group["dataset_file_instrument"]["software_name"] = "MyCap integrated with REDCap"
    if base_stem == "wearlog":
        group["dataset_file_description"] = (
            "Participant-reported wear events concerning the study-worn devices collectively. "
            "No single device association is supplied because the file group is not attributable "
            "to one device throughout."
        )

    if base_stem in DATETIME_COLUMNS:
        column, date_format = DATETIME_COLUMNS[base_stem]
        group["dataset_file_datetime"] = {
            "dataset_file_datetime_source": "column",
            "dataset_file_datetime_date": column,
            "dataset_file_datetime_dateformat": date_format,
        }
    elif base_stem in {"chronotype", "demographics", "health"}:
        group["dataset_file_datetime"] = {
            "dataset_file_datetime_source": "collection",
            "dataset_file_datetime_date": screening_datetime or trial_start,
            "dataset_file_datetime_dateformat": "YYYY-MM-DD HH:mm:ss",
        }
        group["dataset_file_description"] = (
            "This questionnaire was part of participant screening and contains "
            "no embedded completion timestamp. Its collection datetime is "
            + (
                "represented by the participant's in-person screening timestamp "
                "recorded in Study_dates_MeLiDos_MPI.xlsx."
                if screening_datetime
                else "approximated using the participant's trial-start timestamp "
                "because no screening timestamp was available."
            )
        )
    else:
        group["dataset_file_datetime"] = {
            "dataset_file_datetime_source": "collection",
            "dataset_file_datetime_date": trial_start,
            "dataset_file_datetime_dateformat": "YYYY-MM-DD HH:mm:ss",
        }

    location = None
    if base_stem == "light_glasses": location = "head"
    if base_stem == "light_chest": location = "chest"
    if base_stem == "light_wrist": location = "wrist"
    if base_stem == "acttrust_wrist": location = "wrist"
    if location:
        group["dataset_file_crossref_device_id"] = device_map[location]
        group["dataset_file_device_location"] = {"head": "eye level", "chest": "chest", "wrist": "wrist"}[location]
        group["dataset_file_device_location_type"] = "body_worn"
    return group


def main():
    root = Path(sys.argv[1]).resolve()
    workbook_extract = root / "workbook_metadata"
    manifest = read_csv(root / "split_manifest.csv")
    records = defaultdict(list)
    for record in manifest:
        records[record["participant_id"]].append(record)

    participants = participants_from_split(root)
    participant_ids = [row["participant_internal_id"] for row in participants]
    device_map = workbook_device_map(workbook_extract)
    trials = {pid: read_csv(root / "data" / "imported" / f"{pid}_trial_times.csv")[0]["start"] for pid in participant_ids}
    screening = {}
    datasets = []
    for participant_id in participant_ids:
        groups = [
            file_group(
                root,
                record,
                trials[participant_id],
                screening.get(participant_id),
                device_map[participant_id],
            )
            for record in sorted(
                records[participant_id],
                key=lambda x: x["output_file"],
            )
        ]
        datasets.append({
            "schema_version": SCHEMA_VERSION,
            "dataset_internal_id": f"MELIDOS_{participant_id}",
            "dataset_participant_associated": True,
            "dataset_crossref": {"dataset_crossref_study_id": STUDY_ID, "dataset_crossref_participant_id": participant_id},
            "dataset_timezone": "Europe/Berlin",
            "dataset_location": [48.5216, 9.0576],
            "dataset_variable_terms": [{"term": "other", "label": "Other"}],
            "dataset_file": groups,
        })

    data = root / "data"
    write_participants(data / "participants.csv", participants)
    write_participant_characteristics(root, data / "participant_characteristics.csv", participant_ids)
    write_json(data / "datasets.json", datasets)
    devices = workbook_devices(workbook_extract)
    write_json(data / "devices.json", devices)
    write_json(data / "device_datasheets.json", [{
        "schema_version": SCHEMA_VERSION,
        "datasheet_id": "actlumus-al0101",
        "datasheet_manufacturer": "Condor Instruments",
        "datasheet_type": "wearable actigraph",
        "datasheet_sensor_modality": ["light", "accelerometer", "temperature", "other"],
        "datasheet_sensor_modality_other": "Capacitive off-wrist detection",
        "datasheet_model": "ActLumus AL0101",
        "datasheet_calibration_range": "1–100000 lx",
        "datasheet_calibration_notes": (
            "Measurement range is taken from the Condor Instruments ActLumus "
            "AL0101 user manual. Device-specific calibration details were not "
            "supplied with the MPI source data. The device delivery month from "
            "Metadata_Melidos_MPI.xlsx or, where absent, the earliest documented "
            "deployment date from Study_dates_MeLiDos_MPI.xlsx is used provisionally "
            "as a calibration-date proxy and requires confirmation against the calibration records."
        ),
        "datasheet_channel": [
            {"datasheet_channel_nr": index, "datasheet_channel_name": name}
            for index, name in enumerate(
                [
                    "EVENT",
                    "TEMPERATURE",
                    "ORIENTATION",
                    "PIM",
                    "PIMn",
                    "TAT",
                    "TATn",
                    "ZCM",
                    "ZCMn",
                    "LIGHT",
                    "IR.LIGHT",
                    "CAP_SENS_1",
                    "CAP_SENS_2",
                    "F1",
                    "F2",
                    "F3",
                    "F4",
                    "F5",
                    "F6",
                    "F7",
                    "F8",
                    "MEDI",
                    "CLEAR",
                    "STATE",
                ],
                start=1,
            )
        ],
    }])
    dataset_ids = [row["dataset_internal_id"] for row in datasets]
    write_json(data / "study.json", [{
        "schema_version": SCHEMA_VERSION,
        "study_internal_id": STUDY_ID,
        "study_title": "Personal light exposure dataset for Delft, The Netherlands",
        "study_ethics": "The Hague University of Applied Sciences Ethics Committee (approval 20240529)",
        "study_short_description": "MeLiDos field-study data collected by The Hague University of Applied Sciences in Delft, The Netherlands.",
        "study_sample": "Twenty participants were enrolled; fifteen participants were included in the repository.",
        "study_setting": "Field study",
        "study_geographical_location": "Delft, The Netherlands, city/urban",
        "study_contributors": [
            {
                "contributor_full_name": "Sam Aerts",
                "contributor_roles": ["Conceptualization", "Data curation", "Formal analysis", "Investigation", "Methodology", "Project administration", "Software", "Validation", "Visualization", "Writing – original draft", "Writing – review & editing"],
                "contributor_email": "s.h.aerts@hhs.nl",
                "contributor_institution": {"contributor_institution_name": "The Hague University of Applied Sciences", "contributor_institution_city": "Delft", "contributor_institution_country": "The Netherlands"},
            },
            {
                "contributor_full_name": "Astrid Jansen",
                "contributor_roles": ["Data curation", "Investigation", "Writing – original draft"],
                "contributor_email": "a.p.jansen@hhs.nl",
                "contributor_institution": {"contributor_institution_name": "The Hague University of Applied Sciences", "contributor_institution_city": "Delft", "contributor_institution_country": "The Netherlands"},
            },
            {
                "contributor_full_name": "Nico Hogervorst",
                "contributor_roles": ["Data curation", "Investigation", "Validation"],
                "contributor_institution": {"contributor_institution_name": "The Hague University of Applied Sciences", "contributor_institution_city": "Delft", "contributor_institution_country": "The Netherlands"},
            },
            {
                "contributor_full_name": "Daan Boesten",
                "contributor_roles": ["Data curation", "Investigation", "Validation", "Writing – original draft"],
                "contributor_institution": {"contributor_institution_name": "The Hague University of Applied Sciences", "contributor_institution_city": "Delft", "contributor_institution_country": "The Netherlands"},
            },
            {
                "contributor_full_name": "John Bolte",
                "contributor_roles": ["Conceptualization", "Funding acquisition", "Project administration", "Resources", "Supervision", "Writing – review & editing"],
                "contributor_institution": {"contributor_institution_name": "The Hague University of Applied Sciences", "contributor_institution_city": "Delft", "contributor_institution_country": "The Netherlands"},
            },
        ],
        "study_datasets": dataset_ids,
        "study_type": "field study",
        "study_keywords": ["light exposure", "circadian", "wearable sensor", "MeLiDos", "Delft", "The Netherlands"],
    }])

    schema_out = root / "schemas" / SCHEMA_VERSION
    schema_out.mkdir(parents=True, exist_ok=True)
    for source in (VALIDATOR / "schemas" / SCHEMA_VERSION).glob("*.json"):
        shutil.copy2(source, schema_out / source.name)
    shutil.copy2(VALIDATOR / "schemas" / "1.0.0" / "json-entity-resource.json", root / "json-entity-resource.json")
    resources = [
        {"name": "study", "path": "data/study.json", "profile": "json-entity-resource.json", "mediatype": "application/json", "jsonSchema": f"schemas/{SCHEMA_VERSION}/study.schema.json"},
        {"name": "participants", "path": "data/participants.csv", "profile": "tabular-data-resource", "format": "csv", "mediatype": "text/csv", "schema": f"schemas/{SCHEMA_VERSION}/participants.schema.json"},
        {"name": "participant_characteristics", "path": "data/participant_characteristics.csv", "profile": "tabular-data-resource", "format": "csv", "mediatype": "text/csv", "schema": f"schemas/{SCHEMA_VERSION}/participant_characteristics.schema.json"},
        {"name": "datasets", "path": "data/datasets.json", "profile": "json-entity-resource.json", "mediatype": "application/json", "jsonSchema": f"schemas/{SCHEMA_VERSION}/dataset.schema.json"},
        {"name": "devices", "path": "data/devices.json", "profile": "json-entity-resource.json", "mediatype": "application/json", "jsonSchema": f"schemas/{SCHEMA_VERSION}/device.schema.json"},
        {"name": "device_datasheets", "path": "data/device_datasheets.json", "profile": "json-entity-resource.json", "mediatype": "application/json", "jsonSchema": f"schemas/{SCHEMA_VERSION}/device_datasheet.schema.json"},
    ]
    write_json(root / "datapackage.json", {"profile": f"schemas/{SCHEMA_VERSION}/glc-dp-profile.json", "schema_version": SCHEMA_VERSION, "name": "melidos-mpi-glc-package", "title": "MeLiDos MPI GLC Data Package", "resources": resources})


if __name__ == "__main__":
    main()
