"""

This script operates on a set of time series. 
It is particularly suited for use with data collected from
Gnip streams using the Gnip-Stream-Collector-Metric packages
and its rule counting module.

The script re-bins the data (in parallel), using 'rebin.py'.
The resulting data are then modeled with 'analyze.py'
and plotted with 'plot.py'.

NOTE: by default, neither the rebin, nor the analyzing, nor the plotting are performed. 

"""


import json
import time
import argparse
import pickle
import logging
import sys 
import copy
import operator
from multiprocessing import Process,Queue,Pool

from rebin import rebin
from analyze import analyze as analyzer
from plot import plot as plotter

# a few internal configuration setting

###
lvl = logging.INFO
n_cpu = 10
queue_size = 20000
###

parser = argparse.ArgumentParser()
parser.add_argument("-r",dest="rules_file_name",default="rules.json")   
parser.add_argument("-a",dest="start_time",default=None,help="YYYYMMDDhhmmss")
parser.add_argument("-o",dest="stop_time",default=None,help="YYYYMMDDhhmmss")
parser.add_argument('-b',dest='binning_unit',action='store',default='seconds',help="days,hours,minutes") 
parser.add_argument('-n',dest='n_binning_unit',action='store',default=60,type=int,help='number of binning units per bin') 
parser.add_argument("-i",dest="input_file_names",default=None, nargs="*")   
parser.add_argument("-f",dest="output_file_name",default="all_outputs.pkl")   
parser.add_argument("-d",dest="do_rebin",action="store_true",default=False,help="do rebin")   
parser.add_argument("-s",dest="do_analysis",action="store_true",default=False,help="do analysis")   
parser.add_argument("-p",dest="do_plot",action="store_true",default=False,help="do plotting")   
args = parser.parse_args() 


logr = logging.getLogger("analyzer")
fmtr = logging.Formatter('%(asctime)s %(name)s - %(levelname)s - %(message)s') 
hndlr = logging.StreamHandler()
hndlr.setFormatter(fmtr)
hndlr.setLevel(lvl)
logr.addHandler(hndlr) 
logr.setLevel(lvl)
logr.info("Analyzer starting")

if args.do_plot and not args.do_analysis:
    logr.error("Can't plot without analysis first. Exiting.")
    sys.exit()



if args.do_rebin:
    queue = Queue(queue_size)

    # get all rules and generate kwargs objects
    kwargs = vars(args)
    kwargs["logger_name"] = "analyzer"
    kwargs["return_queue"] = queue

    rule_list = []
    counter = 0
    for rule in json.load(open(args.rules_file_name))["rules"]:
        d = copy.copy(kwargs)
        d["rule_name"] = rule["value"]
        d["rule_counter"] = counter
        rule_list.append(d)  

        counter += 1

    def chunks(l, n):
        """ Yield successive n-sized chunks from l.
        """
        for i in xrange(0, len(l), n):
            yield l[i:i+n]

    def manage_rule_list(rule_list,func):
        for kwargs in rule_list:
            func(**kwargs)

    # run it!
    chunk_size = len(rule_list)/n_cpu
    if chunk_size == 0:
        chunk_size = 1
    process_list = []
    for chunk in chunks(rule_list,chunk_size):
        p = Process(target=manage_rule_list,args=(chunk,rebin))
        p.start()
        process_list.append(p) 

    data = {}

    # get results
    rule_counter = len(rule_list)
    while rule_counter != 0:
        if not queue.empty():
            data.update([queue.get()])
            rule_counter -= 1
        time.sleep(0.1) 

    logr.info("Got all results")

    # allow processes to gently die
    for p in process_list:
        p.join()

    pickle.dump(data,open(args.output_file_name,"w"))

if args.do_analysis:
    import models

    model = models.Poisson(alpha=0.95,mode="a")
    period_list = ["hour"]

    data_list = [] 
    data = pickle.load(open(args.output_file_name))
    for rule, rule_data in data.items():
        logr.info(u"analyzing rule: {}".format(rule))
        plotable_data = analyzer(rule_data,model,period_list) 
        
        rule_name = rule.replace(" ","-")[0:100]

        if args.do_plot:
            plotter(plotable_data,rule_name)

        # save data
        data_list.append((rule_name,plotable_data))
    
    def max_eta_getter(tup): 
        plotable_data = tup[1] 
        return max(plotable_data, key=operator.itemgetter(3))

    sorted_data_list = sorted(data_list, key = max_eta_getter)  
    for rule_name, plotable_data in sorted_data_list[0:3]: 
        logr.info("{}: {}".format(rule_name,max_eta_getter((rule_name,plotable_data))))

