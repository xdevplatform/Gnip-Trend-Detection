#!/usr/bin/env python

import sys
import csv
import importlib
import argparse
import logging
try:
    import ConfigParser as configparser
except ImportError:
    import configparser
    
from gnip_trend_detection.analysis import analyze
from gnip_trend_detection import models

# logging
logger = logging.getLogger("analyze")
if logger.handlers == []:
    fmtr = logging.Formatter('%(asctime)s %(name)s - %(levelname)s - %(message)s') 
    hndlr = logging.StreamHandler()
    hndlr.setFormatter(fmtr)
    logger.addHandler(hndlr) 

# parse arguments
parser = argparse.ArgumentParser()
parser.add_argument("-i","--input-file",dest="input_file_name",default=None) 
parser.add_argument("-o","--analyzed-file",dest="analyzed_data_file",default=None) 
parser.add_argument("-c","--config-file",dest="config_file_name",default="config.cfg",help="get configuration from this file")
parser.add_argument("-v","--verbose",dest="verbose",action="store_true",default=False)
args = parser.parse_args()

# read config file
config = configparser.SafeConfigParser()
config.read(args.config_file_name)
model_name = config.get("analyze","model_name")
model_config = dict(config.items(model_name + "_model"))

if args.verbose:
    logger.setLevel(logging.DEBUG)

model = getattr(models,model_name)(config=model_config) 

# set up input
if args.input_file_name is not None:
    generator = csv.reader(open(args.input_file_name))
else:
    generator = csv.reader(sys.stdin)

# do the analysis
plotable_data = analyze(generator,model)

# output
if args.analyzed_data_file is not None:
    output = open(args.analyzed_data_file,'w')
else:
    output = sys.stdout
writer = csv.writer(output)
for row in plotable_data:
    writer.writerow(row)
