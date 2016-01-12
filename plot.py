#!/usr/bin/env python

import datetime
import os
import matplotlib as mpl
mpl.use('Agg')
import matplotlib.dates as mdates
import matplotlib.pyplot as plt

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


if __name__ == "__main__":
    
    import argparse
    import ConfigParser
    import importlib
    import logging
    
    import models
    from analyze import analyze as analyzer

    logr = logging.getLogger("analyzer")
    #logr.setLevel(logging.DEBUG)
    if logr.handlers == []:
        fmtr = logging.Formatter('%(asctime)s %(name)s - %(levelname)s - %(message)s') 
        hndlr = logging.StreamHandler()
        hndlr.setFormatter(fmtr)
        logr.addHandler(hndlr) 

    parser = argparse.ArgumentParser()
    parser.add_argument("-i","--input-file",dest="input_file_name",default="output.pkl") 
    parser.add_argument("-c","--config-file",dest="config_file_name",default="config.cfg",help="get configuration from this file")
    parser.add_argument("-t","--plot-title",dest="plot_title",default=None) 
    parser.add_argument("-d","--analyzed-data-file",dest="analyzed_data_file",default=None) 
    parser.add_argument("-v","--verbose",dest="verbose",action="store_true",default=False) 
    parser.add_argument("-s","--serializer",dest="serializer",default="pickle") 
    args = parser.parse_args()

    plot_config = {}
    
    config = ConfigParser.ConfigParser()
    config.read(args.config_file_name)
    model_name = config.get("analyze","model_name")
    model_config = dict(config.items(model_name + "_model")) 
    if config.has_section("plot"):
        plot_config = dict(config.items("plot"))
    else:
        plot_config["plot_title"] = "output"
        plot_config["plot_dir"] = "."
    rebin_items = config.items("rebin")
    rebin_config = dict(rebin_items)
    rule_name = rebin_config["rule_name"]
    if plot_config["plot_title"] == "":
        plot_config["plot_title"] = rule_name
    if plot_config["plot_file_name"] == "":
        plot_config["plot_file_name"] = rule_name

    plot_config["x_unit"] = str(rebin_config["n_binning_unit"]) + " " + str(rebin_config["binning_unit"])
    
    ## manage plot configuration that involves bools
    if "logscale_eta" in plot_config:
        plot_config["logscale_eta"] = config.getboolean("plot","logscale_eta")
    else:
        plot_config["logscale_eta"] = False
    if "use_x_var" in plot_config:
        plot_config["use_x_var"] = config.getboolean("plot","use_x_var")
    else:
        plot_config["use_x_var"] = True
    if "plot_eta" in plot_config:
        plot_config["plot_eta"] = config.getboolean("plot","plot_eta")
    else:
        plot_config["plot_eta"] = True

    if args.plot_title is not None:
        plot_config["plot_title"] = args.plot_title
    if args.verbose is True:
        logr.setLevel(logging.DEBUG)

    serializer = importlib.import_module(args.serializer)
    model = getattr(models,model_name)(config=model_config) 
    if args.analyzed_data_file is not None:
        plotable_data = serializer.load(open(args.analyzed_data_file))[rule_name]
    else:
        generator = serializer.load(open(args.input_file_name))[rule_name]
        plotable_data = analyzer(generator,model,None,None,logr)
    
    plot(plotable_data,plot_config)
