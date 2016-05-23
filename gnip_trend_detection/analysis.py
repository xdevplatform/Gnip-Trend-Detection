from math import log10, floor
import models
import datetime
import argparse
import collections
import operator
import importlib
import logging
import fnmatch
import os
import traceback

import matplotlib as mpl
mpl.use('Agg')
import matplotlib.dates as mdates
import matplotlib.pyplot as plt

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
        kwargs["rule_counter"] = 0

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

def analyze(generator, model, rule_name = None, return_queue = None, logr = None): 
    """
    This function loops over the items generated by the first argument.
    The expected format for each item is: [TimeBucket instance] [count]
    Each count is used to update the model, and the model result is added to the return list.
    """
    plotable_data = [] 
    for line in generator:
        time_bucket = line[0]
        count = line[1]
        
        model.update(count=count, time_bucket=time_bucket)
        result = float(model.get_result())
        
        if count > 0:
            trimmed_count = round(count, -int(floor(log10(count)))+3) 
        else:
            trimmed_count = 0
        if result > 0:
            trimmed_result = round(result, -int(floor(log10(result)))+3) 
        else:
            trimmed_result = 0
        
        plotable_data.append( (time_bucket, count, trimmed_result) )
        if logr is not None:
            logr.debug("{0} {1:>8} {2}".format(time_bucket, trimmed_count, trimmed_result))  
    if return_queue is not None:
        return_queue.put_nowait((rule_name,plotable_data))
    return plotable_data

def plot(plotable_data,config):            
    """
    plotable_data is a list of tuples with the following structure:
    (time_bucket, count, eta)
    """
    use_x_var = True
    if "use_x_var" in config:
        use_x_var = bool(config["use_x_var"])  
    if "y_label" not in config:
        config["y_label"] = "counts"
    if "start_time" in config and "stop_time" in config:
        start_tm = datetime.datetime.strptime(config["start_time"],"%Y%m%d%H%M")
        stop_tm = datetime.datetime.strptime(config["stop_time"],"%Y%m%d%H%M")
        data = [(tup[0].start_time,tup[1],tup[2]) for tup in plotable_data if tup[0].start_time > start_tm and tup[0].stop_time < stop_tm ]
    else:
        data = [(tup[0].start_time,tup[1],tup[2]) for tup in plotable_data] 
    
    if "rebin_factor" not in config or int(config["rebin_factor"]) == 1:
        tbs = [tup[0] for tup in data]
        cts = [tup[1] for tup in data]
        eta = [tup[2] for tup in data]
    # do a hacky rebin
    else:
        tbs = []
        cts = []
        eta = []
        tbs_tmp = None
        cts_tmp = 0
        eta_tmp = 0
        counter = 0
        for tbs_i,cts_i,eta_i in data:
            tbs_tmp = tbs_i
            cts_tmp += cts_i
            eta_tmp += eta_i
            counter += 1
            if counter == int(config["rebin_factor"]):
                counter = 0
                tbs.append(tbs_tmp)
                cts.append(cts_tmp)
                eta.append(eta_tmp/float(config["rebin_factor"]))
                tbs_tmp = None
                cts_tmp = 0
                eta_tmp = 0

    if cts == []:
        print("'cts' list is empty") 
        return -1
    max_cts = max(cts)
    min_cts = min(cts)
   
    # build the plot
    fig = plt.figure()
    plt.title(config["plot_title"])
    
    ax1 = fig.add_subplot(111)
    if use_x_var:
        ax1.plot(tbs,cts,'k-') 
    else:
        ax1.plot(cts,'bo',cts,'k-') 
        ax1.set_xlim(0,len(cts))
    
    ## fancify
    ax1.set_ylabel(config["y_label"],color='k',fontsize=10)
    ax1.set_ylim(min_cts*0.9,max_cts*1.7)
    for tl in ax1.get_yticklabels():
        if use_x_var:
            tl.set_color('k')
        else:
            tl.set_color('b')
        tl.set_fontsize(10)
    plt.locator_params(axis = 'y', nbins = 4)
    if use_x_var:
        formatter = mdates.DateFormatter('%Y-%m-%d')
        ax1.xaxis.set_major_formatter( formatter ) 
        fig.autofmt_xdate()
    ax1.set_xlabel("time ({} bins)".format(config["x_unit"].rstrip('s')))

    if config['plot_eta']:
        ax2 = ax1.twinx()
        plotter="plot"
        if config["logscale_eta"]:
            plotter="semilogy"
        if use_x_var:
            getattr(ax2,plotter)(tbs,eta,'r')
        else:
            getattr(ax2,plotter)(eta,'r')
            ax2.set_xlim(0,len(eta))
        min_eta = 0
        if min(eta) > 0:
            min_eta = min(eta) * 0.9
        ax2.set_ylim(min_eta, max(eta)*1.1)
        ax2.set_ylabel("eta",color='r',fontsize=10)
        for tl in ax2.get_yticklabels():
            tl.set_color('r')
            tl.set_fontsize(10)

    if not config["plot_eta"]:
        config["plot_file_name"] += "_no_eta"
    try:
        os.makedirs(config["plot_dir"]) 
    except OSError:
        pass
    plot_file_name = config["plot_dir"] + "/{}.{}".format(config["plot_file_name"],config["plot_file_extension"])
    plt.savefig(plot_file_name) 
    plt.close()


