#!/usr/bin/env python

import pickle
import sys
import argparse

import models
import time_bucket

def analyze(input_file_name, model):
    for line in pickle.load(open(input_file_name)):
        tb = line[0]
        count = line[1]
        hour = int(tb.start_time.hour)
        model.update(count=count,hour=hour)
        print("{0} {1:>8} {2:>8.2f} {3:.2f}".format(tb,str(count),model.get_mean(),model.get_eta()))

if __name__ == "__main__":
    
    parser = argparse.ArgumentParser()
    parser.add_argument("-a",dest="alpha",type=float,default=0.95)
    parser.add_argument("-m",dest="mode",default="lc")
    parser.add_argument("-i",dest="input_file_name",default="output.pkl")
    args = parser.parse_args()

    model = models.Poisson(alpha=args.alpha,mode=args.mode)
    
    analyze(args.input_file_name,model)

