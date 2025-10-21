
# This code takes the Kongsberg .xml calibration format and converts it to csv, to paste into excel
# The excel file name is ComparisonsCalibrationSailorEK80.csv

import xml.etree.ElementTree as ET
import csv
import sys



#!/usr/bin/env python3
"""
xml_to_calib_csv.py

Usage:
    python xml_to_calib_csv.py input.xml output.csv

This script streams the XML and extracts data under each <CalibrationResults>
element to a CSV with the exact column order requested.
"""

import sys
import csv
import xml.etree.ElementTree as ET
from collections import defaultdict

# Desired columns in this order - each occurrence gets its own column
COLUMNS = [
    "Frequency", "Gain", "SaCorrection",
    "BeamWidthAlongship_1", "BeamWidthAthwartship_1",
    "AngleOffsetAlongship_1", "AngleOffsetAthwartship_1",
    "TsRmsError_1", "Impedance_1", "Phase_1",
    # second group with separate column names
    "BeamWidthAlongship_2", "BeamWidthAthwartship_2",
    "AngleOffsetAlongship_2", "AngleOffsetAthwartship_2",
    "TsRmsError_2", "Impedance_2", "Phase_2"
]

# Base field names for mapping
BASE_FIELDS = [
    "Frequency", "Gain", "SaCorrection",
    "BeamWidthAlongship", "BeamWidthAthwartship",
    "AngleOffsetAlongship", "AngleOffsetAthwartship",
    "TsRmsError", "Impedance", "Phase"
]

# common attribute keys that might hold numeric/text values
ATTR_KEYS = ("value","Value","val","Val","v")

def local_name(tag):
    """Strip namespace from an Element tag."""
    if tag is None:
        return ""
    if "}" in tag:
        return tag.split("}", 1)[1]
    return tag

def extract_values_from_calib_elem(calib_elem):
    """
    Walk all descendants of calib_elem and build a dict:
        name -> [list of values in document order]
    For each element we try:
      - element.text (if non-empty)
      - any attribute in ATTR_KEYS (first match)
    """
    occ = defaultdict(list)
    for desc in calib_elem.iter():
        if desc is calib_elem:
            continue
        name = local_name(desc.tag)
        # try element text
        val = None
        if desc.text:
            t = desc.text.strip()
            if t != "":
                val = t
        # otherwise try common attributes
        if val is None and desc.attrib:
            for k in ATTR_KEYS:
                if k in desc.attrib and desc.attrib[k].strip() != "":
                    val = desc.attrib[k].strip()
                    break
        # if we found a value, append to occurrences
        if val is not None:
            occ[name].append(val)
    return occ

def make_row_from_occ(occ):
    """
    Split semicolon-separated values and create multiple rows.
    Each position in the semicolon-separated lists becomes a separate row.
    Handle multiple occurrences of fields (e.g., two sets of beam measurements).
    """
    # Get all the field values and split by semicolon
    all_rows = []
    
    # Find the field with the most values to determine number of rows
    max_length = 0
    split_values = {}
    
    for field in BASE_FIELDS:
        values = occ.get(field, [])
        if values:
            # Split all occurrences by semicolon
            all_splits = []
            for val in values:
                all_splits.append(val.split(';') if ';' in val else [val])
            split_values[field] = all_splits
            # Max length from first occurrence
            if all_splits:
                max_length = max(max_length, len(all_splits[0]))
        else:
            split_values[field] = []
    
    # Create rows - one for each position in the semicolon-separated lists
    for i in range(max_length):
        row = []
        
        # Single occurrence fields first
        for field in ["Frequency", "Gain", "SaCorrection"]:
            all_splits = split_values.get(field, [])
            if all_splits and len(all_splits) > 0 and i < len(all_splits[0]):
                row.append(all_splits[0][i])
            else:
                row.append("")
        
        # Multi-occurrence fields - handle both _1 and _2 columns
        multi_fields = [
            "BeamWidthAlongship", "BeamWidthAthwartship",
            "AngleOffsetAlongship", "AngleOffsetAthwartship", 
            "TsRmsError", "Impedance", "Phase"
        ]
        
        for field in multi_fields:
            all_splits = split_values.get(field, [])
            # First occurrence (_1 column)
            if all_splits and len(all_splits) > 0 and i < len(all_splits[0]):
                row.append(all_splits[0][i])
            else:
                row.append("")
            # Second occurrence (_2 column)
            if all_splits and len(all_splits) > 1 and i < len(all_splits[1]):
                row.append(all_splits[1][i])
            else:
                row.append("")
    
        all_rows.append(row)
    
    return all_rows

def stream_and_extract(input_xml_path, output_csv_path):
    # We'll use iterparse to find CalibrationResults elements and free memory
    context = ET.iterparse(input_xml_path, events=("start","end"))
    _, root = next(context)  # get root element
    rows_written = 0

    with open(output_csv_path, "w", newline="", encoding="utf-8") as fout:
        writer = csv.writer(fout)
        writer.writerow(COLUMNS)

        # Walk through file, look for end event of CalibrationResults elements
        for event, elem in context:
            if event == "end" and local_name(elem.tag) == "CalibrationResults":
                occ = extract_values_from_calib_elem(elem)
                rows = make_row_from_occ(occ)  # Now returns multiple rows
                for row in rows:
                    writer.writerow(row)
                    rows_written += 1
                # clear the element from memory (very important for large XML)
                elem.clear()
                # clear the root occasionally to avoid memory leak
                if rows_written % 100 == 0:
                    root.clear()

    print(f"Wrote {rows_written} rows to {output_csv_path}")

if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("Usage: python xml_to_calib_csv.py input.xml output.csv")
        sys.exit(1)
    input_xml = sys.argv[1]
    output_csv = sys.argv[2]
    stream_and_extract(input_xml, output_csv)

# Run example
# python3 code/calibration/xml_to_csv.py temp/CalibrationDataFile-D20250706HudsonBay.xml temp/cal_hudson2025.csv