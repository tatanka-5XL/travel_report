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

from datetime import datetime, timedelta
import json

# Functions
def to_isotime (string_year, string_time):
    # Add input control!
    return datetime.strptime(
    f"{string_year}{string_time}", "%Y%m%d%H%M")

def to_stringtime (isotime):
    return isotime.strftime("%Y-%m-%dT%H:%M")

def to_stringday (isotime):
    return isotime.strftime("%d/%m")

def diff_in_hours (iso_start, iso_end):
    # Add input control
    delta = iso_end - iso_start
    return delta.total_seconds() / 3600


# Get times in a string form
with open("../input/trep.json", "r", encoding="utf-8") as f:
    json_file_data = json.load(f)

year = json_file_data["year"]
actual_time = None
trip = []
# adding: countries, hours in given country, number of meals

for segment in json_file_data["segments"]:

    start_time = to_isotime(year, segment["start_time"])
    end_time = to_isotime(year, segment["end_time"])
    day_str = to_stringday(start_time)
    hours = diff_in_hours(start_time, end_time)
    
    # if no entry about the current day yet -> create it with first segment
    if not any(day["date"] == day_str for day in trip):
        trip.append({"date": day_str, "segments": [{"country": segment["country"], "time_hours": hours, "meals": segment["meals"]}]})    
        continue # day created + segment added, go to next input segment

    # find the existing day entry
    for day in trip:
        if day["date"] != day_str:
            continue

        # list of countries already stored for this day
        countries_in_day = [s["country"] for s in day["segments"]]

        # if current country not in current day entry -> append new country segment
        if segment["country"] not in countries_in_day:
            day["segments"].append({"country": segment["country"], "time_hours": hours, "meals": segment["meals"]})
            break

        # if country already exists -> add hours/meals to that country's segment
        for s in day["segments"]:
            if s["country"] == segment["country"]:
                s["time_hours"] += hours
                s["meals"] += segment["meals"]
                break

        break # done handling this segment's day       
    
                
print(json.dumps(trip, indent=2, ensure_ascii=False))

with open("../output/trip.json", "w", encoding="utf-8") as f:
    json.dump(trip, f, indent=2, ensure_ascii=False)

