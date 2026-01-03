#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Filename: main.py
Description: Parses segments in travel report json input and calculates times and perdiems.

Author: Tatanka5XL
Created: 2025-12-23
Last Modified: 2026-01-03
Version: 0.3
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

# Calculating perdiems and pocket money

# --- Load settings.json ---
settings_path = os.path.join("..", "input", "../config/settings.json")
with open(settings_path, "r", encoding="utf-8") as f:
    settings = json.load(f)

cz_rates = settings["cz"]["per_diems_czk"]
cz_meal_reduce = settings["cz"]["lowering_percents_per_meal"]

foreign_rates_raw = settings["foreign"]["per_diems"]
foreign_percents = settings["foreign"]["per_diems_percents"]
foreign_meal_reduce = settings["foreign"]["lowering_percents_per_meal"]

# --- FX map from trip input (CZK per 1 unit currency) ---
fx_czk = {}
for c in json_file_data.get("bank_rates", {}).get("currencies", []):
    code = (c.get("code") or "").upper()
    rate = c.get("exchange_rate")
    if code and rate is not None:
        fx_czk[code] = float(rate)

# Build mapping: country -> {"rate": 50, "currency": "EUR"} from keys like "PL_eur"
foreign_rates = {}
for k, v in foreign_rates_raw.items():
    country, cur = k.split("_", 1)
    foreign_rates[country] = {"rate": float(v), "currency": cur.upper()}

def cz_band(hours: float):
    if hours < 5:
        return None
    if hours < 12:
        return "5_to_12"
    if hours < 18:
        return "12_to_18"
    return "over_18"

def foreign_percent_band(hours_abroad: float):
    # entitlement bands for foreign: 1_to_12, 12_to_18, over_18
    if hours_abroad < 1:
        return None
    if hours_abroad < 12:
        return "1_to_12"
    if hours_abroad < 18:
        return "12_to_18"
    return "over_18"

def apply_meal_reduction(base_amount: float, pct_per_meal: float, meals: int) -> float:
    # reduce by pct_per_meal * meals, cap at 0
    factor = 1.0 - (meals * (pct_per_meal / 100.0))
    if factor < 0:
        factor = 0.0
    return base_amount * factor

def pick_highest_foreign_rate_country_czk(foreign_countries: set[str]):
    """
    Pick the country with highest foreign per diem DAILY RATE among countries visited,
    comparing in CZK equivalent using fx rates.
    Returns (country, rate, currency, rate_czk_equiv).
    """
    best = None
    for country in foreign_countries:
        if country not in foreign_rates:
            raise KeyError(f"No foreign per diem rate in settings.json for country: {country}")
        rate = foreign_rates[country]["rate"]
        cur = foreign_rates[country]["currency"]
        fx = fx_czk.get(cur)
        if fx is None:
            raise KeyError(f"No FX rate for currency {cur} in trip bank_rates.currencies")
        rate_czk = rate * fx
        if best is None or rate_czk > best[3]:
            best = (country, rate, cur, rate_czk)
    return best  # (country, rate, cur, rate_czk)

