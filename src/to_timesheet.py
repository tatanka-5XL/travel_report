#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Filename: to_timesheet.py
Description: Parses waypoints in travel report json input and fills in relevant timesheet

Author: Tatanka5XL
Created: 2026-01-29
Last Modified: 2026-01-29
Version: 0.1
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
    """Input like '0112' meaning Jan 12 -> returns datetime(year-01-12)."""
    # mmdd is MMDD
    return datetime.strptime(f"{year}{mmdd}", "%Y%m%d")

def mmdd_to_ddmm(year: str, mmdd: str) -> str:
    d = mmdd_to_date(year, mmdd)
    return d.strftime("%d/%m")

def hhmm_to_hh_colon_mm(hhmm: str) -> str:
    hhmm = str(hhmm).zfill(4)
    return f"{hhmm[:2]}:{hhmm[2:]}"


# ---------------------------
# Build timeline segments
# ---------------------------

def build_segments(data: dict) -> list[dict]:
    """
    Returns list of segments:
      {
        "mmdd": "0113",
        "date_out": "13/01",
        "start_hhmm": "0930",
        "end_hhmm": "1000",
        "type": "drive"|"meeting",
        "country": "IT",
        "place_from": "...",
        "place_to": "...",
        "minutes": int,
        "km": int,
        "rd": int,  # percent
      }
    """
    year = str(data["year"])
    segments = []

    for mmdd in sorted(data["waypoints"].keys(), key=int):
        wps = data["waypoints"][mmdd]
        if not wps or len(wps) < 2:
            continue

        day_dt = mmdd_to_date(year, mmdd)

        def dt_of(hhmm: str) -> datetime:
            return datetime.strptime(f"{day_dt.strftime('%Y%m%d')}{str(hhmm).zfill(4)}", "%Y%m%d%H%M")

        for i in range(len(wps) - 1):
            cur = wps[i]
            nxt = wps[i + 1]

            seg_kind = (cur.get("next") or "").strip().lower()
            if seg_kind not in ("drive", "meeting"):
                # "end", "endtrip", etc -> no segment after this waypoint
                continue

            a = dt_of(cur["time"])
            b = dt_of(nxt["time"])
            if b < a:
                # midnight rollover safety
                b = b.replace(day=b.day + 1)

            minutes = int(round((b - a).total_seconds() / 60.0))
            if minutes < 0:
                minutes = 0

            # km is stored on the ARRIVAL waypoint (your JSON)
            km = int(nxt.get("km", 0) or 0) if seg_kind == "drive" else 0

            segments.append({
                "mmdd": mmdd,
                "date_out": mmdd_to_ddmm(year, mmdd),
                "start_hhmm": str(cur["time"]).zfill(4),
                "end_hhmm": str(nxt["time"]).zfill(4),
                "type": seg_kind,
                "country": (cur.get("country") or "").strip().upper(),
                "place_from": cur.get("place") or "",
                "place_to": nxt.get("place") or "",
                "minutes": minutes,
                "km": km,
                "rd": int(cur.get("r_d", 0) or 0),
            })

    return segments


def find_first_meeting_start(segments: list[dict]) -> tuple[str, str] | None:
    """Returns (mmdd, start_hhmm) for the first meeting segment."""
    for s in segments:
        if s["type"] == "meeting":
            return s["mmdd"], s["start_hhmm"]
    return None


def find_last_meeting_end(segments: list[dict]) -> tuple[str, str] | None:
    """Returns (mmdd, end_hhmm) for the last meeting segment."""
    last = None
    for s in segments:
        if s["type"] == "meeting":
            last = (s["mmdd"], s["end_hhmm"])
    return last


def weighted_avg_meeting_rd(segments: list[dict]) -> float:
    """Weighted average meeting R&D% by meeting minutes."""
    total_min = 0
    weighted = 0
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

    # Trip dates
    day_keys = sorted(data["waypoints"].keys(), key=int)
    trip_from = mmdd_to_ddmm(year, day_keys[0])
    trip_to = mmdd_to_ddmm(year, day_keys[-1])

    # Meeting boundaries
    first_meet = find_first_meeting_start(segs)   # (mmdd, hhmm)
    last_meet = find_last_meeting_end(segs)       # (mmdd, hhmm)

    avg_meet_rd = weighted_avg_meeting_rd(segs)

    # Load workbook
    wb = load_workbook(template_path)
    ws = wb.active  # "Monthly Timesheet"

    # Header fields
    ws["C7"].value = int(data["trip_info"]["trip_number"])
    ws["B5"].value = f"{trip_from} - {trip_to}"

    # Helper to compare (mmdd, hhmm)
    def key(mmdd: str, hhmm: str) -> int:
        return int(mmdd) * 10000 + int(hhmm)

    first_meet_key = key(*first_meet) if first_meet else None
    last_meet_key = key(*last_meet) if last_meet else None

    # Split segments
    travel_there = []
    travel_home = []
    detailed = segs[:]  # all segments

    for s in segs:
        s_key_start = key(s["mmdd"], s["start_hhmm"])
        s_key_end = key(s["mmdd"], s["end_hhmm"])

        if s["type"] == "drive" and first_meet_key is not None and s_key_end <= first_meet_key:
            travel_there.append(s)
        if s["type"] == "drive" and last_meet_key is not None and s_key_start >= last_meet_key:
            travel_home.append(s)

    # Aggregate “one row per day” driving-only blocks
    def aggregate_daily(driving_segments: list[dict]) -> list[dict]:
        by_day = {}
        for s in driving_segments:
            by_day.setdefault(s["mmdd"], []).append(s)

        out = []
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

    # First meeting place for description
    first_meeting_place = None
    for s in segs:
        if s["type"] == "meeting":
            first_meeting_place = s["place_from"]
            break

    # Start writing at row 10
    row = 10

    # “Travel there …” rows (one per day)
    for d in there_days:
        ws.cell(row=row, column=1, value=d["date_out"])  # A Date
        ws.cell(row=row, column=2, value=f"Travel to {first_meeting_place or 'first meeting'}")  # B Desc
        ws.cell(row=row, column=3, value=hhmm_to_hh_colon_mm(d["start_hhmm"]))  # C Start
        ws.cell(row=row, column=4, value=hhmm_to_hh_colon_mm(d["end_hhmm"]))    # D Finish

        rd_pct = round(avg_meet_rd, 2)
        rd_time = round(d["minutes"] * (rd_pct / 100.0), 2)
        ws.cell(row=row, column=5, value=rd_pct)         # E R&D %
        ws.cell(row=row, column=6, value=rd_time)        # F R&D time
        ws.cell(row=row, column=7, value=int(d["minutes"]))  # G Total mins
        ws.cell(row=row, column=8, value=int(d["km"]))       # H km
        row += 1

    # “Travel home” rows (one per day)
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

    # One empty line
    row += 1

    # Detailed segments: one row per drive/meeting
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

    # Save
    out_path = os.path.expanduser(out_path)
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    wb.save(out_path)


# ---------------------------
# Example usage
# ---------------------------
if __name__ == "__main__":
    # Load your JSON input
    json_path = os.path.join("..", "input", "0101_itfr.json")
    with open(json_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    template = "../config/timesheet_template.xlsx"  # adjust for your machine path
    out = os.path.expanduser(f"~/Documents/profi/expenses/timesheet_{data['report_id']}_{data['trip_info']['trip_number']}.xlsx")

    fill_timesheet(template, data, out)
    print("Saved:", out)
           