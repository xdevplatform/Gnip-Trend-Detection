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

"""
Calculate Pearson's correlation coefficient 
for all pairs of time series
"""

parser = argparse.ArgumentParser()
parser.add_argument("-i","--input-file",dest="input_file_names",nargs="+",default=None,help="input CSV file(s)")
parser.add_argument("-p","--precision",dest="precision",default=4,help="correlation coefficient precision")
args = parser.parse_args()

if args.input_file_names is None:
    line_generator = csv.reader(sys.stdin)
else:
    line_generator = csv.reader(fileinput.input(args.input_file_names))

counters = collections.defaultdict(list)

for line in line_generator:
    dt = dt_parse(line[0])
    tb_size_in_sec,count,counter = line[1:]
    counters[counter].append(int(count))

print(counters)
results = []
for pair in itertools.combinations(counters.keys(),2):
    series_0 = counters[pair[0]]
    series_1 = counters[pair[1]]
    # corrcoef return the covariance matrix; get the off-diag element
    r = np.corrcoef(series_0,series_1)[0][1]
    r_round = round(r,args.precision)
    results.append((pair,r_round))

for pair,r in sorted(results,key=operator.itemgetter(1)): 
    sys.stdout.write("{},{},{}\n".format(r,pair[0],pair[1]))
