#!/usr/bin/env python3
"""Apply MPI-specific study, device, and environmental metadata."""

import csv
import json
import sys
from pathlib import Path


def read_json(path):
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def variables(path):
    with path.open(newline="", encoding="utf-8-sig") as handle:
        headers = next(csv.reader(handle))
    numeric = set(headers) - {"Id", "file.name", "Datetime"}
    integers = {"MS", "EVENT", "ORIENTATION", "PIM", "TAT", "ZCM", "STATE", "CAP_SENS_1", "CAP_SENS_2"}
    units = {
        "MS": "ms", "TEMPERATURE": "Cel", "EXT.TEMPERATURE": "Cel",
        "LIGHT": "lx", "AMB.LIGHT": "uW/cm2", "RED.LIGHT": "uW/cm2",
        "GREEN.LIGHT": "uW/cm2", "BLUE.LIGHT": "uW/cm2",
        "IR.LIGHT": "uW/cm2", "UVA.LIGHT": "uW/cm2", "UVB.LIGHT": "uW/cm2",
        "MEDI": "lx",
    }
    terms = {
        "Datetime": "datetime", "TEMPERATURE": "temperature",
        "EXT.TEMPERATURE": "temperature", "LIGHT": "photopic_illuminance",
        "MEDI": "melanopic_edi", "PIM": "accelerometer_activity_metric",
        "PIMn": "accelerometer_activity_metric", "TAT": "accelerometer_activity_metric",
        "TATn": "accelerometer_activity_metric", "ZCM": "accelerometer_activity_metric",
        "ZCMn": "accelerometer_activity_metric",
    }
    output = []
    for name in headers:
        variable = {
            "dataset_file_variables_name": name,
            "dataset_file_variables_labels": name.replace(".", " ").replace("_", " ").title(),
            "dataset_file_variables_type": "integer" if name in integers else "numeric" if name in numeric else "string",
            "dataset_file_variables_term": {"variable_term": terms.get(name, "other")},
        }
        if terms.get(name, "other") == "other":
            variable["dataset_file_variables_term"]["variable_name"] = name
        if name in units:
            variable["dataset_file_variables_units"] = units[name]
        elif name in numeric:
            variable["dataset_file_variables_units"] = "1"
        output.append(variable)
    return output


def datasheet(identifier, model, channels):
    return {
        "schema_version": "3.0.2",
        "datasheet_id": identifier,
        "datasheet_manufacturer": "Condor Instruments",
        "datasheet_type": "wearable actigraph",
        "datasheet_sensor_modality": ["light", "accelerometer", "temperature", "other"],
        "datasheet_sensor_modality_other": "Capacitive off-wrist detection",
        "datasheet_model": model,
        "datasheet_calibration_range": "Not documented in the source metadata.",
        "datasheet_calibration_notes": (
            "The source metadata states that the devices were not calibrated and provides no calibration records. "
            "Because GLC 3.0.2 requires a calibration date, the earliest documented deployment date is used as a transparent provisional proxy; it must not be interpreted as evidence of calibration."
        ),
        "datasheet_channel": [
            {"datasheet_channel_nr": number, "datasheet_channel_name": name}
            for number, name in enumerate(channels, 1)
        ],
    }


