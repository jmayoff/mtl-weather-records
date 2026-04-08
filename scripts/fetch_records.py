#!/usr/bin/env python3
"""
fetch_records.py
Fetches daily climate data from Environment Canada (ECCC) for all known
Montréal-area stations, then computes record high/low temperature for
every calendar day-of-year. Outputs:
  data/records.json   — record high & low for each MM-DD, with year & station
  data/stations.json  — metadata about each station queried
"""

import csv
import io
import json
import time
import urllib.request
from collections import defaultdict
from datetime import date, datetime

# ---------------------------------------------------------------------------
# Known Montréal-area station IDs from ECCC Station Inventory
# stationID | Name                                  | Years
# ---------------------------------------------------------------------------
STATIONS = [
    {"id": 5415,  "name": "Montréal/P.E. Trudeau Intl A",   "start": 1941, "end": 2013},
    {"id": 10761, "name": "Montréal/P.E. Trudeau Intl A",   "start": 2013, "end": None},
    {"id": 7024,  "name": "Montréal McGill",                 "start": 1871, "end": 1993},
    {"id": 30165, "name": "Montréal (UQAM)",                 "start": 1993, "end": 2019},
    {"id": 48374, "name": "Montréal McTavish",               "start": 2002, "end": None},
    {"id": 5417,  "name": "Montréal Ville-Marie",            "start": 1941, "end": 1980},
    {"id": 5424,  "name": "Montréal St-Hubert A",            "start": 1928, "end": 2019},
    {"id": 51157, "name": "Montréal St-Hubert A",            "start": 2013, "end": None},
]

BASE_URL = (
    "https://climate.weather.gc.ca/climate_data/bulk_data_e.html"
    "?format=csv&stationID={station_id}&Year={year}&Month=1&Day=1"
    "&timeframe=2&submit=Download+Data"
)

CURRENT_YEAR = date.today().year
PROXY_BASE = "https://api.allorigins.win/raw?url="  # fallback CORS proxy for GH Actions direct HTTP


def fetch_year(station_id: int, year: int, retries: int = 3) -> list[dict]:
    """Download one year of daily data for a station, return list of row dicts."""
    url = BASE_URL.format(station_id=station_id, year=year)
    for attempt in range(retries):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "mtl-weather-dashboard/1.0"})
            with urllib.request.urlopen(req, timeout=30) as resp:
                raw = resp.read().decode("utf-8", errors="replace")
            # ECCC CSVs have a variable-length header block; find the data header row
            lines = raw.splitlines()
            header_idx = None
            for i, line in enumerate(lines):
                if line.startswith('"Date/Time"') or line.startswith("Date/Time"):
                    header_idx = i
                    break
            if header_idx is None:
                return []
            data_str = "\n".join(lines[header_idx:])
            reader = csv.DictReader(io.StringIO(data_str))
            rows = []
            for row in reader:
                rows.append(row)
            return rows
        except Exception as e:
            print(f"  attempt {attempt+1} failed for station {station_id} year {year}: {e}")
            time.sleep(2 ** attempt)
    return []


def parse_temp(val: str) -> float | None:
    """Parse a temperature string to float, returning None on failure."""
    if val is None:
        return None
    v = val.strip().strip('"').replace(",", ".")
    # Flag characters appended by ECCC (e.g. "M", "E", "†")
    v = v.rstrip("MECa†‡^")
    try:
        return float(v)
    except ValueError:
        return None


def main():
    # record_high[mm_dd] = {"temp": float, "year": int, "station_id": int, "station_name": str}
    record_high: dict[str, dict] = {}
    record_low: dict[str, dict] = {}
    station_meta: dict[int, dict] = {}

    for station in STATIONS:
        sid = station["id"]
        sname = station["name"]
        start = station["start"]
        end = station["end"] or CURRENT_YEAR

        years_scanned = 0
        years_with_data = 0
        print(f"\n=== Station {sid}: {sname} ({start}–{end}) ===")

        for year in range(start, end + 1):
            rows = fetch_year(sid, year)
            if not rows:
                continue
            years_scanned += 1
            got_data = False

            for row in rows:
                # Find the date field (name varies slightly across eras)
                date_val = row.get("Date/Time") or row.get("Date/Time (LST)") or ""
                date_val = date_val.strip().strip('"')
                if len(date_val) < 10:
                    continue
                try:
                    d = datetime.strptime(date_val[:10], "%Y-%m-%d")
                except ValueError:
                    continue

                mm_dd = f"{d.month:02d}-{d.day:02d}"

                # ECCC column names differ slightly; handle both old and new
                max_temp_raw = (
                    row.get("Max Temp (°C)")
                    or row.get("Max Temp (\xb0C)")
                    or row.get("Max Temp (C)")
                    or row.get("Max Temp")
                    or ""
                )
                min_temp_raw = (
                    row.get("Min Temp (°C)")
                    or row.get("Min Temp (\xb0C)")
                    or row.get("Min Temp (C)")
                    or row.get("Min Temp")
                    or ""
                )

                max_t = parse_temp(max_temp_raw)
                min_t = parse_temp(min_temp_raw)

                if max_t is not None:
                    got_data = True
                    if mm_dd not in record_high or max_t > record_high[mm_dd]["temp"]:
                        record_high[mm_dd] = {
                            "temp": max_t,
                            "year": d.year,
                            "station_id": sid,
                            "station_name": sname,
                        }

                if min_t is not None:
                    got_data = True
                    if mm_dd not in record_low or min_t < record_low[mm_dd]["temp"]:
                        record_low[mm_dd] = {
                            "temp": min_t,
                            "year": d.year,
                            "station_id": sid,
                            "station_name": sname,
                        }

            if got_data:
                years_with_data += 1

            # Be polite to the ECCC server
            time.sleep(0.3)

        station_meta[sid] = {
            "name": sname,
            "start": start,
            "end": end,
            "years_scanned": years_scanned,
            "years_with_data": years_with_data,
        }
        print(f"  → {years_with_data}/{years_scanned} years had usable data")

    # Build final output
    records = {}
    all_keys = set(list(record_high.keys()) + list(record_low.keys()))
    for mm_dd in all_keys:
        records[mm_dd] = {
            "high": record_high.get(mm_dd),
            "low": record_low.get(mm_dd),
        }

    output = {
        "generated": datetime.utcnow().isoformat() + "Z",
        "records": records,
    }

    with open("data/records.json", "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)
    print("\n✓ Wrote data/records.json")

    stations_out = [
        {"id": k, **v} for k, v in station_meta.items()
    ]
    with open("data/stations.json", "w", encoding="utf-8") as f:
        json.dump(stations_out, f, ensure_ascii=False, indent=2)
    print("✓ Wrote data/stations.json")


if __name__ == "__main__":
    main()
