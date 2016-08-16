#!/usr/bin/env python 

"""

This script operates on a set of CSV-fromatted time series,
such as those produced by the Gnip-Analysis-Pipeline package.

The script re-bins the data on multiple processes using multiprocessing.
The resulting data are then analyzed point-by-point with a trend detection
alogrithm (also in parallel), and plotted.

Command-line argument control the input, output, and config file names,
as well as the switches for doing re-bin, analysis, and plotting.
The config file specifies the model configuration and the time series on which
to operate.

NOTE: by default, neither the rebin, nor the analyzing, nor the plotting are performed. 

"""


import json
import datetime
import time
import argparse
import logging
import sys 
import os
import copy
import csv
import fileinput
import collections
import multiprocessing as mp
try:
    import ConfigParser as configparser
except ImportError:
    import configparser
from gnip_trend_detection.analysis import rebin
from gnip_trend_detection.analysis import analyze as analyzer
from gnip_trend_detection.analysis import plot as plotter
from gnip_trend_detection import models,utils

#lvl = logging.DEBUG
lvl = logging.WARNING

logger = logging.getLogger("analyze")
if logger.handlers == []:
    fmtr = logging.Formatter('%(asctime)s %(module)s:%(lineno)s - %(levelname)s - %(message)s') 
    hndlr = logging.StreamHandler()
    hndlr.setFormatter(fmtr)
    hndlr.setLevel(logging.DEBUG)
    logger.addHandler(hndlr) 
    logger.setLevel(lvl)

# get input, output, and config file naems from cmd-line argument parsing
parser = argparse.ArgumentParser()
parser.add_argument("-c","--config-file",dest="config_file_name",default=None)   
parser.add_argument("-i","--input-file-names",dest="input_file_names",default=None,nargs="+")   
parser.add_argument("-o","--rebinned-file-name",dest="rebinned_file_name",default=None)    
parser.add_argument("-e","--analyzed-file-name",dest="analyzed_file_name",default=None)
parser.add_argument("-r","--do-rebin",dest="do_rebin",action="store_true",default=False,help="do rebin")   
parser.add_argument("-a","--do-analysis",dest="do_analysis",action="store_true",default=False,help="do analysis")   
parser.add_argument("-p","--do-plotting",dest="do_plot",action="store_true",default=False,help="do plotting")   
parser.add_argument("-v","--verbose",dest="verbose",action="store_true",default=False)   
args = parser.parse_args()

# parse config file, which contains model and rule info
if args.config_file_name is not None and not os.path.exists(args.config_file_name) and not os.path.exists("config.cfg"): 
    logger.error("cmd-line argument 'config_file_name' must be a valid config file, or config.cfg must exist")
    sys.exit(1)
else:
    if args.config_file_name is None and os.path.exists("config.cfg"):
        args.config_file_name = "config.cfg"
    
    config = configparser.ConfigParser()
    config.read(args.config_file_name)
    rebin_config = dict(config.items("rebin") )
    model_name = config.get("analyze","model_name")
    model_config = dict(config.items(model_name + "_model"))
    plot_config = dict(config.items("plot")) 
    
    # some plotting silliness
    if "logscale_eta" in plot_config:
        plot_config["logscale_eta"] = config.getboolean("plot","logscale_eta")
    else:
        plot_config["logscale_eta"] = False
    if "plot_eta" in plot_config:
        plot_config["plot_eta"] = config.getboolean("plot","plot_eta")
    else:
        plot_config["plot_eta"] = True

if args.verbose:
    logger.setLevel(logging.INFO)

# process input data if available
input_data = None
if args.input_file_names is not None:
    input_data = collections.defaultdict(list)
    
    input_generator = csv.reader(fileinput.input(args.input_file_names))
    counters = [counter.rstrip('\n') for counter in open(rebin_config["counters_file_name"]) ]
    
    for line in input_generator:
        try:
            counter_name = line[3] 
        except IndexError:
            sys.stderr.write("no 4th field in " + str(line) + '\n')
            continue
        input_data[counter_name].append(line[:3])

logger.info('Finished loading data')

# set up some multiprocessing stuff
pool = mp.Pool()

rebin_output_data = None
if args.do_rebin:
    logger.info('Re-binning...')
    
    if input_data is None:
        sys.stderr.write("Input file(s) must be specified. Exiting.\n")
        sys.exit(1)

    rebin_results = {}
    for counter,data in input_data.items(): 
        # set up config for this job
        config = copy.copy(rebin_config)
        rebin_results[counter] = pool.apply_async(rebin,(data,counter),config) 

    rebin_output_data = {}
    while len(rebin_results) != 0:
        time.sleep(0.1)
        for counter,result in rebin_results.items():
            if result.ready():
                rebin_output_data[counter] = result.get()
                del rebin_results[counter]
                logger.debug("{} results unfinished".format(len(rebin_results)))
                break
    if args.rebinned_file_name is not None:
        json.dump(rebin_output_data,open(args.rebinned_file_name,'wb'))

analyzer_output_data = None
if args.do_analysis:
   
    logger.info('Analyzing...')
    
    # get and configure the model
    model = getattr(models,model_name)(config=model_config) 

    # get input data
    if rebin_output_data is None:
        if args.rebinned_file_name is None:
            if input_data is None:
                sys.stderr.write('No input data available or file specified. Exiting.\n')
                sys.exit(1)
            else:
                # account for input that has not been rebinned
                logger.debug('Using input data directly in analysis')
                analyzer_input_data = input_data
        else: 
            analyzer_input_data = json.load(open(args.rebinned_file_name))
    else:
        analyzer_input_data = rebin_output_data

    analyzer_results = {}
    for counter, counter_data in analyzer_input_data.items():
        if len(counter_data) == 0:
            continue
        #logger.debug(u"submitting analysis for counter: {}".format(counter))
        analyzer_results[counter] = pool.apply_async(analyzer,(counter_data,model)) 

    analyzer_output_data = {}
    while len(analyzer_results) != 0:
        if datetime.datetime.now().second%10 == 0:
            logger.info(str(len(analyzer_results)) + ' analyses remaining')
        time.sleep(0.8)
        for counter,result in list(analyzer_results.items()):
            if result.ready():
                analyzer_output_data[counter] = result.get()
                del analyzer_results[counter]
                logger.debug("{} results unfinished".format(len(analyzer_results)))
                #break
    if args.analyzed_file_name is not None:
        json.dump(analyzer_output_data,open(args.analyzed_file_name,'w'))

if args.do_plot:

    logger.info('Plotting...')

    if analyzer_output_data is None:
        if args.analyzed_file_name is None:
            sys.stderr.write('No analyzed input data available or file specified. Exiting.\n')
            sys.exit(1)
        plotting_input_data = json.load(open(args.analyzed_file_name))
    else:
        plotting_input_data = analyzer_output_data

    # auto-generate this plotting param from re-bin params
    plot_config["x_unit"] = str(rebin_config["n_binning_unit"]) + " " + str(rebin_config["binning_unit"])
    plot_config["plot_dir"] += "{}/".format(model_name)

    for counter, plotable_data in list(plotting_input_data.items()): 
        if len(plotable_data) == 0:
            continue
        # remove spaces in counter name
        counter_name = counter.replace(" ","-")[0:100]
        plot_config["plot_title"] = counter_name
        plot_config["plot_file_name"] = counter_name
        plotter(plotable_data,plot_config) 
    
logger.info('Done.')
