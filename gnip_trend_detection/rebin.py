"""
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
import importlib
import logging
import fnmatch
import os
import traceback

import models
from time_bucket import TimeBucket

# keyword arguments start/stop time are written in this format
COMPACT_DATETIME_FORMAT = "%Y%m%d%H%M%S"

def rebin(**kwargs):
    """
    This function must be passed the following keyword arguments:
        rule_name 
        start_time
        stop_time
        input_file_names
        input_dt_format
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
                        
                        this_stop_time = datetime.datetime.strptime(line_split[0],kwargs["input_dt_format"])  
                        dt = datetime.timedelta(seconds=int(float(line_split[4])))
                        this_start_time = this_stop_time - dt
                        
                        if this_stop_time > stop_time:
                            continue
                        if this_start_time < start_time:
                            continue
                        time_bucket = TimeBucket(this_start_time, this_stop_time, kwargs["input_dt_format"])  
                        
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

        # add data to a dictionary with keys mapped to the grid indicies
        output_data = collections.defaultdict(float)
        for input_tb,input_count in input_data_sorted:
            logr.debug("input. TB: {}, count: {}".format(input_tb,input_count))
           
            for grid_tb in grid:
                if input_tb in grid_tb:
                    idx = grid.index(grid_tb) 
                    output_data[idx] += float(input_count)
                    break
                elif input_tb.intersects(grid_tb):
                    # assign partial count of input_tb to grid_tb
                    idx_lower = grid.index(grid_tb) 
                    frac_lower = input_tb.get_fraction_overlapped_by(grid_tb)  
                    output_data[idx_lower] += (float(input_count) * frac_lower)
                    
                    try:
                        idx = idx_lower + 1
                        frac = input_tb.get_fraction_overlapped_by(grid[idx])  
                        while frac > 0:
                            output_data[idx] += (frac * float(input_count))
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

        # use these to strip off leading and trailing zero-count entries
        prev_count = 0
        last_non_zero_ct_idx = -1

        # the grid is already time ordered, and the output_data are indexed
        for idx,dt in enumerate(grid):
            if idx in output_data:
                count = output_data[idx]
                last_non_zero_ct_idx = idx
            else:
                count = 0
            if count != 0 or prev_count != 0:
                sorted_output_data.append((dt,count))
            prev_count = count
        sorted_output_data = sorted_output_data[:last_non_zero_ct_idx+1]
        
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

