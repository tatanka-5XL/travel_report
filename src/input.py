#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Filename: excel.py
Description: Temporary file to input data via exchancheable data format (json)

Author: Tatanka5XL
Created: 2025-12-23
Last Modified: 2026-01-10
Version: 0.2 (change from segment to point input)
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
    return int(val) if val else None


def ask_float(prompt, default=None):
    val = ask(prompt, default)
    return float(val) if val else None


def normalize_yesno(val):
    v = (val or "").strip().lower()
    if v in ("y", "yes"):
        return "yes"
    if v in ("n", "no"):
        return "no"
    return v


def normalize_new_country_or_end(val):
    v = (val or "").strip().lower()
    if v == "end":
        return "end"
    if v in ("no", "n", ""):
        return "no"
    return v.upper()


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


# --- Segments ---
data["points"] = []

print("\nEnter travel segments (type 'end' at 'New country' to finish trip segments):")

prefill = {
    "country": None,
    "start_time": None,
    "start_place": None
}

while True:
    country = ask("Country", prefill["country"])

    start_time = ask("Start time (MMDDHHMM)", prefill["start_time"])
    start_place = ask("Start place", prefill["start_place"])

    end_time = ask("End time (MMDDHHMM)")
    end_place = ask("End place")

    # 🔁 MOVED HERE
    meals = ask_int("Meals", 0) or 0

    border_cross = normalize_yesno(
        ask("Border cross (yes/no)", "no")
    )

    new_country = normalize_new_country_or_end(
        ask("New country or 'end' to finish trip", "no")
    )

    segment = {
        "country": country,
        "start_time": start_time,
        "start_place": start_place,
        "end_time": end_time,
        "end_place": end_place,
        "meals": meals,                 # ⬅ moved before border_cross
        "border_cross": border_cross,
        "new_country": new_country
    }

    data["segments"].append(segment)

    # stop segment input if user typed "end"
    if new_country == "end":
        break

    # auto-fill next segment
    if new_country not in ("no", None, ""):
        prefill["country"] = new_country
    else:
        prefill["country"] = country

    prefill["start_place"] = end_place if end_place else None
    prefill["start_time"] = end_time if end_time else None

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
