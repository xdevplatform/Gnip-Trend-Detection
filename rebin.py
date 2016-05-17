#!/usr/bin/env python

import logging
import argparse
import ConfigParser
import os
import importlib

from gnip_trend_detection.analysis import rebin

"""
The script reads in data in the format: 
 [time_stamp],[rule],[rule_count],[total_count],[interval_duration_in_sec] 
Data are read from a file. 

Inputs are:
    input file name(s)
    rule name
    start time
    stop time
    bin size and unit
    output file name

Output is a .pkl of the list of (TimeBucket,count) pairs.

"""
   
# set up a logger
logr = logging.getLogger("rebin")
logr.setLevel(logging.DEBUG)
if logr.handlers == []:
    fmtr = logging.Formatter('%(asctime)s %(name)s:%(lineno)s - %(levelname)s - %(message)s') 
    hndlr = logging.StreamHandler()
    hndlr.setFormatter(fmtr)
    logr.addHandler(hndlr) 

parser = argparse.ArgumentParser()
parser.add_argument("-c","--config-file",dest="config_file_name",default=None)   
parser.add_argument("-i","--input-file",dest="input_file_names",nargs="+",default=[])    
parser.add_argument("-d","--input-file-base-dir",dest="input_file_base_dir",default=None)   
parser.add_argument("-p","--input-file-postfix",dest="input_file_postfix",default="counts")    
parser.add_argument("-o","--output-file",dest="output_file_name",default="output.pkl")    
parser.add_argument("-v","--verbose",dest="verbose",action="store_true",default=False)    
parser.add_argument("-s","--serializer",dest="serializer",default="pickle")    
args = parser.parse_args()

# parse config file
if args.config_file_name is not None and not os.path.exists(args.config_file_name) and not os.path.exists("config.cfg"): 
    logr.error("cmd-line argument 'config_file_name' must be a valid config file, or config.cfg must exist")
    sys.exit(1)
else:
    if args.config_file_name is None and os.path.exists("config.cfg"):
        args.config_file_name = "config.cfg"

    import ConfigParser as cp 
    config = cp.ConfigParser()
    config.read(args.config_file_name)
    rebin_config = config.items("rebin") 
    kwargs = dict(rebin_config)

if args.input_file_base_dir is not None:
    args.input_file_names = []
    for root, dirnames, filenames in os.walk(args.input_file_base_dir):
        for fname in fnmatch.filter(filenames,"*"+args.input_file_postfix):
            args.input_file_names.append(os.path.join(root,fname))

if args.input_file_names is []:
    sys.stderr.write("Input file(s) must be specified. Exiting.")
    sys.exit(1)

serializer = importlib.import_module(args.serializer)

if args.verbose:
    data = rebin(input_file_names=args.input_file_names,logger_name="rebin",**kwargs)
else:
    data = rebin(input_file_names=args.input_file_names,**kwargs)
serializer.dump({kwargs["rule_name"]:data},open(args.output_file_name,"w"))
