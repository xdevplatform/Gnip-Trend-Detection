#!/usr/bin/env python

import pickle
import sys
import argparse
import logging

import models
import time_bucket

logr = logging.getLogger("analyzer")
logr.setLevel(logging.DEBUG)
#fmtr = logging.Formatter('%(asctime)s %(name)s - %(levelname)s - %(message)s') 
#hndlr = logging.StreamHandler()
#hndlr.setFormatter(fmtr)
#logr.addHandler(hndlr) 

def analyze(generator, model, period_list = ["hour"]):
    plotable_data = [] 
    for line in generator:
        tb = line[0]
        count = line[1]
        period = ":".join([str(getattr(tb.start_time,p)) for p in period_list])
        logr.debug("period: {}".format(period))
        model.update(count=count,period=period)
        plotable_data.append( (tb,count,model.get_res ult()) )
        logr.debug("{0} {1:>8} {2:>8.2f} {3:.2f}".format(tb,str(count),model.get_result())) 
    return plotable_data

if __name__ == "__main__":
    
    parser = argparse.ArgumentParser()
    parser.add_argument("-a",dest="alpha",type=float,default=0.95)
    parser.add_argument("-m",dest="mode",default="lc")
    parser.add_argument("-p",dest="period_list",default="hour",nargs="+")
    parser.add_argument("-i",dest="input_file_name",default="output.pkl")
    args = parser.parse_args()

    model = models.Poisson(alpha=args.alpha,mode=args.mode)

    generator = pickle.load(open(args.input_file_name))
    analyze(generator,model,args.period_list)

