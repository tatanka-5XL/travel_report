from datetime import datetime
import json


# Get tomes in a string form
with open("../input/trep.json", "r", encoding="utf-8") as f:
    json_file_data = json.load(f)

year = json_file_data["year"]

start_date = json_file_data['trip_info']['start']['date']
start_time = json_file_data['trip_info']['start']['time']

end_date = json_file_data['trip_info']['end']['date']
end_time = json_file_data['trip_info']['end']['time']


# Start and End isodates
start_dt = datetime.strptime(
    f"{year}{start_date}{start_time}", "%Y%m%d%H%M")
start_iso = start_dt.strftime("%Y-%m-%dT%H:%M")

end_dt = datetime.strptime(
    f"{year}{end_date}{end_time}", "%Y%m%d%H%M")
end_iso = end_dt.strftime("%Y-%m-%dT%H:%M")


print(start_iso)
print(end_iso)


# First day
for day in json_file_data["daily_schedule"]:
    print(day)
    print("XXXXXXXX\n")


# Get the difference between times
start = datetime.fromisoformat("2025-03-12T06:30")
end = datetime.fromisoformat("2025-03-13T09:10")

delta = end - start
hours = delta.total_seconds() / 3600

print(hours)   # 2.6666666666666665
