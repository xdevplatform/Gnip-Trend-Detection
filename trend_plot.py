#!/usr/bin/env python

import sys
import argparse
import ConfigParser
import importlib
import logging
import csv

from gnip_trend_detection import models
from gnip_trend_detection.analysis import analyze
from gnip_trend_detection.analysis import plot

logr = logging.getLogger("analyzer")
if logr.handlers == []:
    fmtr = logging.Formatter('%(asctime)s %(name)s - %(levelname)s - %(message)s') 
    hndlr = logging.StreamHandler()
    hndlr.setFormatter(fmtr)
    logr.addHandler(hndlr) 

parser = argparse.ArgumentParser()
parser.add_argument("-i","--input-file",dest="input_file_name",default=None) 
parser.add_argument("-c","--config-file",dest="config_file_name",default="config.cfg",help="get configuration from this file")
parser.add_argument("-t","--plot-title",dest="plot_title",default=None) 
parser.add_argument("-v","--verbose",dest="verbose",action="store_true",default=False) 
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
rule_name = rebin_config["counter_name"]
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

if args.input_file_name is None:
    input_generator = csv.reader(sys.stdin)
else:
    input_generator = csv.reader(open(args.input_file_name))

plot(input_generator,plot_config)
