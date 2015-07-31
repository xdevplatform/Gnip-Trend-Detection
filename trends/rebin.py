#!/usr/bin/env python

"""
The script reads in data in the format: 
 [time_stamp],[rule],[rule_count],[total_count],[interval_duration_in_sec] 
Data are read from a file. 

Inputs are:
    input file name(s)
    rule name
    start time
    stop time
    bin size and unit
    output file name

Output is a .pkl of the list of (TimeBucket,count) pairs.

Rebinning logic looks like:
    try to assign an input interval to a single output bin
    when the input interval is smaller than the output bin AND is split over two bins:
        assume constant rate over the input interval and split counts between bins proportionally
    when the input interval is larger than an output bin:
        distribute count over output bins proportionally

"""

import sys
import datetime
import argparse
import collections
import operator
import pickle
import logging
import fnmatch
import os
import traceback

import models
from time_bucket import TimeBucket

# timestamps read from files are expected to match an element of this list
dt_format_list = ["%Y-%m-%d %H:%M:%S.%f"
        ,"%Y-%m-%dT%H:%M"
        ,"%Y%m%d%H%M%S"
        ,"%Y%m%d%H%M"
        ]
# as a last resort, this format will be tried
INPUT_DATETIME_FORMAT = "%Y-%m-%d %H:%M:%S.%f"

# keyword arguments start/stop time are expected in this format
COMPACT_DATETIME_FORMAT = "%Y%m%d%H%M%S"

def rebin(**kwargs):
    """
    This function must be passed the following keyword arguments:
        rule_name 
        start_time
        stop_time
        input_file_names
        binning_unit
        n_binning_unit
    Optional keyword arguments are:
        return_queue
        logger_name
    """
    if "logger_name" in kwargs:
        logr = logging.getLogger(kwargs["logger_name"]) 
    else:
        lvl = logging.INFO
        logr = logging.getLogger("rebin")
    
        if logr.handlers == []:
            fmtr = logging.Formatter('%(asctime)s %(name)s:%(lineno)s - %(levelname)s - %(message)s') 
            hndlr = logging.StreamHandler()
            hndlr.setFormatter(fmtr)
            hndlr.setLevel(lvl)
            logr.addHandler(hndlr) 
        logr.setLevel(lvl)

    if "rule_counter" not in kwargs:
        kwargs["rule_counter"] = 1

    try:
        logr.info(u"rebin.py is processing rule {}: {}".format(kwargs["rule_counter"],kwargs["rule_name"])) 

        start_time = datetime.datetime.strptime(kwargs["start_time"],COMPACT_DATETIME_FORMAT)
        stop_time = datetime.datetime.strptime(kwargs["stop_time"],COMPACT_DATETIME_FORMAT) 

        input_data = []

        # put the data into a list of (TimeBucket, count) tuples
        for input_file_name in kwargs["input_file_names"]:
            with open(input_file_name) as f:
                for line in f:
                    line_split = line.split(",")
                    if line_split[1].strip().rstrip() != kwargs["rule_name"].strip().rstrip(): 
                        continue
                    else:
                        logr.debug("{}".format(line))
                        
                        # manage datetime formats
                        this_stop_time = None
                        for dt_format in dt_format_list:
                            try:
                                this_stop_time = datetime.datetime.strptime(line_split[0],dt_format)  
                                dt = datetime.timedelta(seconds=int(float(line_split[4])))
                                this_start_time = this_stop_time - dt
                                time_bucket = TimeBucket(this_start_time, this_stop_time, dt_format)  
                                break
                            except ValueError:
                                continue
                        if this_stop_time is None:
                            this_stop_time = datetime.datetime.strptime(line_split[0],INPUT_DATETIME_FORMAT)
                        
                        if this_stop_time > stop_time:
                            continue
                        if this_start_time < start_time:
                            continue
                        
                        '''
                        # sanity check: input time buckets must always be smaller than output time bucket
                        if time_bucket.size() > datetime.timedelta(**{kwargs["binning_unit"]:int(kwargs["n_binning_unit"])}):
                            sys.stderr.write("Input time bucket {} is larger that {}{}\n".format(time_bucket,str(kwargs["n_binning_unit"]),kwargs["binning_unit"]))
                            sys.exit(-1) 
                        '''
                        count = line_split[2]
                        input_data.append((time_bucket, count)) 

        logr.debug("Completed reading from files for {}".format(kwargs["rule_name"]))
        input_data_sorted = sorted(input_data)

        # make a grid with appropriate bin size
        grid_dt = datetime.timedelta(**{kwargs["binning_unit"]:int(kwargs["n_binning_unit"])})
        tb_stop_time = start_time + grid_dt
        tb = TimeBucket(start_time,tb_stop_time)

        # make list of TimeBuckets for bins
        grid = []
        while tb.stop_time <= stop_time:
            logr.debug("{}".format(tb))
            grid.append(tb)
            tb_start_time = tb.stop_time
            tb_stop_time = tb_start_time + grid_dt
            tb = TimeBucket(tb_start_time,tb_stop_time) 
        grid.append(tb)

        logr.debug("Finished generating grid for {}".format(kwargs["rule_name"]))

        # add data to a dictionary with indicies mapped to the grid indicies
        output_data = collections.defaultdict(int)
        for input_tb,input_count in input_data_sorted:
            logr.debug("input. TB: {}, count: {}".format(input_tb,input_count))
           
            for grid_tb in grid:
                if input_tb in grid_tb:
                    idx = grid.index(grid_tb) 
                    output_data[idx] += int(input_count)
                    break
                elif input_tb.intersects(grid_tb):
                    # assign partial count of input_tb to grid_tb
                    idx_lower = grid.index(grid_tb) 
                    frac_lower = input_tb.get_fraction_overlapped_by(grid_tb)  
                    output_data[idx_lower] += int(int(input_count) * frac_lower)
                    
                    try:
                        idx = idx_lower + 1
                        frac = input_tb.get_fraction_overlapped_by(grid[idx])  
                        while frac > 0:
                            output_data[idx] += int(frac * int(input_count))
                            idx += 1
                            frac = input_tb.get_fraction_overlapped_by(grid[idx])   
                    except IndexError:
                        pass
                    
                    break
                else:
                    pass

        logr.debug("Completed rebin distribution for {}".format(kwargs["rule_name"])) 
        
        # put data back into a sorted list of tuples
        sorted_output_data = []
        for idx,count in sorted(output_data.items(), key=operator.itemgetter(0)):  
            dt = grid[idx]
            sorted_output_data.append((dt,count))
            logr.debug("{} {}".format(dt,count))

        # a mystery
        try:
            sorted_output_data.pop(0)     
        except IndexError:
            pass

        # for use with multiprocessing
        if "return_queue" in kwargs:
            logr.debug("adding {} key to dict with value {}".format(kwargs["rule_name"],sorted_output_data)) 
            kwargs["return_queue"].put_nowait((kwargs["rule_name"], sorted_output_data))
            logr.debug("added to return queue for {}".format(kwargs["rule_name"]))
        else:
        # return the data structure
            return sorted_output_data
    
    except ValueError, e:
        logr.error(traceback.print_exc())

    except Exception, e:
        logr.error(traceback.print_exc())

