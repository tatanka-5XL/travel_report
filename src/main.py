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

# VarA Create time log for every segment?
time_log = []
time_log.append([start_iso, json_file_data["trip_info"]["start"]
                ["country"], json_file_data["trip_info"]["start"]["place"]])

# print("Trip started in " + time_log[0][2] + " in " +
#      time_log[0][1] + " at " + time_log[0][0] + ".")

# for log in time_log:
#    for item in log:
#        print(item)

# VarB Border crossing identification?
print("Trip started in " + json_file_data["trip_info"]["start"]
      ["country"] + " in " +
      json_file_data["trip_info"]["start"]["place"] + " at " + start_iso + ".")


for day in json_file_data["segments"]:
    for day, seg_list in day.items():
        if seg_list["border_cross_time"] == "no_cross":
            # calculate perdiems
            continue
        if segment.value().len() <= 1:
            print("None or one segment only in ." + segment.key())
            continue

# create functions:
# def check_time_input ("ddmm")
# def calculate_perdiems_cz():
# def calculate_perdiems_abroad():

# Get the difference between times
start = datetime.fromisoformat("2025-03-12T06:30")
end = datetime.fromisoformat("2025-03-13T09:10")

delta = end - start
hours = delta.total_seconds() / 3600

print(hours)   # 2.6666666666666665
