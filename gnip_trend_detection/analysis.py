import datetime
import argparse
import collections
import operator
import importlib
import logging
import os
import sys
import datetime_truncate 
from math import log10, floor
from dateutil.parser import parse as dt_parser

import matplotlib as mpl
mpl.use('Agg')
import matplotlib.dates as mdates
import matplotlib.ticker as plticker
import matplotlib.pyplot as plt

from .time_bucket import TimeBucket

def rebin(input_generator,
        start_time = str(datetime.datetime(1970,1,1)),
        stop_time = str(datetime.datetime(2020,1,1)),
        binning_unit = 'hours',
        n_binning_unit = 1,
        **kwargs
        ):
    """
    This function must be passed the following positional argument:
        input_generator
    Optional keyword arguments are:
        binning_unit
        n_binning_unit
        stop_time
        start_time

    The 'input_generator' object must yield tuples like:
        [interval start time], [interval duration in sec], [interval count]

    The function return a list of tuples like:
        [new interval start time], [new interval duration in sec], [new interval count]
    """
    
    logger = logging.getLogger("rebin")
    
    start_time = dt_parser(start_time)  
    stop_time = dt_parser(stop_time)  

    # these are just for keeping track of what range of date/times we observe in the data
    max_stop_time = datetime.datetime(1970,1,1)
    min_start_time = datetime.datetime(2020,1,1)

    input_data = []

    # put the data into a list of (TimeBucket, count) tuples
    for line in input_generator:
        
        try:
            this_start_time = dt_parser(line[0])
        except ValueError:
            continue
        dt = datetime.timedelta(seconds=int(float(line[1])))
        this_stop_time = this_start_time + dt
       
        if this_stop_time > stop_time:
            continue
        if this_start_time < start_time:
            continue
        time_bucket = TimeBucket(this_start_time, this_stop_time)  
        
        count = line[2]
        input_data.append((time_bucket, count)) 
        
        if this_stop_time > max_stop_time:
            max_stop_time = this_stop_time
        if this_start_time < min_start_time:
            min_start_time = this_start_time

    input_data_sorted = sorted(input_data)

    # make a grid with appropriate bin size
    grid_start_time = datetime_truncate.truncate(min_start_time,binning_unit.rstrip('s'))
    grid_stop_time = datetime_truncate.truncate(max_stop_time,binning_unit.rstrip('s'))
    grid_dt = datetime.timedelta(**{binning_unit:int(n_binning_unit)})

    tb_stop_time = grid_start_time + grid_dt
    tb = TimeBucket(grid_start_time,tb_stop_time)

    # make list of TimeBuckets for bins
    grid = []
    while tb.stop_time <= grid_stop_time:
        #logger.debug("{}".format(tb))
        grid.append(tb)
        tb_start_time = tb.stop_time
        tb_stop_time = tb_start_time + grid_dt
        tb = TimeBucket(tb_start_time,tb_stop_time) 
    grid.append(tb)


    # add data to a dictionary with keys mapped to the grid indicies
    output_data = collections.defaultdict(float)
    for input_tb,input_count in input_data_sorted:
        logger.debug("input. TB: {}, count: {}".format(input_tb,input_count))
       
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

            if count > 0:
                trimmed_count = int(count)
                #trimmed_count = round(count, -int(floor(log10(count)))+1) 
            else:
                trimmed_count = 0
            sorted_output_data.append((str(dt.start_time),dt.size().total_seconds(),trimmed_count)) 
        
        prev_count = count
    sorted_output_data = sorted_output_data[:last_non_zero_ct_idx+1]
    
    # return the data structure
    return sorted_output_data
    
def analyze(generator, model): 
    """
    This function acts on CSV data for a single counter.
    It loops over the items generated by the first argument.
    Each item is expected to be a tuple of: 
        [interval_start_time] [interval_duration_in_sec] [interval_count] 
    Each count is used to update the model, and the model result is added to the return list. 
    """
    
    logger = logging.getLogger("analyze") 
    if logger.handlers == []:
        fmtr = logging.Formatter('%(asctime)s %(name)s:%(lineno)s - %(levelname)s - %(message)s') 
        hndlr = logging.StreamHandler()
        hndlr.setFormatter(fmtr)
        logger.addHandler(hndlr) 

    output_data = [] 
    for line in generator:
        try:
            time_interval_start = dt_parser(line[0]) 
        except ValueError:
            print(line[0])
            sys.exit()
        time_interval_duration = line[1]
        count = float(line[2])
        
        model.update(count=count, interval_start_time=time_interval_start) 
        result = float(model.get_result())
        
        # trim digits in outputs
        if count > 0:
            trimmed_count = round(count, -int(floor(log10(count)))+1) 
        else:
            trimmed_count = 0
        if result > 0:
            trimmed_result = round(result, -int(floor(log10(result)))+1) 
        else:
            trimmed_result = 0
        
        output_data.append( (str(time_interval_start), count, trimmed_result) )
        logger.debug("{0} {1:>8} {2}".format(time_interval_start, trimmed_count, trimmed_result))  
    
    return output_data

