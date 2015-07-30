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
import pickle
import logging
import sys 
import os
import copy
import operator
import fnmatch
from multiprocessing import Process,Queue,Pool

from rebin import rebin
from analyze import analyze as analyzer
from plot import plot as plotter

# a few internal configuration setting

###
#lvl = logging.DEBUG
lvl = logging.INFO
n_cpu = 8
queue_size = 20000
###

# get input, output, and config file naems from cmd-line argument parsing
parser = argparse.ArgumentParser()
parser.add_argument("-c",dest="config_file_name",default=None)   
parser.add_argument("-i",dest="input_file_names",default=None)   
parser.add_argument("-d",dest="input_file_base_dir",default=None)   
parser.add_argument("-o",dest="output_file_name",default="output.pkl")    
parser.add_argument("-r",dest="do_rebin",action="store_true",default=False,help="do rebin")   
parser.add_argument("-a",dest="do_analysis",action="store_true",default=False,help="do analysis")   
parser.add_argument("-p",dest="do_plot",action="store_true",default=False,help="do plotting")   
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

logr = logging.getLogger("analyzer")
if logr.handlers == []:
    fmtr = logging.Formatter('%(asctime)s %(name)s:%(lineno)s - %(levelname)s - %(message)s') 
    hndlr = logging.StreamHandler()
    hndlr.setFormatter(fmtr)
    hndlr.setLevel(lvl)
    logr.addHandler(hndlr) 
    logr.setLevel(lvl)
logr.info("Analysis starting")

if args.do_plot and not args.do_analysis:
    logr.error("Can't plot without analysis first. Exiting.")
    sys.exit(1)

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
    
    # results from the distributed processes are returned to this queue
    queue = Queue(queue_size)

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
        p = Process(target=manage_rule_list,args=(chunk,rebin))
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

    logr.info("Got all results")

    # allow processes to gently die
    for p in process_list:
        p.join() 

    # save the data
    pickle.dump(data,open(args.output_file_name,"w"))

if args.do_analysis:
   
    # get and configure the model
    import models
    model = getattr(models,model_name)(config=model_config) 

    # auto-generate this plotting param from re-bin params
    plot_config["x_unit"] = str(rebin_config["n_binning_unit"]) + " " + str(rebin_config["binning_unit"])

    # iterate over rule data and analyze point-by-point
    saved_data_list = [] 
    data = pickle.load(open(args.output_file_name))
    for rule, rule_data in data.items():
        logr.info(u"analyzing rule: {}".format(rule))
        plotable_data = analyzer(rule_data,model,logr) 
        # remove spaces in rule name
        rule_name = rule.replace(" ","-")[0:100]
        plot_config["plot_title"] = rule_name
        if args.do_plot:
            return_val = plotter(plotable_data,plot_config) 
            # the plotter returns -1 if the counts data don't exist
            if return_val == -1:
                continue

        # save data
        if plotable_data != []:
            saved_data_list.append((rule_name,plotable_data))
  
    def max_last_field_getter(tup): 
        """ a function that acts on tuples like: 
        ( [rule], [ (1_field_1, 1_field_2, 1_field_3 ... 1_field_n),(2_field_1,2_field_2,2_field_3...2_field_n)...] )
        and returns the largest m_field_n value, where n is the (fixed) size of the tuple in the list, 
        and m is the length of the list
        """
        plotable_data = tup[1] 
        m = max(plotable_data, key=operator.itemgetter(-1)) 
        logr.debug("{} - max eta: {}".format(tup[0],m[-1]))
        return m[-1]

    def area_under_eta_curve(tup):
        """ a function that acts on tuples like:
        ( [rule], [ (tb_1,count_1,eta_1),(tb_2,count_2,eta_2)... ] )
        and calculated the area under the eta curve for a window of size "half_window_size"
        """
        rule = tup[0]
        data = tup[1]
        
        index = 0 
        half_window_size = 3

        auc_list = []
        for tb,ct,eta in data:
            if index < half_window_size:
                auc_list.append((tb,ct,eta,0))
                index += 1
                continue
            auc = 0
            for tb,ct,eta in data[index-half_window_size:index+half_window_size+1]:
                auc += eta
            auc_list.append((tb,ct,eta,auc))
            index += 1
        return (rule,auc_list)        

    # sort the saved data list by maximum eta value
    sorted_data_list = list(reversed(sorted(saved_data_list, key=max_last_field_getter)))
    
    # print top 3 rules by max eta value
    for rule_name, data in sorted_data_list[0:3]: 
        max_pt = max(data,key=operator.itemgetter(2))
        print("Rule: {0} - maximum eta: {1:.1f} at count: {2} / timestamp: {3}".format(rule_name, max_pt[2], max_pt[1], max_pt[0]))

    # append area-under-curve to data
    auc_data_list = [ area_under_eta_curve(tup) for tup in saved_data_list]

    # sort the saved data list by maximum area-under-eta-curve value
    sorted_data_list = list(reversed(sorted(auc_data_list, key=max_last_field_getter)))
    
    # print top 3 rules by max area-under-eta-curve value
    for rule_name, data in sorted_data_list[0:3]: 
        max_pt = max(data,key=operator.itemgetter(3))
        print("Rule: {0} - maximum area-under-eta-curve: {1:.1f} at count: {2} / timestamp: {3}".format(rule_name, max_pt[3], max_pt[1], max_pt[0]))

    
