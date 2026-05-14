import json

string_new = ""
with open("jj.json", "r") as f:
    data = f.read()
    data = json.loads(data)
    for j in data:
        print(type(j), j)
        time_logs = j.get("time_logs", [])
        for log in time_logs:
            activity = log.get("activity", "")
            start_time = log.get("start_time", "")
            end_time = log.get("end_time", "")
            string_new += f"Start Time: {start_time}, End Time: {end_time} Activity: {activity}\n\n"
with open("jj.txt", "w") as f:
    f.write(string_new)
print(string_new)