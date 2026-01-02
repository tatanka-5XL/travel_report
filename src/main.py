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
start_time_strg = json_file_data['trip_info']['start']['datetime']
end_time_strg = json_file_data['trip_info']['end']['datetime']

# Set up start and actual time
start_time = to_isotime(year, start_time_strg)
end_time = to_isotime(year, end_time_strg)

print("Trip started in " + json_file_data["trip_info"]["start"]
      ["country"] + " in " +
      json_file_data["trip_info"]["start"]["place"] + " at " + to_stringtime(start_time) + ".")

actual_time = start_time

for segment in json_file_data["segments"]:
    new_time = to_isotime(year, segment["end_time"])
    if segment["border_cross"] == "no":
        hours_difference = diff_in_hours(actual_time, new_time)
        print(hours_difference)
        if (hours_difference < 24):
            print("The rest of " + to_stringday(new_time) + " was spent in " + segment["place"] + ", which was reached at " + to_stringtime(new_time) + ".")
        else:
            print("On " + to_stringday(new_time - timedelta(hours=12)) + ", whole day was spent in " + segment["country"] + ".")
            print("Then, on " + to_stringday(new_time) + ":")
    else:
        print("The trip continued to " + segment["country"] + " border, which was reached at " + to_stringtime(new_time) + ".")        
    actual_time = new_time        

print("The trip was ended in " + json_file_data["trip_info"]["end"]
      ["country"] + " in " +
      json_file_data["trip_info"]["end"]["place"] + " at " + to_stringtime(end_time) + ".")




# create functions:
# def calculate_perdiems_cz():
# def calculate_perdiems_abroad():

# Get the difference between times
# start = datetime.fromisoformat("2025-03-12T06:30")
# end = datetime.fromisoformat("2025-03-13T09:10")

# delta = end - start
# hours = delta.total_seconds() / 3600

# print(hours)   # 2.6666666666666665