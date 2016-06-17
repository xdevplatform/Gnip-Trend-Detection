#!/usr/bin/env python 

import collections
import itertools
import sys
import operator
import argparse
import csv
import fileinput
from dateutil.parser import parse as dt_parse

import numpy as np

parser = argparse.ArgumentParser()
parser.add_argument("-i","--input-file",dest="input_file_names",nargs="+",default=None,help="input CSV file(s)")
parser.add_argument("-p","--precision",dest="precision",default=5,help="correlation coefficient precision")
args = parser.parse_args()

if args.input_file_names is None:
    line_generator = csv.reader(sys.stdin)
else:
    line_generator = csv.reader(fileinput.input(args.input_file_names))

measurements = collections.defaultdict(list)

for line in line_generator:
    dt = dt_parse(line[0])
    measurement,count,total_count,tb_size_in_sec = line[1:]
    measurements[measurement].append(int(count))

results = []
for pair in itertools.combinations(measurements.keys(),2):
    series_0 = measurements[pair[0]]
    series_1 = measurements[pair[1]]
    r = np.corrcoef(series_0,series_1)[0][1]
    r_round = round(r,args.precision)
    results.append((pair,r_round))

for pair,r in sorted(results,key=operator.itemgetter(1)): 
    sys.stdout.write("{},{},{}\n".format(r,pair[0],pair[1]))
