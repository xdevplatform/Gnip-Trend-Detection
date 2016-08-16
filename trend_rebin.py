#!/usr/bin/env python

import logging
import argparse
import os
import fileinput
import sys
import csv
try:
    import ConfigParser as configparser
except ImportError:
    import configparser

from gnip_trend_detection.analysis import rebin
from gnip_trend_detection import utils

"""
The script reads in CSV data in the format: 
    start_time_stamp,interval_duration_in_sec,count[,counter name]
Data are read from stdin or a file. 

NOTE: this script does not filter for a specific counter name.
You must do this yourself.

Inputs are:
    input file name(s)
    start time
    stop time
    bin size and unit
    output file name

Output is a CSV with the following format:
    start_time_stamp,interval_duration_in_sec,count

"""
   
# set up a logger
logger = logging.getLogger("rebin")
logger.setLevel(logging.WARNING)
#logger.setLevel(logging.DEBUG)
if logger.handlers == []:
    fmtr = logging.Formatter('%(asctime)s %(name)s:%(lineno)s - %(levelname)s - %(message)s') 
    hndlr = logging.StreamHandler()
    hndlr.setFormatter(fmtr)
    logger.addHandler(hndlr) 

parser = argparse.ArgumentParser()
parser.add_argument("-c","--config-file",dest="config_file_name",default=None)   
parser.add_argument("-i","--input-file",dest="input_file_names",nargs="+",default=[])    
parser.add_argument("-d","--input-file-base-dir",dest="input_file_base_dir",default=None)   
parser.add_argument("-p","--input-file-postfix",dest="input_file_postfix",default="counts")    
parser.add_argument("-o","--output-file",dest="output_file_name",default=None)    
parser.add_argument("-n","--counter-name",dest="counter_name",default=None)    
parser.add_argument("-v","--verbose",dest="verbose",action="store_true",default=False)    
args = parser.parse_args()

if args.verbose:
    logger.setLevel(logging.INFO)

# figure out input files
if args.input_file_base_dir is not None:
    args.input_file_names = []
    for root, dirnames, filenames in os.walk(args.input_file_base_dir):
        for fname in fnmatch.filter(filenames,"*"+args.input_file_postfix):
            args.input_file_names.append(os.path.join(root,fname))

if len(args.input_file_names) != 0:
    input_generator = csv.reader(fileinput.input(args.input_file_names))
else:
    input_generator = csv.reader(sys.stdin)

# parse config file
if ( args.config_file_name is not None and os.path.exists(args.config_file_name) ) or os.path.exists("config.cfg"): 
    if args.config_file_name is None and os.path.exists("config.cfg"):
        args.config_file_name = "config.cfg"

    config = configparser.ConfigParser()
    config.read(args.config_file_name)
    rebin_config = config.items("rebin") 
    kwargs = dict(rebin_config) 
else:
    kwargs = {}

# do the rebin
data = rebin(input_generator, **kwargs)

# do output
if args.output_file_name is not None:
    output = open(args.output_file_name,"w")
else:
    output = sys.stdout
writer = csv.writer(output) 
for tup in data:
    writer.writerow(tup)
