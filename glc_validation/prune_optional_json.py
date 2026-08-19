#!/usr/bin/env python3
"""Omit empty optional JSON properties while preserving schema-required fields."""

import argparse
import json
from pathlib import Path


def is_empty(value):
    return value is None or value == "" or value == []


def prune(value, schema, path="$", removed=None):
    removed = removed if removed is not None else []
    if isinstance(value, list):
        item_schema = schema.get("items", {}) if isinstance(schema, dict) else {}
        return [prune(item, item_schema, f"{path}[{index}]", removed) for index, item in enumerate(value)]
    if not isinstance(value, dict):
        return value

    properties = schema.get("properties", {}) if isinstance(schema, dict) else {}
    required = set(schema.get("required", [])) if isinstance(schema, dict) else set()
    missing = required.difference(value)
    if missing:
        raise ValueError(f"{path} is missing required properties: {sorted(missing)}")

    output = {}
    for key, item in value.items():
        child = prune(item, properties.get(key, {}), f"{path}.{key}", removed)
        if key not in required and is_empty(child):
            removed.append(f"{path}.{key}")
        else:
            output[key] = child
    return output


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("input", type=Path)
    parser.add_argument("schema", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()

    data = json.loads(args.input.read_text(encoding="utf-8"))
    schema = json.loads(args.schema.read_text(encoding="utf-8"))
    removed = []
    if isinstance(data, list):
        cleaned = [prune(item, schema, f"$[{index}]", removed) for index, item in enumerate(data)]
    else:
        cleaned = prune(data, schema, removed=removed)
    args.output.write_text(json.dumps(cleaned, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Removed {len(removed)} empty optional properties from {args.input}")


if __name__ == "__main__":
    main()
