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
lvl = logging.INFO

logger = logging.getLogger("rebin-analyze-plot")
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
parser.add_argument("-i",
        dest="input_file_names",default=None,nargs="+",
        help="input file name(s) for CSV data to rebin or analyze")   
parser.add_argument("-r",
        dest="rebin_output_file_name",default=None,
        help="output file name for JSON-formatted re-binned data")    
parser.add_argument("-a",
        dest="analysis_input_file_name",default=None,
        help="input file name for JSON-formatted data to be analyzed")    
parser.add_argument("-o",
        dest="analysis_output_file_name",default=None,
        help="output file name for JSON-formatted analyzed data")    
parser.add_argument("-p",
        dest="plot_input_file_name",default=None,
        help="input file name for JSON-formatted data to be plotted")    
parser.add_argument("--rebin",dest="do_rebin",action="store_true",default=False,help="do rebin")   
parser.add_argument("--analysis",dest="do_analysis",action="store_true",default=False,help="do analysis")   
parser.add_argument("--plot",dest="do_plot",action="store_true",default=False,help="do plotting")   
parser.add_argument("-v","--verbose",dest="verbose",action="store_true",default=False)   
args = parser.parse_args()

# parse config file, which contains model and rule info
if args.config_file_name is not None and not os.path.exists(args.config_file_name) and not os.path.exists("config.cfg"): 
    logger.error("cmd-line argument 'config_file_name' must reference a valid config file, or config.cfg must exist")
    sys.exit(1)
else:
    if args.config_file_name is None and os.path.exists("config.cfg"):
        args.config_file_name = "config.cfg"
    logger.info('Using {} for configuration.'.format(args.config_file_name))
    
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

# warn if option configuration will return no results
if args.do_rebin and not args.do_analysis and args.rebin_output_file_name is None: 
    logger.error('No rebin output file specified or further analysis requested, so rebin results will be lost!')
    sys.exit(1)
if args.do_analysis and not args.do_plot and args.analysis_output_file_name is None:
    logger.error('No analysis output file specified or further plotting requested, so analysis results will be lost!')
    sys.exit(1)

# warn if options configure ambiguous input 
if args.do_analysis and args.do_rebin and args.analysis_input_file_name is not None:
    logger.error('Input to analysis step is ambigious. Exiting.')
    sys.exit(1)
if args.do_rebin and args.do_plot and args.plot_input_file_name is not None:
    logger.error('Input to plotting step is ambigious. Exiting.')
    sys.exit(1)

# process input data if available
input_data = None
if args.input_file_names is not None:
    logger.info('Loading CSV data...')  
    input_data = collections.defaultdict(list)
    
    input_generator = csv.reader(fileinput.input(args.input_file_names))
    counters = [counter.rstrip('\n') for counter in open(rebin_config["counters_file_name"]) ]
    
    for line in input_generator:
        try:
            counter_name = line[3] 
        except IndexError:
            logger.debug("no 4th field in " + str(line))
            continue
        if counter_name in counters:
            input_data[counter_name].append(line[:3])

    logger.info('Finished loading CSV data')

# set up the multiprocessing stuff
pool = mp.Pool()

rebin_output_data = None
if args.do_rebin:
    logger.info('Re-binning...')
    
    if input_data is None:
        sys.stderr.write("Input file(s) must be specified with '-i'. Exiting.\n")
        sys.exit(1)

    rebin_results = {}
    for counter,data in input_data.items(): 
        # set up config for this job
        config = copy.copy(rebin_config)
        rebin_results[counter] = pool.apply_async(rebin,(data,),config) 

    rebin_output_data = {}
    num_rebin_results = len(rebin_results)
    while num_rebin_results != 0:
        if datetime.datetime.now().second%10 == 0:
            logger.info(str(num_rebin_results) + ' rebins remaining') 
            time.sleep(1)
        logger.debug("{} results unfinished".format(num_rebin_results))
        for counter,result in list(rebin_results.items()):
            if result.ready():
                rebin_output_data[counter] = result.get()
                del rebin_results[counter]
        num_rebin_results = len(rebin_results)
    
    if args.rebin_output_file_name is not None:
        json.dump(rebin_output_data,open(args.rebin_output_file_name,'w'))

analyzer_output_data = None
if args.do_analysis:
   
    logger.info('Analyzing...')
    
    # get and configure the model
    model = getattr(models,model_name)(config=model_config) 

    # get input data
    if rebin_output_data is None:
        if args.analysis_input_file_name is None:
            if input_data is None:
                sys.stderr.write('No input data available ("-a") or input file specified ("-i").\n Exiting.\n')
                sys.exit(1)
            else:
                # account for input that has not been rebinned
                logger.debug('Using input data directly in analyze step')
                analyzer_input_data = input_data
        else: 
            analyzer_input_data = json.load(open(args.analysis_input_file_name))
    else:
        analyzer_input_data = rebin_output_data

    analyzer_results = {}
    for counter, counter_data in analyzer_input_data.items():
        if len(counter_data) == 0:
            continue
        analyzer_results[counter] = pool.apply_async(analyzer,(counter_data,model)) 

    analyzer_output_data = {}
    num_analyzer_results = len(analyzer_results)
    while num_analyzer_results != 0:
        if datetime.datetime.now().second%10 == 0:
            logger.info(str(num_analyzer_results) + ' analyses remaining')
            time.sleep(1)
        logger.debug("{} results unfinished".format(num_analyzer_results))
        for counter,result in list(analyzer_results.items()):
            if result.ready():
                analyzer_output_data[counter] = result.get()
                del analyzer_results[counter]
        num_analyzer_results = len(analyzer_results)
    
    if args.analysis_output_file_name is not None:
        json.dump(analyzer_output_data,open(args.analysis_output_file_name,'w'))

if args.do_plot:

    logger.info('Plotting...')

    if analyzer_output_data is None:
        if args.plot_input_file_name is None:
            sys.stderr.write('No analyzed input data available or file specified. Exiting.\n')
            sys.exit(1)
        plotting_input_data = json.load(open(args.plot_input_file_name))
    else:
        plotting_input_data = analyzer_output_data

    # auto-generate this plotting param from re-bin params
    plot_config["x_unit"] = str(rebin_config["n_binning_unit"]) + " " + str(rebin_config["binning_unit"])
    plot_config["plot_dir"] = plot_config['plot_dir'].rstrip('/') + "/{}/".format(model_name)

    for counter, plotable_data in list(plotting_input_data.items()): 
        if len(plotable_data) == 0:
            continue
        # remove spaces in counter name
        counter_name = counter.replace(" ","-")[0:100]
        plot_config["plot_title"] = counter_name
        plot_config["plot_file_name"] = counter_name
        plotter(plotable_data,plot_config) 
    
logger.info('Done.')