# --- Calculate per diems for each day (CZ + foreign) ---
for day in trip:
    day["per_diem"] = []
    comments = []

    # ---------- CZ ----------
    cz_seg = next((s for s in day["segments"] if s["country"] == "CZ"), None)
    cz_hours = float(cz_seg.get("time_hours", 0) or 0) if cz_seg else 0.0
    cz_meals = int(cz_seg.get("meals", 0) or 0) if cz_seg else 0

    cz_key = cz_band(cz_hours)
    if cz_key is None:
        cz_base = 0.0
        cz_final = 0.0
        cz_lowered = 0.0
        day["per_diem"].append({
            "country": "CZ", "currency": "CZK",
            "band": "under_5", "base": 0,
            "meals": cz_meals, "reduction_percent_per_meal": None,
            "amount": 0
        })
        if cz_seg:
            comments.append(f"CZ: {cz_hours:.2f}h <5h ⇒ stravné 0 CZK.")
    else:
        cz_base = float(cz_rates[cz_key])
        cz_pct = float(cz_meal_reduce[cz_key])
        cz_final = apply_meal_reduction(cz_base, cz_pct, cz_meals)
        cz_lowered = cz_base - cz_final

        day["per_diem"].append({
            "country": "CZ", "currency": "CZK",
            "band": cz_key, "base": cz_base,
            "meals": cz_meals, "reduction_percent_per_meal": cz_pct,
            "amount": round(cz_final, 2)
        })
        comments.append(
            f"CZ: {cz_hours:.2f}h ⇒ base {cz_base:.2f} CZK ({cz_key}); "
            f"meals {cz_meals} → lowered {cz_lowered:.2f} CZK; paid {cz_final:.2f} CZK."
        )

    # ---------- FOREIGN ----------
    foreign_segs = [s for s in day["segments"] if s["country"] != "CZ"]
    if not foreign_segs:
        day["comment"] = " | ".join(comments) if comments else ""
        continue

    total_foreign_hours = sum(float(s.get("time_hours", 0) or 0) for s in foreign_segs)
    total_foreign_meals = sum(int(s.get("meals", 0) or 0) for s in foreign_segs)
    foreign_countries = {s["country"] for s in foreign_segs}

    # NEW RULE #1:
    # If CZ >= 5h but foreign < 5h => no foreign per diem
    if cz_hours >= 5 and total_foreign_hours < 5:
        day["per_diem"].append({
            "country": "FOREIGN",
            "currency": None,
            "band": "blocked_by_rule_cz5_foreign<5",
            "base_rate": None,
            "percent": 0,
            "base": 0,
            "foreign_hours_total": round(total_foreign_hours, 2),
            "meals": total_foreign_meals,
            "reduction_percent_per_meal": None,
            "amount": 0
        })
        comments.append(
            f"FOREIGN: {total_foreign_hours:.2f}h abroad but CZ {cz_hours:.2f}h ≥5h and abroad <5h ⇒ foreign stravné 0."
        )
        day["comment"] = " | ".join(comments)
        continue

    # entitlement band by total foreign hours (1h minimum still applies)
    pct_key = foreign_percent_band(total_foreign_hours)
    if pct_key is None:
        day["per_diem"].append({
            "country": "FOREIGN",
            "currency": None,
            "band": "under_1",
            "base_rate": None,
            "percent": 0,
            "base": 0,
            "foreign_hours_total": round(total_foreign_hours, 2),
            "meals": total_foreign_meals,
            "reduction_percent_per_meal": None,
            "amount": 0
        })
        comments.append(f"FOREIGN: {total_foreign_hours:.2f}h <1h ⇒ foreign stravné 0.")
        day["comment"] = " | ".join(comments)
        continue

    # NEW RULE #2:
    # If multiple foreign countries, pick highest DAILY RATE among countries visited
    best_country, best_rate, best_cur, best_rate_czk = pick_highest_foreign_rate_country_czk(foreign_countries)

    percent = float(foreign_percents[pct_key])
    foreign_base = best_rate * (percent / 100.0)

    # Meal reduction for foreign uses same bands: 1_to_12 / 12_to_18 / over_18 (per your correction)
    red_key = pct_key
    red_pct = float(foreign_meal_reduce.get(red_key, 0))
    foreign_final = apply_meal_reduction(foreign_base, red_pct, total_foreign_meals)
    foreign_lowered = foreign_base - foreign_final

    day["per_diem"].append({
        "country": best_country,
        "currency": best_cur,
        "band": pct_key,
        "base_rate": best_rate,
        "base_rate_czk_equiv": round(best_rate_czk, 2),
        "percent": percent,
        "base": round(foreign_base, 2),
        "foreign_hours_total": round(total_foreign_hours, 2),
        "foreign_countries_visited": sorted(list(foreign_countries)),
        "meals": total_foreign_meals,
        "reduction_percent_per_meal": red_pct,
        "amount": round(foreign_final, 2)
    })

    comments.append(
        f"FOREIGN: {total_foreign_hours:.2f}h in {sorted(list(foreign_countries))} ⇒ using highest rate {best_country} "
        f"({best_rate:.2f} {best_cur}/day, ~{best_rate_czk:.2f} CZK/day); band {pct_key} ({percent:.1f}%) "
        f"→ base {foreign_base:.2f} {best_cur}; meals {total_foreign_meals} → lowered {foreign_lowered:.2f} {best_cur}; "
        f"paid {foreign_final:.2f} {best_cur}."
    )

    # NEW RULE #3: comment per day
    day["comment"] = " | ".join(comments)


# --- Output ---
print(json.dumps(trip, indent=2, ensure_ascii=False))

# --- Build output filename from input filename ---
base_name = os.path.splitext(filename)[0]   # removes .json
output_filename = f"{base_name}_seg.json"

output_path = os.path.join("..", "output", output_filename)

with open(output_path, "w", encoding="utf-8") as f:
    json.dump(trip, f, indent=2, ensure_ascii=False)

print(f"\nProcessed data saved to {output_path}")
