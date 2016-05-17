#!/usr/bin/env python

import importlib
import argparse
import logging
import ConfigParser

from gnip_trend_detection.analysis import analyze
from gnip_trend_detection import models

logr = logging.getLogger("analyzer")
if logr.handlers == []:
    fmtr = logging.Formatter('%(asctime)s %(name)s - %(levelname)s - %(message)s') 
    hndlr = logging.StreamHandler()
    hndlr.setFormatter(fmtr)
    logr.addHandler(hndlr) 

parser = argparse.ArgumentParser()
parser.add_argument("-i","--input-file",dest="input_file_name",default="output.pkl") 
parser.add_argument("-d","--analyzed-file",dest="analyzed_data_file",default=None) 
parser.add_argument("-c","--config-file",dest="config_file_name",default="config.cfg",help="get configuration from this file")
parser.add_argument("-v","--verbose",dest="verbose",action="store_true",default=False)
parser.add_argument("-s","--serializer",dest="serializer",default="pickle") 
args = parser.parse_args()

config = ConfigParser.SafeConfigParser()
config.read(args.config_file_name)
model_name = config.get("analyze","model_name")
model_config = dict(config.items(model_name + "_model"))

if args.verbose:
    logr.setLevel(logging.DEBUG)

serializer = importlib.import_module(args.serializer)

rule_name = config.get("rebin","rule_name")
model = getattr(models,model_name)(config=model_config) 
generator = serializer.load(open(args.input_file_name))[rule_name] 
plotable_data = analyze(generator,model,None,None,logr)
if args.analyzed_data_file is not None:
    serializer.dump({rule_name:plotable_data},open(args.analyzed_data_file,"w"))

