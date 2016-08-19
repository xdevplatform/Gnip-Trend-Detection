#!/usr/bin/env python

import json
import argparse
import sys

parser = argparse.ArgumentParser()
parser.add_argument("-i","--input-file",dest="input_file",default=None)
parser.add_argument("-t","--theta",dest="theta",default=float(1),type=float)
args = parser.parse_args()

if args.input_file is None:
    sys.stderr.write("Please specify an input file.\n")
    sys.exit(1)

data_summary = json.load(open(args.input_file))

global_max_eta = 0
global_max_eta_counter = None
for counter,data in data_summary.items():
    counter = counter.encode('utf8')
    for dt,ct,eta in data:
        if eta > global_max_eta:
            global_max_eta = eta
            global_max_eta_counter = counter
        if eta > args.theta:
            sys.stdout.write("Theta = {0} was exceeded at {1} by measurement: {2}; eta: {3:.1f}\n".format(args.theta,str(dt),counter,eta))
sys.stdout.write("Max eta was {0:.1f} for measurement {1}\n".format(global_max_eta,global_max_eta_counter))
