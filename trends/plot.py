#!/usr/bin/env python

import matplotlib as mpl
mpl.use('Agg')
import matplotlib.pyplot as plt

def plot(plotable_data,config):            
    """
    plotable_data is a list of tuples with the following structure:
    (time_bucket, count, eta)
    """
    use_x_var = False

    tbs = [tup[0].start_time for tup in plotable_data]
    cts = [tup[1] for tup in plotable_data]
    eta = [tup[2] for tup in plotable_data]
    if cts == []:
        return -1
    max_cts = max(cts)
    min_cts = min(cts)
    
    fig = plt.figure()
    plt.title(config["plot_title"])
    
    ax1 = fig.add_subplot(111)
    if use_x_var:
        ax1.plot(tbs,cts,'bo',tbs,cts,'k-') 
    else:
        ax1.plot(cts,'bo',cts,'k-') 
    ax1.set_ylabel("counts",color='b',fontsize=10)
    ax1.set_ylim(min_cts*0.9,max_cts*1.7)
    for tl in ax1.get_yticklabels():
        tl.set_color('b')
        tl.set_fontsize(10)
    import matplotlib.dates as mdates
    ax1.fmt_xdata = mdates.DateFormatter('%Y-%m-%d')
    plt.locator_params(axis = 'y', nbins = 4)
    ax1.set_xlabel("time (hours)")

    ax2 = ax1.twinx()
    if use_x_var:
        ax2.plot(tbs,eta,'r')
    else:
        ax2.plot(eta,'r')
    min_eta = 0
    if min(eta) > 0:
        min_eta = min(eta) * 0.9
    ax2.set_ylim(min_eta, max(eta)*1.1)
    ax2.set_ylabel("eta",color='r',fontsize=10)
    for tl in ax2.get_yticklabels():
        tl.set_color('r')
        tl.set_fontsize(10)
    fig.autofmt_xdate()
  
    plt.savefig(config["plot_dir"] + "/{}".format(config["plot_title"]),dpi=400) 

    return 0

if __name__ == "__main__":
    
    import argparse
    import ConfigParser
    import pickle
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
    parser.add_argument("-i",dest="input_file_name",default="output.pkl") 
    parser.add_argument("-c",dest="config_file_name",default=None,help="get configuration from this file")
    parser.add_argument("-t",dest="plot_title",default=None) 
    args = parser.parse_args()

    plot_config = {}
    if args.config_file_name is not None:
        config = ConfigParser.SafeConfigParser()
        config.read(args.config_file_name)
        model_name = config.get("analyze","model_name")
        model_config = dict(config.items(model_name + "_model")) 
        if config.has_section("plot"):
            plot_config = dict(config.items("plot"))
        else:
            plot_config["plot_title"] = "output"
            plot_config["plot_dir"] = "."
    else:
        model_config = {"alpha":0.99,"mode":"lc"}
        model_name = "Poisson"
        plot_config["plot_title"] = "output"
        plot_config["plot_dir"] = "."
   
    if args.plot_title is not None:
        plot_config["plot_title"] = args.plot_title

    model = getattr(models,model_name)(config=model_config) 
    generator = pickle.load(open(args.input_file_name))
    plotable_data = analyzer(generator,model,logr)  
    plot(plotable_data,plot_config)