if __name__ == "__main__":
   
    # set up a logger
    logr = logging.getLogger("rebin")
    logr.setLevel(logging.DEBUG)
    if logr.handlers == []:
        fmtr = logging.Formatter('%(asctime)s %(name)s:%(lineno)s - %(levelname)s - %(message)s') 
        hndlr = logging.StreamHandler()
        hndlr.setFormatter(fmtr)
        logr.addHandler(hndlr) 

    parser = argparse.ArgumentParser()
    parser.add_argument("-c",dest="config_file_name",default=None)   
    parser.add_argument("-i",dest="input_file_names",nargs="+",default=[])    
    parser.add_argument("-d",dest="input_file_base_dir",default=None)   
    parser.add_argument("-p",dest="input_file_postfix",default="counts")    
    parser.add_argument("-o",dest="output_file_name",default="output.pkl")    
    parser.add_argument("-v",dest="verbose",action="store_true",default=False)    
    args = parser.parse_args()

    # parse config file
    if args.config_file_name is not None and not os.path.exists(args.config_file_name) and not os.path.exists("config.cfg"): 
        logr.error("cmd-line argument 'config_file_name' must be a valid config file, or config.cfg must exist")
        sys.exit(1)
    else:
        if args.config_file_name is None and os.path.exists("config.cfg"):
            args.config_file_name = "config.cfg"

        import ConfigParser as cp 
        config = cp.ConfigParser()
        config.read(args.config_file_name)
        rebin_config = config.items("rebin") 
        kwargs = dict(rebin_config)

    if args.input_file_base_dir is not None:
        args.input_file_names = []
        for root, dirnames, filenames in os.walk(args.input_file_base_dir):
            for fname in fnmatch.filter(filenames,"*"+args.input_file_postfix):
                args.input_file_names.append(os.path.join(root,fname))

    if args.input_file_names is []:
        sys.stderr.write("Input file(s) must be specified. Exiting.")
        sys.exit(1)
  
    if args.verbose:
        data = rebin(input_file_names=args.input_file_names,logger_name="rebin",**kwargs)
    else:
        data = rebin(input_file_names=args.input_file_names,**kwargs)
    pickle.dump({kwargs["rule_name"]:data},open(args.output_file_name,"w"))
