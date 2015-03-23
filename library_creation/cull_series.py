import json
import sys

check_zeros = False
if len(sys.argv) > 1 and sys.argv[1] == "-0":
    check_zeros = True

for line in sys.stdin:
    data = json.loads(line)
    for topic,time_series in data.items():
        num_zeros = 0
        for ct in time_series:
            if ct == 0:
                num_zeros += 1
        if not check_zeros or float(num_zeros)/len(time_series) < 0.1: 
            sys.stdout.write(json.dumps(data) + "\n")

