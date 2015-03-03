import json
import sys

for line in sys.stdin:
    data = json.loads(line)
    for topic,time_series in data.items():
        num_zeros = 0
        for ct in time_series:
            if ct == 0:
                num_zeros += 1
        if float(num_zeros)/len(time_series) < 0.1: 
            sys.stdout.write(json.dumps(data) + "\n")

