#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Filename: excel.py
Description: Temporary file to input data via exchangeable data format (json)

Author: Tatanka5XL
Created: 2025-12-23
Last Modified: 2026-01-27
Version: 0.3 (day-based waypoint input)
License: Proprietary
"""

import json
import re


def ask(prompt, default=None):
    """Ask a question, allow empty input. If default provided, Enter keeps default."""
    if default is not None and default != "":
        val = input(f"{prompt} [{default}]: ").strip()
        return val if val else str(default)
    return input(f"{prompt}: ").strip()


def ask_int(prompt, default=None):
    val = ask(prompt, default)
    return int(val) if val else 0


def ask_float(prompt, default=None):
    val = ask(prompt, default)
    return float(val) if val else None


def normalize_next(val: str) -> str:
    """Normalize 'next' control values."""
    v = (val or "").strip()
    low = v.lower()
    if low in ("end", "endtrip"):
        return low
    return v  # free-form string allowed


def validate_mmdd(val: str) -> str:
    v = (val or "").strip()
    if not re.fullmatch(r"\d{4}", v):
        raise ValueError("Day must be in MMDD format, e.g. 0312")
    mm = int(v[:2])
    dd = int(v[2:])
    if not (1 <= mm <= 12 and 1 <= dd <= 31):
        raise ValueError("Invalid MMDD value.")
    return v


def validate_hhmm(val: str) -> str:
    v = (val or "").strip()
    if not re.fullmatch(r"\d{4}", v):
        raise ValueError("Time must be in HHMM format, e.g. 0630")
    hh = int(v[:2])
    mm = int(v[2:])
    if not (0 <= hh <= 23 and 0 <= mm <= 59):
        raise ValueError("Invalid HHMM value.")
    return v


data = {}

# --- Basic info ---
data["report_id"] = ask("Report ID")
data["year"] = ask("Year", 2026)

# --- Employee ---
data["employee"] = {
    "name": ask("Employee name", "Petr Pribil"),
    # "company": ask("Company", "Profisolv, s.r.o."),
    # "position": ask("Position", "Sales Eng, Owner"),
}

# --- Trip info ---
data["trip_info"] = {
    "trip_number": ask_int("Trip number"),
    "Trip description": ask("Trip description"),
    "Target locations": ask("Target locations"),
    "transport": {
        "mode": ask("Transport mode", "Company Car"),
        "vehicle_registration": ask("Vehicle registration", "3BF 3073"),
    }
}

# --- Bank rates ---
data["bank_rates"] = {
    "effective_date": ask("Bank rates effective date (MMDD)"),
    "currencies": [{"code": "CZK", "exchange_rate": 1}]
}

print("\nEnter foreign currencies (empty code to finish):")
while True:
    code = ask("Currency code")
    if not code:
        break
    rate = ask_float("Exchange rate")
    data["bank_rates"]["currencies"].append({
        "code": code,
        "exchange_rate": rate
    })

# --- Day-based waypoints ---
# Structure:
# data["waypoints"] = {
#   "0312": [ {time, place, country, meals, next}, ... ],
#   "0313": [ ... ]
# }
data["waypoints"] = {}

print("\nEnter travel days and waypoints.")
print("Rules:")
print(" - First enter day (MMDD).")
print(" - For each day, enter waypoints (time HHMM, place, country, meals, next).")
print(" - 'next' can be any string, or 'end' to finish the day, or 'endtrip' to finish the trip.\n")

last_country = None
end_trip = False

while not end_trip:
    # Ask for day first
    day_raw = ask("Day (MMDD) (empty to finish trip input)")
    if not day_raw:
        break
    try:
        day = validate_mmdd(day_raw)
    except ValueError as e:
        print(f"Invalid day: {e}")
        continue

    data["waypoints"].setdefault(day, [])
    print(f"\n--- Day {day} ---")

    while True:
        # Build one waypoint dict
        try:
            t = validate_hhmm(ask("  Time (HHMM)"))
        except ValueError as e:
            print(f"  Invalid time: {e}")
            continue

        place = ask("  Place")
        country = ask("  Country", last_country or "")
        meals = ask_int("  Meals", 0)

        nxt = normalize_next(
            ask("  Next (string, or 'end' to finish day, or 'endtrip' to finish trip)", "")
        )

        wp = {
            "time": t,
            "place": place,
            "country": country,
            "meals": int(meals),
            "next": nxt
        }
        data["waypoints"][day].append(wp)

        # Remember last country for the next waypoint (and next day)
        if country:
            last_country = country

        if nxt == "end":
            print(f"--- Day {day} closed ---\n")
            break

        if nxt == "endtrip":
            print(f"--- Trip input closed at day {day} ---\n")
            end_trip = True
            break

# --- Bills ---
data["bills"] = []

print("\nEnter bills (empty type to finish):")
while True:
    bill_type = ask("Bill type")
    if not bill_type:
        break

    bill = {
        "type": bill_type,
        "date": ask("Date (YYYY-MM-DD)"),
        "currency": ask("Currency"),
        "amount": ask_float("Amount"),
        "note": ask("Note"),
    }
    data["bills"].append(bill)

# --- Save JSON ---
safe_report_id = re.sub(r"[^A-Za-z0-9_.-]", "_", data["report_id"] or "trip")
filename = f"../input/{safe_report_id}.json"

with open(filename, "w", encoding="utf-8") as f:
    json.dump(data, f, indent=2, ensure_ascii=False)

print(f"\nJSON file saved as {filename}")