from datetime import datetime, timedelta
import json
import os

# =========================
# Helpers
# =========================

def to_isodate(year_str: str, mmdd: str) -> datetime:
    """year + MMDD -> datetime date at 00:00"""
    return datetime.strptime(f"{year_str}{mmdd}", "%Y%m%d")

def to_isodatetime(year_str: str, mmdd: str, hhmm: str) -> datetime:
    """year + MMDD + HHMM -> datetime"""
    return datetime.strptime(f"{year_str}{mmdd}{hhmm}", "%Y%m%d%H%M")

def to_stringday(date_dt: datetime) -> str:
    return date_dt.strftime("%d/%m")

def diff_in_hours(iso_start: datetime, iso_end: datetime) -> float:
    delta = iso_end - iso_start
    return delta.total_seconds() / 3600

def cz_band(hours: float):
    if hours < 5:
        return None
    if hours < 12:
        return "5_to_12"
    if hours < 18:
        return "12_to_18"
    return "over_18"

def foreign_band(hours: float):
    if hours < 1:
        return None
    if hours < 12:
        return "1_to_12"
    if hours < 18:
        return "12_to_18"
    return "over_18"

def apply_meal_reduction(base_amount: float, pct_per_meal: float, meals: int) -> float:
    factor = 1.0 - (meals * (pct_per_meal / 100.0))
    if factor < 0:
        factor = 0.0
    return base_amount * factor

def build_trip_from_waypoints(json_data: dict) -> list[dict]:
    """
    Build trip overview:
    [
      {
        "date": "12/01",
        "segments": [
          {"country": "CZ", "time_hours": 2.5, "meals": 0},
          {"country": "AT", "time_hours": 7.9, "meals": 0},
          ...
        ]
      },
      ...
    ]
    """
    year = str(json_data["year"])
    waypoints = json_data.get("waypoints", {})

    trip_days: list[dict] = []

    # sort by MMDD as integers (safe for same-year trips)
    for mmdd in sorted(waypoints.keys(), key=lambda x: int(x)):
        wps = waypoints[mmdd] or []
        if not wps:
            continue

        day_date = to_isodate(year, mmdd)
        day_str = to_stringday(day_date)

        # aggregate per country
        agg: dict[str, dict] = {}  # country -> {"time_hours": float, "meals": int}

        # meals: sum per country from waypoint entries
        for wp in wps:
            c = (wp.get("country") or "").strip().upper()
            m = int(wp.get("meals", 0) or 0)
            if not c:
                continue
            agg.setdefault(c, {"country": c, "time_hours": 0.0, "meals": 0})
            agg[c]["meals"] += m

        # time: from waypoint[i] to waypoint[i+1] belongs to waypoint[i]["country"]
        prev_dt = None
        for i in range(len(wps) - 1):
            cur = wps[i]
            nxt = wps[i + 1]

            cur_country = (cur.get("country") or "").strip().upper()
            if not cur_country:
                continue

            cur_dt = to_isodatetime(year, mmdd, str(cur["time"]))
            nxt_dt = to_isodatetime(year, mmdd, str(nxt["time"]))

            # handle midnight rollover inside same "day" input (rare, but safe)
            # If times go backwards, assume next day
            if nxt_dt < cur_dt:
                nxt_dt = nxt_dt + timedelta(days=1)

            hours = diff_in_hours(cur_dt, nxt_dt)
            if hours < 0:
                hours = 0.0

            agg.setdefault(cur_country, {"country": cur_country, "time_hours": 0.0, "meals": 0})
            agg[cur_country]["time_hours"] += hours

            prev_dt = nxt_dt

        day_obj = {"date": day_str, "segments": list(agg.values())}
        trip_days.append(day_obj)

    return trip_days