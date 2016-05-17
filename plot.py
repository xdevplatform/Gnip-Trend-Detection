#!/usr/bin/env python

import argparse
import ConfigParser
import importlib
import logging

from gnip_trend_detection import models
from gnip_trend_detection.analysis import analyze
from gnip_trend_detection.analysis import plot

logr = logging.getLogger("analyzer")
#logr.setLevel(logging.DEBUG)
if logr.handlers == []:
    fmtr = logging.Formatter('%(asctime)s %(name)s - %(levelname)s - %(message)s') 
    hndlr = logging.StreamHandler()
    hndlr.setFormatter(fmtr)
    logr.addHandler(hndlr) 

parser = argparse.ArgumentParser()
parser.add_argument("-i","--input-file",dest="input_file_name",default="output.pkl") 
parser.add_argument("-c","--config-file",dest="config_file_name",default="config.cfg",help="get configuration from this file")
parser.add_argument("-t","--plot-title",dest="plot_title",default=None) 
parser.add_argument("-d","--analyzed-data-file",dest="analyzed_data_file",default=None) 
parser.add_argument("-v","--verbose",dest="verbose",action="store_true",default=False) 
parser.add_argument("-s","--serializer",dest="serializer",default="pickle") 
args = parser.parse_args()

plot_config = {}

config = ConfigParser.ConfigParser()
config.read(args.config_file_name)
model_name = config.get("analyze","model_name")
model_config = dict(config.items(model_name + "_model")) 
if config.has_section("plot"):
    plot_config = dict(config.items("plot"))
else:
    plot_config["plot_title"] = "output"
    plot_config["plot_dir"] = "."
rebin_items = config.items("rebin")
rebin_config = dict(rebin_items)
rule_name = rebin_config["rule_name"]
if plot_config["plot_title"] == "":
    plot_config["plot_title"] = rule_name
if plot_config["plot_file_name"] == "":
    plot_config["plot_file_name"] = rule_name

plot_config["x_unit"] = str(rebin_config["n_binning_unit"]) + " " + str(rebin_config["binning_unit"])

## manage plot configuration that involves bools
if "logscale_eta" in plot_config:
    plot_config["logscale_eta"] = config.getboolean("plot","logscale_eta")
else:
    plot_config["logscale_eta"] = False
if "use_x_var" in plot_config:
    plot_config["use_x_var"] = config.getboolean("plot","use_x_var")
else:
    plot_config["use_x_var"] = True
if "plot_eta" in plot_config:
    plot_config["plot_eta"] = config.getboolean("plot","plot_eta")
else:
    plot_config["plot_eta"] = True

if args.plot_title is not None:
    plot_config["plot_title"] = args.plot_title
if args.verbose is True:
    logr.setLevel(logging.DEBUG)

serializer = importlib.import_module(args.serializer)
model = getattr(models,model_name)(config=model_config) 
if args.analyzed_data_file is not None:
    plotable_data = serializer.load(open(args.analyzed_data_file))[rule_name]
else:
    generator = serializer.load(open(args.input_file_name))[rule_name]
    plotable_data = analyze(generator,model,None,None,logr)

plot(plotable_data,plot_config)
