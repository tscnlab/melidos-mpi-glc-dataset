#!/usr/bin/env python3
"""Add the GLC missing optional-value convention to JSON Schemas."""

import json
import sys
from pathlib import Path

GUIDANCE = (
    "Missing-value convention: Optional properties with no value should be omitted rather than "
    "represented as null, an empty string, or an empty array. Required properties must remain "
    "present and satisfy their schema, including where null is explicitly permitted."
)

for argument in sys.argv[1:]:
    path = Path(argument)
    schema = json.loads(path.read_text(encoding="utf-8"))
    schema["$comment"] = GUIDANCE
    path.write_text(json.dumps(schema, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
