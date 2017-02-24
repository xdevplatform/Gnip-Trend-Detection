#!/usr/bin/env python

import sys
import argparse
import importlib
import logging
import csv
try:
    import ConfigParser as configparser
except ImportError:
    import configparser

from gnip_trend_detection.analysis import analyze
from gnip_trend_detection.analysis import plot

logger = logging.getLogger("plot")
if logger.handlers == []:
    fmtr = logging.Formatter('%(asctime)s %(name)s - %(levelname)s - %(message)s') 
    hndlr = logging.StreamHandler()
    hndlr.setFormatter(fmtr)
    logger.addHandler(hndlr) 

parser = argparse.ArgumentParser()
parser.add_argument("-i","--input-file",dest="input_file_name",default=None) 
parser.add_argument("-c","--config-file",dest="config_file_name",default="config.cfg",help="get configuration from this file")
parser.add_argument("-t","--plot-title",dest="plot_title",default=None) 
parser.add_argument("-o","--output_file_name",dest="output_file_name",default=None) 
parser.add_argument("-v","--verbose",dest="verbose",action="store_true",default=False) 
args = parser.parse_args()

config = configparser.ConfigParser()
config.read(args.config_file_name)

# manage config parameters that can be overwritten with cmd-line options
if args.plot_title is not None:
    config.set("plot","plot_title",args.plot_title)
if args.output_file_name is not None:
    # strip off extension
    if len(args.output_file_name.split('.')) > 1:
        args.output_file_name = '.'.join( args.output_file_name.split('.')[:-1] )
    config.set("plot",'plot_file_name', args.output_file_name )

if args.verbose is True:
    logger.setLevel(logging.DEBUG)

if args.input_file_name is None:
    input_generator = csv.reader(sys.stdin)
else:
    input_generator = csv.reader(open(args.input_file_name))

plot(input_generator,config)
