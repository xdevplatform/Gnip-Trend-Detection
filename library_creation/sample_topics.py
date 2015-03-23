import random
import sys

num_topics=int(sys.argv[1])

corpus = []
for line in sys.stdin:
    corpus.append(line)

random.seed()
for line in random.sample(corpus,num_topics):
    print("{}".format(line.rstrip("\n")))