def plot(input_generator,config):            
    """
    input_generator is a generator of tuples with the following structure:
        (time_interval_start, count, eta)
    """
    
    logger = logging.getLogger("plot") 
    if logger.handlers == []:
        fmtr = logging.Formatter('%(asctime)s %(name)s:%(lineno)s - %(levelname)s - %(message)s') 
        hndlr = logging.StreamHandler()
        hndlr.setFormatter(fmtr)
        logger.addHandler(hndlr) 
    
    # if this throws a configparser.NoSectionError, 
    # then let it rise uncaught, since nothing will work
    plot_config = config['plot'] 
  
    # get parameters and set defaults
    logscale_eta = plot_config.getboolean('logscale_eta',fallback=False)
    use_x_var = plot_config.getboolean('use_x_var',fallback=True)
    do_plot_parameters = plot_config.getboolean('do_plot_parameters',fallback=False)
    start_tm = dt_parser( plot_config.get("start_time","1900-01-01") )
    stop_tm = dt_parser( plot_config.get("stop_time","2050-01-01") )
    rebin_factor = plot_config.getint("rebin_factor",fallback=1)

    rebin_config = dict(config.items("rebin"))
    plot_config["x_unit"] = "{0:d} {1:s}" .format( int(rebin_config["n_binning_unit"]) * rebin_factor, rebin_config["binning_unit"])

    """
    # only useful if we revive 'counter_name' parameter
    if 'counter_name' in rebin_config:
        if plot_config["plot_title"] == "":
            plot_config["plot_title"] = rebin_config["counter_name"]
        if plot_config["plot_file_name"] == "":
            plot_config["plot_file_name"] = rebin_config["counter_name"]
    """

    # TODO: should just put this in a dataframe
    data = [(dt_parser(tup[0]),float(tup[1]),float(tup[2])) for tup in input_generator if dt_parser(tup[0]) > start_tm and dt_parser(tup[0]) < stop_tm ]
    
    if rebin_factor <= 1:
        tbs = [tup[0] for tup in data]
        cts = [tup[1] for tup in data]
        eta = [tup[2] for tup in data]
    # do a hacky rebin, just for plotting 
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
            if counter == rebin_factor:
                counter = 0
                tbs.append(tbs_tmp)
                cts.append(cts_tmp)
                eta.append(eta_tmp/float(rebin_factor))
                tbs_tmp = None
                cts_tmp = 0
                eta_tmp = 0

    if cts == []:
        sys.stderr.write("'cts' list is empty\n") 
        return -1
    max_cts = max(cts)
    min_cts = min(cts)
   
    # build the plotting surface
    fig,(ax1,ax2) = plt.subplots(2,sharex=True) 
   
    # plot the data
    if use_x_var:
        ax1.plot(tbs,cts,'k-') 
    else:
        ax1.plot(cts,'k-') 
        ax1.set_xlim(0,len(cts))
   
    plotter="plot"
    if logscale_eta:
        plotter="semilogy"
    if use_x_var:
        getattr(ax2,plotter)(tbs,eta,'r')
    else:
        getattr(ax2,plotter)(eta,'r')
        ax2.set_xlim(0,len(eta))

    # adjust spacing
    ax1.set_ylim(min_cts*0.9,max_cts*1.7)
    min_eta = 0
    if min(eta) > 0:
        min_eta = min(eta) * 0.9
    ax2.set_ylim(min_eta, max(eta)*1.1)

    # remove the horizintal space between plots
    plt.subplots_adjust(hspace=0)
    # modify ticklabels
    for tl in ax1.get_yticklabels():
        tl.set_color('k')
        tl.set_fontsize(10)
    for tl in ax2.get_yticklabels():
        tl.set_color('r')
        tl.set_fontsize(10)
   
    # y labels
    y_label = plot_config.get('y_label','counts')
    ax1.set_ylabel(y_label,color='k',fontsize=12)
    ax2.set_ylabel("eta",color='r',fontsize=12)

    ax1.yaxis.set_major_locator(plticker.MaxNLocator(4))
    ax2.yaxis.set_major_locator(plticker.MaxNLocator(5))

    # x date formatting
    if use_x_var:
        day_locator = mdates.DayLocator()
        hour_locator = mdates.HourLocator()
        day_formatter = mdates.DateFormatter('%Y-%m-%d')
        ax2.xaxis.set_major_formatter( day_formatter ) 
        ax2.xaxis.set_major_locator( day_locator ) 
        ax2.xaxis.set_minor_locator( hour_locator ) 
        fig.autofmt_xdate()
    ax2.set_xlabel("time ({} bins)".format(plot_config["x_unit"].rstrip('s')))

    ax1.grid(True)
    ax2.grid(True)
 
    # build text box for parameter display
    if do_plot_parameters:
        props = dict(boxstyle='round',facecolor='white', alpha=0.5)
        model_name = config['analyze']['model_name']
        model_pars = ""
        for k,v in config[model_name + '_model'].items():
            model_pars += "{}: {}\n".format(k,v) 
        text_str = "model: {}\n{}".format(model_name,str(model_pars))
        ax1.text(0.05,0.95,
                text_str,
                bbox=props,
                verticalalignment='top',
                fontsize=8,
                transform=ax1.transAxes
                )
    
    plt.suptitle(u"{}".format( plot_config.get("plot_title","SET A PLOT TITLE")))
    
    # write the image 
    try:
        os.makedirs(plot_config.get("plot_dir",".")) 
    except OSError:
        pass

    plot_file_name = u"{}/{}.{}".format(
            plot_config.get("plot_dir",".").rstrip('/'), 
            plot_config.get("plot_file_name","plot"),
            plot_config.get("plot_file_extension","png")
            )
    plt.savefig(plot_file_name) 
    plt.close()


