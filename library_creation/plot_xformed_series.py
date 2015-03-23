import sys
import argparse
import pickle
import ConfigParser

import matplotlib as mpl
mpl.use('Agg')
import matplotlib.pyplot as plt

sys.path.insert(0,"/Users/jkolb/work/repos/Gnip-Trend-Detection/trends/")

parser = argparse.ArgumentParser()
parser.add_argument("-c",dest="config_file_name",default="config.cfg")
parser.add_argument("-l",dest="library_file_name",default=None)
args = parser.parse_args()

cp = ConfigParser.ConfigParser()
cp.read(args.config_file_name)
model_name = cp.get("analyze","model_name")
plot_config = dict(cp.items("plot"))
model_config = dict(cp.items(model_name + "_model"))

library_file_name = model_config["library_file_name"]
if args.library_file_name is not None:
    library_file_name = args.library_file_name

lib = pickle.load(open(library_file_name))

trend_series_args = []
for series in lib.trends[1:]:
    trend_series_args.append(series)
    trend_series_args.append("r-")
non_trend_series_args = []
for series in lib.non_trends:
    non_trend_series_args.append(series)
    non_trend_series_args.append("k--")

fig = plt.figure()
plt.title("transformed time series")

ax1 = fig.add_subplot(111)
ax1.plot(*trend_series_args)
ax1.yaxis.set_visible(False)

ax2 = ax1.twinx()
ax2.plot(*non_trend_series_args)
ax2.yaxis.set_visible(False)

#ax3 = ax1.twinx()
#ax3.plot(lib.trends[0],"bo")

plt.savefig(plot_config["plot_dir"] + "/xformed_series.png",dpi=400) 
