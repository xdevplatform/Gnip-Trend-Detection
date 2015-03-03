import random
import sys

num_topics=int(sys.argv[1])

corpus = []
for line in sys.stdin:
    l = line.split(",")
    if "http://" in l[4] or "https://" in l[4]:
        continue
    corpus.append(line)

random.seed()
for line in random.sample(corpus,num_topics):
    l = line.split(",")
    print("{}".format(l[4]))
