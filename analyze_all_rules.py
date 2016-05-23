#!/usr/bin/env python 

"""

This script operates on a set of time series. 
It is particularly well-suited for use with data collected from
Gnip streams using the Gnip-Stream-Collector-Metric packages
and its rule-counting module.

The script re-bins the data with 'rebin.py', using
"n_cpu" multiprocessing.Process objects.
The resulting data are then modeled with 'analyze.py'
and plotted with 'plot.py'.

Command-line argument control the input, output, and config file names,
as well as the switches for doing re-bin, analysis, and plotting.
The config file specifies the rule information and model configuration

NOTE: by default, neither the rebin, nor the analyzing, nor the plotting are performed. 

"""


import json
import time
import argparse
import ConfigParser
import importlib
import logging
import sys 
import os
import copy
import operator
import fnmatch
import multiprocessing as mp

from gnip_trend_detection.analysis import rebin
from gnip_trend_detection.analysis import analyze as analyzer
from gnip_trend_detection.analysis import plot as plotter
from gnip_trend_detection import models

# a few internal configuration setting

###
#lvl = logging.DEBUG
lvl = logging.INFO
n_cpu = 30
queue_size = 20000
###

# get input, output, and config file naems from cmd-line argument parsing
parser = argparse.ArgumentParser()
parser.add_argument("-c","--config-file",dest="config_file_name",default=None)   
parser.add_argument("-i","--input-file-names",dest="input_file_names",default=None,nargs="+")   
parser.add_argument("-d","--input-base-dir",dest="input_file_base_dir",default=None)   
parser.add_argument("-o","--rebinned-file-name",dest="rebinned_file_name",default="rebinned.pkl")    
parser.add_argument("-e","--analyzed-file-name",dest="analyzed_file_name",default="rebinned_analyzed.pkl")
parser.add_argument("-r","--do-rebin",dest="do_rebin",action="store_true",default=False,help="do rebin")   
parser.add_argument("-a","--do-analysis",dest="do_analysis",action="store_true",default=False,help="do analysis")   
parser.add_argument("-p","--do-plotting",dest="do_plot",action="store_true",default=False,help="do plotting")   
parser.add_argument("-v","--verbose",dest="verbose",action="store_true",default=False)   
parser.add_argument("-s","--serializer",dest="serializer",default="pickle",help="pickle,json,etc.")   
args = parser.parse_args()

# parse config file, which contains model and rule info
if args.config_file_name is not None and not os.path.exists(args.config_file_name) and not os.path.exists("config.cfg"): 
    logr.error("cmd-line argument 'config_file_name' must be a valid config file, or config.cfg must exist")
    sys.exit(1)
else:
    if args.config_file_name is None and os.path.exists("config.cfg"):
        args.config_file_name = "config.cfg"
    
    config = ConfigParser.ConfigParser()
    config.read(args.config_file_name)
    rebin_config = dict(config.items("rebin") )
    model_name = config.get("analyze","model_name")
    model_config = dict(config.items(model_name + "_model"))
    plot_config = dict(config.items("plot")) 
    if "logscale_eta" in plot_config:
        plot_config["logscale_eta"] = config.getboolean("plot","logscale_eta")
    else:
        plot_config["logscale_eta"] = False
    if "plot_eta" in plot_config:
        plot_config["plot_eta"] = config.getboolean("plot","plot_eta")
    else:
        plot_config["plot_eta"] = True

serializer = importlib.import_module(args.serializer)

if args.verbose:
    lvl = logging.DEBUG

logr = logging.getLogger("analyzer")
if logr.handlers == []:
    fmtr = logging.Formatter('%(asctime)s %(module)s:%(lineno)s - %(levelname)s - %(message)s') 
    hndlr = logging.StreamHandler()
    hndlr.setFormatter(fmtr)
    hndlr.setLevel(lvl)
    logr.addHandler(hndlr) 
    logr.setLevel(lvl)

logr.info("rebin/analysis/plotting starting") 

## set up some multiprocessing stuff