def main():
    root = Path(sys.argv[1])
    data = root / "data"
    datasets = read_json(data / "datasets.json")
    datasets = [dataset for dataset in datasets if dataset.get("dataset_internal_id") != "MELIDOS_MPI_AMBIENT"]
    for dataset in datasets:
        for group in dataset.get("dataset_file", []):
            names = group.get("dataset_file_names", [])
            if names and Path(names[0]).stem.endswith("_acttrust_wrist"):
                group["dataset_file_variables"] = variables(root / names[0])
    ambient_path = root / "data/imported/environmental/MPI_ambient_rooftop.csv"
    ambient_group = {
        "dataset_file_modality": ["light", "accelerometry", "temperature"],
        "dataset_file_temporal_resolution": {"resolution_type": "fixed_interval", "value": 30, "unit": "second"},
        "dataset_file_instructions": "Operate the ActLumus logger at the building rooftop to record ambient environmental conditions.",
        "dataset_file_names": ["data/imported/environmental/MPI_ambient_rooftop.csv"],
        "dataset_file_format": "csv",
        "dataset_file_encoding": ["UTF-8"],
        "dataset_file_timezone": "Europe/Berlin",
        "dataset_file_role": "supporting",
        "dataset_file_data_state": "processed",
        "dataset_file_header_row": 1,
        "dataset_file_preprocessing": {
            "dataset_file_preprocessing_bol": True,
            "dataset_file_preprocessing_desc": [
                "Decoded from the weekly raw rooftop ActLumus logs because this environmental stream was absent from the imported RData files.",
                "Weekly files were concatenated and ordered by timestamp; no participant association, trial trimming, resampling, or synthetic gap rows were introduced.",
            ],
        },
        "dataset_file_variables": variables(ambient_path),
        "dataset_file_datetime": {
            "dataset_file_datetime_source": "column",
            "dataset_file_datetime_date": "Datetime",
            "dataset_file_datetime_dateformat": "YYYY-MM-DD HH:mm:ss",
        },
        "dataset_file_crossref_device_id": "MPI_AL_1431",
        "dataset_file_device_location": "building rooftop",
        "dataset_file_device_location_type": "environmental",
    }
    ambient = {
        "schema_version": "3.0.2",
        "dataset_internal_id": "MELIDOS_MPI_AMBIENT",
        "dataset_participant_associated": False,
        "dataset_crossref": {"dataset_crossref_study_id": "MELIDOS_MPI_2025"},
        "dataset_timezone": "Europe/Berlin",
        "dataset_location": [48.5216, 9.0576],
        "dataset_variable_terms": [{"term": "other", "label": "Other"}],
        "dataset_file": [ambient_group],
    }
    datasets.append(ambient)
    write_json(data / "datasets.json", datasets)

    study = read_json(data / "study.json")[0]
    study.update({
        "study_title": "Personal light exposure dataset for Tuebingen, Germany",
        "study_ethics": "Ethics Committee of the Technical University of Munich (2023-115-S-KK)",
        "study_short_description": "Near-corneal-plane light exposure and contextual, environmental, behavioural, sleep, and questionnaire data collected in healthy adults in everyday life.",
        "study_sample": "Thirty participants were enrolled; twenty-six healthy adults aged 18–55 years were retained in the published repository.",
        "study_setting": "Real-world field study",
        "study_geographical_location": "Tuebingen, Germany, urban setting",
        "study_preregistration": "https://doi.org/10.5281/zenodo.16895188",
        "study_contributors": [
            {"contributor_full_name": "Carolina Guidolin", "contributor_roles": ["Conceptualization", "Data collection"], "contributor_email": "carolina.guidolin@tuebingen.mpg.de", "contributor_orcid": "https://orcid.org/0009-0007-4959-2667", "contributor_institution": {"contributor_institution_name": "Max Planck Institute for Biological Cybernetics", "contributor_institution_city": "Tuebingen", "contributor_institution_country": "Germany"}},
            {"contributor_full_name": "Johannes Zauner", "contributor_roles": ["Data curation", "Software", "Validation"], "contributor_email": "johannes.zauner@tum.de", "contributor_orcid": "https://orcid.org/0000-0003-2171-4566", "contributor_institution": {"contributor_institution_name": "Technical University of Munich", "contributor_institution_city": "Munich", "contributor_institution_country": "Germany"}},
            {"contributor_full_name": "Manuel Spitschan", "contributor_roles": ["Conceptualization", "Supervision"], "contributor_email": "manuel.spitschan@tum.de", "contributor_orcid": "https://orcid.org/0000-0002-8572-9268", "contributor_institution": {"contributor_institution_name": "Technical University of Munich", "contributor_institution_city": "Munich", "contributor_institution_country": "Germany"}},
        ],
        "study_datasets": [dataset["dataset_internal_id"] for dataset in datasets],
        "study_type": "field study",
        "study_keywords": ["light exposure", "circadian", "wearable sensor", "MeLiDos", "Tuebingen", "Germany"],
    })
    write_json(data / "study.json", [study])

    with (root / "data/imported/light/MPI_S201_acttrust_wrist.csv").open(newline="", encoding="utf-8-sig") as handle:
        raw_channels = [name for name in next(csv.reader(handle)) if name not in {"Id", "file.name", "Datetime"}]
    with (root / "data/imported/light/MPI_S201_light_glasses.csv").open(newline="", encoding="utf-8-sig") as handle:
        light_channels = [name for name in next(csv.reader(handle)) if name not in {"Id", "file.name", "Datetime"}]
    write_json(data / "device_datasheets.json", [
        datasheet("actlumus-al0101", "ActLumus AL0101", light_channels),
        datasheet("acttrust2", "ActTrust2", raw_channels),
    ])


if __name__ == "__main__":
    main()
