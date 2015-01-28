#!/usr/bin/env python

import pickle
import sys
import argparse

import models
import time_bucket

parser = argparse.ArgumentParser()
parser.add_argument("-a",dest="alpha",type=float,default=0.95)
parser.add_argument("-m",dest="mode",default="lc")
args = parser.parse_args()

m = models.Poisson(alpha=args.alpha,mode=args.mode)


for line in pickle.load(open("output.pkl")):
    tb = line[0]
    count = line[1]
    hour = int(tb.start_time.hour)
    #print(hour)
    m.update(count=count,hour=hour)
    print("{0} {1:>8} {2:>8.2f} {3:.2f}".format(tb,str(count),m.mean,m.get_eta()))

