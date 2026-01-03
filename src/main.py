#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Filename: main.py
Description: Parses segments in travel report json input and calculates times and perdiems.

Author: Tatanka5XL
Created: 2025-12-23
Last Modified: 2026-01-02
Version: 0.2
License: Proprietary
"""

from datetime import datetime
import json
import os

# Functions
def to_isotime(string_year, string_time):
    return datetime.strptime(f"{string_year}{string_time}", "%Y%m%d%H%M")

def to_stringtime(isotime):
    return isotime.strftime("%Y-%m-%dT%H:%M")

def to_stringday(isotime):
    return isotime.strftime("%d/%m")

def diff_in_hours(iso_start, iso_end):
    delta = iso_end - iso_start
    return delta.total_seconds() / 3600


# --- Ask for input file ---
default_file = "trep.json"
filename = input(f"Input JSON filename [{default_file}]: ").strip() or default_file

input_path = os.path.join("..", "input", filename)

if not os.path.isfile(input_path):
    raise FileNotFoundError(f"Input file not found: {input_path}")

# --- Load JSON ---
with open(input_path, "r", encoding="utf-8") as f:
    json_file_data = json.load(f)

year = json_file_data["year"]
trip = []

# --- Process segments ---
for segment in json_file_data["segments"]:

    start_time = to_isotime(year, segment["start_time"])
    end_time = to_isotime(year, segment["end_time"])
    day_str = to_stringday(start_time)
    hours = diff_in_hours(start_time, end_time)

    # if no entry about the current day yet -> create it with first segment
    if not any(day["date"] == day_str for day in trip):
        trip.append({
            "date": day_str,
            "segments": [{
                "country": segment["country"],
                "time_hours": hours,
                "meals": segment["meals"]
            }]
        })
        continue

    # find the existing day entry
    for day in trip:
        if day["date"] != day_str:
            continue

        countries_in_day = [s["country"] for s in day["segments"]]

        # new country for that day
        if segment["country"] not in countries_in_day:
            day["segments"].append({
                "country": segment["country"],
                "time_hours": hours,
                "meals": segment["meals"]
            })
            break

        # existing country → accumulate
        for s in day["segments"]:
            if s["country"] == segment["country"]:
                s["time_hours"] += hours
                s["meals"] += segment["meals"]
                break

        break  # done handling this segment's day

# --- Output ---
print(json.dumps(trip, indent=2, ensure_ascii=False))

# --- Build output filename from input filename ---
base_name = os.path.splitext(filename)[0]   # removes .json
output_filename = f"{base_name}_seg.json"

output_path = os.path.join("..", "output", output_filename)

with open(output_path, "w", encoding="utf-8") as f:
    json.dump(trip, f, indent=2, ensure_ascii=False)

print(f"\nProcessed data saved to {output_path}")
