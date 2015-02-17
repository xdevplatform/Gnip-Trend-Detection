#!/usr/bin/env python

import matplotlib as mpl
mpl.use('Agg')
import matplotlib.pyplot as plt

def plot(plotable_data,title=None):            
    """
    plotable_data is a list of tuples with the following structure:
    (time_bucket, count, eta)
    """
    tbs = [tup[0].start_time for tup in plotable_data]
    cts = [tup[1] for tup in plotable_data]
    eta = [tup[3] for tup in plotable_data]
    max_cts = max(cts)
    min_cts = min(cts)

    fig = plt.figure()
    if title is not None:
        plt.title(title)
    
    ax1 = fig.add_subplot(111)
    ax1.plot(tbs,cts,'bo',tbs,cts,'k-') 
    ax1.set_ylabel("counts",color='b',fontsize=10)
    ax1.set_ylim(min_cts*0.9,max_cts*1.7)
    for tl in ax1.get_yticklabels():
        tl.set_color('b')
        tl.set_fontsize(10)
    import matplotlib.dates as mdates
    ax1.fmt_xdata = mdates.DateFormatter('%Y-%m-%d')

    ax2 = ax1.twinx()
    ax2.plot(tbs,eta,'r')
    ax2.set_ylim(min(eta)*0.9, max(eta)*1.1)
    ax2.set_ylabel("eta",color='r',fontsize=10)
    for tl in ax2.get_yticklabels():
        tl.set_color('r')
        tl.set_fontsize(10)
    fig.autofmt_xdate()
    #ax1.set_xlabel("time")
  
    if title is None:
        title = "output"
    plt.savefig("/home/jkolb/public_html/rules/{}.png".format(title),dpi=400) 

if __name__ == "__main__":

    import argparse
    import models
    import pickle
    from analyze import analyze as analyzer

    parser = argparse.ArgumentParser()
    parser.add_argument("-a",dest="alpha",type=float,default=0.95)
    parser.add_argument("-m",dest="mode",default="lc")
    parser.add_argument("-i",dest="input_file_name",default="output.pkl")
    parser.add_argument("-t",dest="plot_title",default=None)
    args = parser.parse_args()
    
    model = models.Poisson(alpha=args.alpha,mode=args.mode)
   
    generator = pickle.load(open(args.input_file_name))
    plotable_data = analyzer(generator,model)  
    plot(plotable_data,title=args.plot_title)