# results from the distributed processes are returned to this queue
queue = mp.Queue(queue_size)

if args.do_rebin:
    # get input file names
    if args.input_file_base_dir is not None:
        args.input_file_names = []
        for root, dirnames, filenames in os.walk(args.input_file_base_dir):
            for fname in fnmatch.filter(filenames,"*counts"):
                args.input_file_names.append(os.path.join(root,fname))

    if args.input_file_names is None:
        sys.stderr.write("Input file(s) must be specified. Exiting.\n")
        sys.exit(1)
    # loop over all rules in rules file and generate config objects, 
    # starting from config file and command-line arguments
    rule_config_list = []
    counter = 0
    for rule in json.load(open(rebin_config["rules_file_name"]))["rules"]:
        config = copy.copy(rebin_config)
        config["logger_name"] = "analyzer"
        config["return_queue"] = queue
        config["rule_name"] = rule["value"]
        config["rule_counter"] = counter 
        config["input_file_names"] = args.input_file_names
        rule_config_list.append(config)  
        counter += 1
    
    def chunks(l, n):
        """ Yield successive n-sized chunks from l.
        """
        for i in xrange(0, len(l), n):
            yield l[i:i+n]

    def manage_rule_list(rule_config_list,func):
        """ A function to be run by each Process object,
        running function "func" over a series of kwargs
        taken from rule configurations
        """
        for kwargs in rule_config_list:
            func(**kwargs)

    # figure out how many kwargs config objects to run in each Process object
    chunk_size = len(rule_config_list)/n_cpu
    if chunk_size == 0:
        chunk_size = 1
    logr.debug("chunk size is {}".format(chunk_size))

    # run it! 
    #
    # Each Process object runs the target function once, which takes
    # two arguments: the list of config objects and the function (rebin) to run
    process_list = []
    for chunk in chunks(rule_config_list,chunk_size):
        p = mp.Process(target=manage_rule_list,args=(chunk,rebin))
        p.start()
        process_list.append(p) 

    # container for output data
    data = {}

    # get results
    rule_counter = len(rule_config_list)
    while rule_counter != 0:
        if not queue.empty():
            data.update([queue.get()])
            rule_counter -= 1
        time.sleep(0.1) 

    logr.debug("Got all rebin results")

    # allow processes to gently die
    for p in process_list:
        p.join() 

    # save the data
    serializer.dump(data,open(args.rebinned_file_name,"w"))

if args.do_analysis:
   
    pool = mp.Pool()
    # get and configure the model
    model = getattr(models,model_name)(config=model_config) 

    # iterate over rule data and analyze point-by-point
    results_list = {}
    data = serializer.load(open(args.rebinned_file_name)) 
    for rule, rule_data in data.items():
        if len(rule_data) == 0:
            continue
        logr.info(u"submitting analysis for rule: {}".format(rule))
        results_list[rule] = pool.apply_async(analyzer,(rule_data,model)) 

    # get and save data
    saved_data = {}
    while len(results_list) != 0:
        time.sleep(0.1)
        for rule,result in results_list.items():
            if result.ready():
                saved_data.update([(rule,result.get())])  
                del results_list[rule]
                logr.info("{} results unfinished".format(len(results_list)))
                break

    serializer.dump(saved_data,open(args.analyzed_file_name,"w"))

if args.do_plot:

    logr.info('Plotting...')
    # auto-generate this plotting param from re-bin params
    plot_config["x_unit"] = str(rebin_config["n_binning_unit"]) + " " + str(rebin_config["binning_unit"])
    plot_config["plot_dir"] += "{}/".format(model_name)

    for rule, plotable_data in serializer.load(open(args.analyzed_file_name)).items():
        if len(plotable_data) == 0:
            continue
        logr.info(u"plotting results for rule: {}".format(rule))
        # remove spaces in rule name
        rule_name = rule.replace(" ","-")[0:100]
        plot_config["plot_title"] = rule_name
        plot_config["plot_file_name"] = rule_name
        plotter(plotable_data,plot_config) 
    
logr.info('Done.')
