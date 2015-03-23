import sys
import datetime

data = {}

for line in sys.stdin:
    l = line.split('|')
    time = datetime.datetime.strptime(l[1],"%Y-%m-%d %H:%M:%S.0") 
    topic = l[2]

    if topic not in data:
        data[topic] = (time,time)
    else:
        data[topic] = (data[topic][0],time)

for topic,tup in data.items():
    dt = tup[1] - tup[0]

    if dt.total_seconds() > 60*30 and dt.total_seconds() < 24*60*60:
        sys.stdout.write("{}|{}\n".format(topic.rstrip('\n'),tup[0]))
