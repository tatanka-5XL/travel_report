from datetime import datetime
import json



def to_isotime (string_year, string_time):
    # Add input control!
    return datetime.strptime(
    f"{string_year}{string_time}", "%Y%m%d%H%M")


# Get times in a string form
with open("../input/trep.json", "r", encoding="utf-8") as f:
    json_file_data = json.load(f)

year = json_file_data["year"]
start_time_strg = json_file_data['trip_info']['start']['datetime']
end_time_strg = json_file_data['trip_info']['end']['datetime']

# Set up start and actual time
start_time = to_isotime(start_time_strg)

print("Trip started in " + json_file_data["trip_info"]["start"]
      ["country"] + " in " +
      json_file_data["trip_info"]["start"]["place"] + " at " + start_time + ".")

actual_time = start_time

for segment in json_file_data["segments"]:
    
    continue
        




# create functions:
# def calculate_perdiems_cz():
# def calculate_perdiems_abroad():

# Get the difference between times
# start = datetime.fromisoformat("2025-03-12T06:30")
# end = datetime.fromisoformat("2025-03-13T09:10")

# delta = end - start
# hours = delta.total_seconds() / 3600

# print(hours)   # 2.6666666666666665