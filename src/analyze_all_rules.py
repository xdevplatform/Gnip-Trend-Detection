import json
import time
import argparse
import pickle
import logging
import sys 
import copy
from multiprocessing import Process,Queue,Pool

from rebin import rebin

parser = argparse.ArgumentParser()
parser.add_argument("-r",dest="rules_file_name",default="rules.json")   
parser.add_argument("-a",dest="start_time",default=None,help="YYYYMMDDhhmmss")
parser.add_argument("-o",dest="stop_time",default=None,help="YYYYMMDDhhmmss")
parser.add_argument('-b',dest='binning_unit',action='store',default='seconds',help="days,hours,minutes") 
parser.add_argument('-n',dest='n_binning_unit',action='store',default=60,type=int,help='number of binning units per bin') 
parser.add_argument("-i",dest="input_file_names",default=None, nargs="*")   
parser.add_argument("-f",dest="output_file_name",default="output.pkl")   
parser.add_argument("-v",dest="verbose",default=False)   
args = parser.parse_args() 

lvl = logging.INFO

logr = logging.getLogger("analyzer")
fmtr = logging.Formatter('%(asctime)s %(name)s - %(levelname)s - %(message)s') 
hndlr = logging.StreamHandler()
hndlr.setFormatter(fmtr)
hndlr.setLevel(lvl)
logr.addHandler(hndlr) 
logr.setLevel(lvl)
logr.info("Analyzer starting")

queue = Queue(20000)
n_cpu = 8

# get all rules and generate kwargs objects
kwargs = vars(args)
kwargs["logger_name"] = "analyzer"
kwargs["return_queue"] = queue

rule_list = []
for rule in json.load(open(args.rules_file_name))["rules"]:
    d = copy.copy(kwargs)
    d["rule_name"] = rule["value"]
    rule_list.append(d) 

def chunks(l, n):
    """ Yield successive n-sized chunks from l.
    """
    for i in xrange(0, len(l), n):
        yield l[i:i+n]

def manage_rule_list(rule_list,func):
    for kwargs in rule_list:
        func(**kwargs)

chunk_size = len(rule_list)/n_cpu
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

pickle.dump(data,open(args.output_file_name,"w"))
