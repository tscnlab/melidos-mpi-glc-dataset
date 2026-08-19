#!/usr/bin/env python3
"""Extract workbook sheets to CSV without modifying the source XLSX."""

import csv
import re
import sys
from pathlib import Path
from zipfile import ZipFile
import xml.etree.ElementTree as ET

NS = {
    "a": "http://schemas.openxmlformats.org/spreadsheetml/2006/main",
    "r": "http://schemas.openxmlformats.org/officeDocument/2006/relationships",
}


def column_number(cell_ref):
    match = re.match(r"([A-Z]+)", cell_ref or "A")
    number = 0
    for char in match.group(1) if match else "A":
        number = number * 26 + ord(char) - 64
    return number


def shared_strings(zip_file):
    if "xl/sharedStrings.xml" not in zip_file.namelist():
        return []
    root = ET.fromstring(zip_file.read("xl/sharedStrings.xml"))
    return ["".join(text.text or "" for text in item.findall(".//a:t", NS)) for item in root.findall("a:si", NS)]


def value(cell, strings):
    node = cell.find("a:v", NS)
    if node is None:
        return ""
    text = node.text or ""
    return strings[int(text)] if cell.attrib.get("t") == "s" else text


def rows(zip_file, target, strings):
    root = ET.fromstring(zip_file.read(f"xl/{target}"))
    output = []
    for row in root.findall(".//a:sheetData/a:row", NS):
        values = []
        last_column = 0
        for cell in row.findall("a:c", NS):
            column = column_number(cell.attrib.get("r"))
            values.extend([""] * (column - last_column - 1))
            values.append(value(cell, strings))
            last_column = column
        while values and values[-1] == "":
            values.pop()
        output.append(values)
    return output


def main():
    source, destination = Path(sys.argv[1]), Path(sys.argv[2])
    destination.mkdir(parents=True, exist_ok=True)
    with ZipFile(source) as archive:
        strings = shared_strings(archive)
        workbook = ET.fromstring(archive.read("xl/workbook.xml"))
        relationships = ET.fromstring(archive.read("xl/_rels/workbook.xml.rels"))
        relmap = {rel.attrib["Id"]: rel.attrib["Target"] for rel in relationships}
        for sheet in workbook.find("a:sheets", NS):
            name = sheet.attrib["name"]
            relation = sheet.attrib[f"{{{NS['r']}}}id"]
            sheet_rows = rows(archive, relmap[relation], strings)
            slug = re.sub(r"[^A-Za-z0-9._-]+", "_", name).strip("_").lower()
            output = destination / f"{slug}.csv"
            with output.open("w", newline="", encoding="utf-8") as handle:
                csv.writer(handle).writerows(sheet_rows)
            print(f"{name}: {len(sheet_rows)} rows -> {output}")


if __name__ == "__main__":
    main()
