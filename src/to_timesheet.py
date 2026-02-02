#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Filename: to_timesheet.py
Description: Parses waypoints in travel report json input and fills in relevant timesheet

Author: Tatanka5XL
Created: 2026-01-29
Last Modified: 2026-02-02
Version: 0.3 - improved segment grouping (avoiding border crossing points etc.)
License: Proprietary
"""

from __future__ import annotations

from datetime import datetime
import os
import json
from openpyxl import load_workbook


# ---------------------------
# Date helpers (MMDD -> DD/MM)
# ---------------------------

def mmdd_to_date(year: str, mmdd: str) -> datetime:
    return datetime.strptime(f"{year}{mmdd}", "%Y%m%d")


def mmdd_to_ddmm(year: str, mmdd: str) -> str:
    return mmdd_to_date(year, mmdd).strftime("%d/%m")


def hhmm_to_hh_colon_mm(hhmm: str) -> str:
    hhmm = str(hhmm).zfill(4)
    return f"{hhmm[:2]}:{hhmm[2:]}"


# ---------------------------
# Build timeline segments (COLLAPSE border-cross drive points)
# ---------------------------

def build_segments(data: dict) -> list[dict]:
    """
    Returns list of segments, but with DRIVE segments collapsed across border waypoints.
    MEETING segments are kept as-is.

    Segment format:
      {
        "mmdd": "0113",
        "date_out": "13/01",
        "start_hhmm": "0930",
        "end_hhmm": "1000",
        "type": "drive"|"meeting",
        "country": "IT",            # for drive: destination country (place_to country)
        "place_from": "...",
        "place_to": "...",
        "minutes": int,
        "km": int,                  # sum of km across collapsed drive parts
        "rd": int,                  # for meeting: cur.r_d ; for drive: 0 (classic)
      }
    """
    year = str(data["year"])
    out: list[dict] = []

    for mmdd in sorted(data["waypoints"].keys(), key=int):
        wps = data["waypoints"][mmdd]
        if not wps or len(wps) < 2:
            continue

        day_dt = mmdd_to_date(year, mmdd)

        def dt_of(hhmm: str) -> datetime:
            hhmm = str(hhmm).zfill(4)
            return datetime.strptime(f"{day_dt.strftime('%Y%m%d')}{hhmm}", "%Y%m%d%H%M")

        i = 0
        while i < len(wps) - 1:
            cur = wps[i]
            nxt = wps[i + 1]

            seg_kind = (cur.get("next") or "").strip().lower()
            if seg_kind not in ("drive", "meeting"):
                i += 1
                continue

            # --- MEETING: keep as-is ---
            if seg_kind == "meeting":
                a = dt_of(cur["time"])
                b = dt_of(nxt["time"])
                if b < a:
                    b = b.replace(day=b.day + 1)

                minutes = int(round((b - a).total_seconds() / 60.0))
                if minutes < 0:
                    minutes = 0

                out.append({
                    "mmdd": mmdd,
                    "date_out": mmdd_to_ddmm(year, mmdd),
                    "start_hhmm": str(cur["time"]).zfill(4),
                    "end_hhmm": str(nxt["time"]).zfill(4),
                    "type": "meeting",
                    "country": (cur.get("country") or "").strip().upper(),
                    "place_from": cur.get("place") or "",
                    "place_to": nxt.get("place") or "",
                    "minutes": minutes,
                    "km": 0,
                    "rd": int(cur.get("r_d", 0) or 0),
                })
                i += 1
                continue

            # --- DRIVE: collapse consecutive drive segments across border waypoints ---
            drive_start_wp = cur
            drive_start_idx = i
            drive_start_time = str(cur["time"]).zfill(4)
            a = dt_of(drive_start_time)

            total_minutes = 0
            total_km = 0

            j = i
            last_arrival_wp = None
            last_end_time = None

            while j < len(wps) - 1:
                w0 = wps[j]
                w1 = wps[j + 1]
                kind0 = (w0.get("next") or "").strip().lower()

                if kind0 != "drive":
                    break  # stop collapsing if next is meeting/end/etc

                # segment j: w0 -> w1 is a drive
                b = dt_of(str(w1["time"]).zfill(4))
                a0 = dt_of(str(w0["time"]).zfill(4))
                if b < a0:
                    b = b.replace(day=b.day + 1)

                minutes = int(round((b - a0).total_seconds() / 60.0))
                if minutes < 0:
                    minutes = 0

                total_minutes += minutes

                # km stored on ARRIVAL waypoint
                total_km += int(w1.get("km", 0) or 0)

                last_arrival_wp = w1
                last_end_time = str(w1["time"]).zfill(4)

                # Decide if we should continue collapsing:
                # continue only if next waypoint exists and current arrival waypoint is "just a border crossing"
                # i.e. next segment is also drive.
                next_kind = (w1.get("next") or "").strip().lower()
                if next_kind != "drive":
                    break

                j += 1

            # Build collapsed drive segment from drive_start_wp -> last_arrival_wp
            if last_arrival_wp is None or last_end_time is None:
                i += 1
                continue

            out.append({
                "mmdd": mmdd,
                "date_out": mmdd_to_ddmm(year, mmdd),
                "start_hhmm": drive_start_time,
                "end_hhmm": last_end_time,
                "type": "drive",
                # destination country
                "country": (last_arrival_wp.get("country") or "").strip().upper(),
                "place_from": drive_start_wp.get("place") or "",
                "place_to": last_arrival_wp.get("place") or "",
                "minutes": int(total_minutes),
                "km": int(total_km),
                "rd": 0,
            })

            # jump i to the end of collapsed block
            i = j + 1

    return out


def find_first_meeting_start(segments: list[dict]) -> tuple[str, str] | None:
    for s in segments:
        if s["type"] == "meeting":
            return s["mmdd"], s["start_hhmm"]
    return None


def find_last_meeting_end(segments: list[dict]) -> tuple[str, str] | None:
    last = None
    for s in segments:
        if s["type"] == "meeting":
            last = (s["mmdd"], s["end_hhmm"])
    return last


def weighted_avg_meeting_rd(segments: list[dict]) -> float:
    total_min = 0
    weighted = 0.0
    for s in segments:
        if s["type"] == "meeting":
            m = int(s["minutes"])
            total_min += m
            weighted += m * float(s["rd"])
    return (weighted / total_min) if total_min else 0.0


# ---------------------------
# Fill the template
# ---------------------------

def fill_timesheet(template_path: str, data: dict, out_path: str) -> None:
    year = str(data["year"])
    segs = build_segments(data)
    if not segs:
        raise ValueError(
            "No segments were built. Check your JSON waypoints / 'next' fields.")

    day_keys = sorted(data["waypoints"].keys(), key=int)
    trip_from = mmdd_to_ddmm(year, day_keys[0])
    trip_to = mmdd_to_ddmm(year, day_keys[-1])

    first_meet = find_first_meeting_start(segs)
    last_meet = find_last_meeting_end(segs)
    avg_meet_rd = weighted_avg_meeting_rd(segs)

    wb = load_workbook(template_path)
    ws = wb.active

    ws["C7"].value = int(data["trip_info"]["trip_number"])
    ws["B5"].value = f"{trip_from} - {trip_to}"

    def key(mmdd: str, hhmm: str) -> int:
        return int(mmdd) * 10000 + int(hhmm)

    first_meet_key = key(*first_meet) if first_meet else None
    last_meet_key = key(*last_meet) if last_meet else None

    travel_there: list[dict] = []
    travel_home: list[dict] = []

    for s in segs:
        s_key_start = key(s["mmdd"], s["start_hhmm"])
        s_key_end = key(s["mmdd"], s["end_hhmm"])

        if s["type"] == "drive" and first_meet_key is not None and s_key_end <= first_meet_key:
            travel_there.append(s)

        if s["type"] == "drive" and last_meet_key is not None and s_key_start >= last_meet_key:
            travel_home.append(s)

    def aggregate_daily(driving_segments: list[dict]) -> list[dict]:
        by_day: dict[str, list[dict]] = {}
        for s in driving_segments:
            by_day.setdefault(s["mmdd"], []).append(s)

        out: list[dict] = []
        for mmdd in sorted(by_day.keys(), key=int):
            items = sorted(by_day[mmdd], key=lambda x: int(x["start_hhmm"]))
            minutes = sum(int(x["minutes"]) for x in items)
            km = sum(int(x["km"]) for x in items)
            out.append({
                "mmdd": mmdd,
                "date_out": items[0]["date_out"],
                "start_hhmm": items[0]["start_hhmm"],
                "end_hhmm": items[-1]["end_hhmm"],
                "minutes": minutes,
                "km": km,
            })
        return out

    there_days = aggregate_daily(travel_there)
    home_days = aggregate_daily(travel_home)

    # first meeting place
    first_meeting_place = None
    for s in segs:
        if s["type"] == "meeting":
            first_meeting_place = s["place_from"]
            break

    # --------- IMPORTANT CHANGE #1: remove travel_there/home segments from detailed ----------
    used_keys = set()
    for s in travel_there + travel_home:
        used_keys.add((s["mmdd"], s["start_hhmm"], s["end_hhmm"], s["type"]))

    detailed = [
        s for s in segs
        if (s["mmdd"], s["start_hhmm"], s["end_hhmm"], s["type"]) not in used_keys
    ]
    # --------------------------------------------------------------------------------------

    row = 10

    # Travel there rows
    for d in there_days:
        ws.cell(row=row, column=1, value=d["date_out"])
        ws.cell(row=row, column=2,
                value=f"Travel to {first_meeting_place or 'first meeting'}")
        ws.cell(row=row, column=3, value=hhmm_to_hh_colon_mm(d["start_hhmm"]))
        ws.cell(row=row, column=4, value=hhmm_to_hh_colon_mm(d["end_hhmm"]))

        rd_pct = round(avg_meet_rd, 2)
        rd_time = round(d["minutes"] * (rd_pct / 100.0), 2)

        ws.cell(row=row, column=5, value=rd_pct)
        ws.cell(row=row, column=6, value=rd_time)
        ws.cell(row=row, column=7, value=int(d["minutes"]))
        ws.cell(row=row, column=8, value=int(d["km"]))
        row += 1

    # Travel home rows
    for d in home_days:
        ws.cell(row=row, column=1, value=d["date_out"])
        ws.cell(row=row, column=2, value="Travel home")
        ws.cell(row=row, column=3, value=hhmm_to_hh_colon_mm(d["start_hhmm"]))
        ws.cell(row=row, column=4, value=hhmm_to_hh_colon_mm(d["end_hhmm"]))

        rd_pct = round(avg_meet_rd, 2)
        rd_time = round(d["minutes"] * (rd_pct / 100.0), 2)

        ws.cell(row=row, column=5, value=rd_pct)
        ws.cell(row=row, column=6, value=rd_time)
        ws.cell(row=row, column=7, value=int(d["minutes"]))
        ws.cell(row=row, column=8, value=int(d["km"]))
        row += 1

    # Blank line
    row += 1

    # Detailed rows (now WITHOUT travel_there/home, and border crossings are already collapsed)
    for s in detailed:
        ws.cell(row=row, column=1, value=s["date_out"])

        if s["type"] == "drive":
            desc = f"Travel to {s['place_to']} ({s['country']})"
        else:
            desc = f"Meeting at {s['place_from']} ({s['country']})"

        ws.cell(row=row, column=2, value=desc)
        ws.cell(row=row, column=3, value=hhmm_to_hh_colon_mm(s["start_hhmm"]))
        ws.cell(row=row, column=4, value=hhmm_to_hh_colon_mm(s["end_hhmm"]))

        rd_pct = float(s["rd"]) if s["type"] == "meeting" else 0.0
        rd_time = round(s["minutes"] * (rd_pct / 100.0), 2)

        ws.cell(row=row, column=5, value=rd_pct)
        ws.cell(row=row, column=6, value=rd_time)
        ws.cell(row=row, column=7, value=int(s["minutes"]))
        ws.cell(row=row, column=8, value=int(s["km"]))
        row += 1

    out_path = os.path.expanduser(out_path)
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    wb.save(out_path)


# ---------------------------
# CLI / usage
# ---------------------------
if __name__ == "__main__":
    default_json = "0101_itfr.json"
    json_filename = input(
        f"Input JSON [{default_json}]: ").strip() or default_json
    json_path = os.path.join("..", "input", json_filename)

    if not os.path.isfile(json_path):
        raise FileNotFoundError(f"Input JSON not found: {json_path}")

    with open(json_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    template = os.path.join("..", "config", "timesheet_template.xlsx")
    if not os.path.isfile(template):
        raise FileNotFoundError(f"Template not found: {template}")

    out = os.path.expanduser(
        f"~/Documents/profi/expenses/timesheet_{data['report_id']}_{data['trip_info']['trip_number']}.xlsx"
    )

    fill_timesheet(template, data, out)
    print("Saved:", out)
