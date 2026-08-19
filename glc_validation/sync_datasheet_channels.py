#!/usr/bin/env python3
"""Synchronize the ActLumus datasheet channels with audited source columns."""

import argparse
import json
from pathlib import Path


CHANNELS = [
    "EVENT", "TEMPERATURE", "ORIENTATION",
    "PIM", "PIMn", "TAT", "TATn", "ZCM", "ZCMn", "LIGHT",
    "IR.LIGHT", "CAP_SENS_1", "CAP_SENS_2", "F1", "F2",
    "F3", "F4", "F5", "F6", "F7", "F8", "MEDI", "CLEAR", "STATE",
]


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("datasheets_json", type=Path)
    args = parser.parse_args()
    records = json.loads(args.datasheets_json.read_text(encoding="utf-8"))
    if len(records) != 1 or records[0].get("datasheet_id") != "actlumus-al0101":
        raise ValueError("Expected the single audited ActLumus AL0101 datasheet")
    records[0]["datasheet_channel"] = [
        {"datasheet_channel_nr": number, "datasheet_channel_name": name}
        for number, name in enumerate(CHANNELS, start=1)
    ]
    args.datasheets_json.write_text(
        json.dumps(records, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(f"Documented {len(CHANNELS)} audited ActLumus source channels.")


if __name__ == "__main__":
    main()
