# Introduction

This software provides some simple methods of trend detection.
It include code for creating even-sized time buckets ("bins"),
running point-by-point trend detection models on the data,
and plotting relevant time series. 

This software is designed to work easily with the [Gnip-Stream-Collector-Metrics]
(https://github.com/DrSkippy/Gnip-Stream-Collector-Metrics) package, configured to read
from a Gnip PowerTrack stream. However, any time series data can be easily
transformed into form useable by the scripts in this package. 

# Structure

The work is divided into three basic tasks:

* Bin choice - The original data is collected into larger, even-sized bins,
sized to the user's wish
* Analysis - Each data point is analyzed according to a model implemented in
the `models.py` file. Models return a figure-of-merit (eta) for each point.
* Plotting - The original time series is plotted and overlaid with a plot of the eta values. 

# Example

Suppose you have data from January 26, 2015 stored at /mnt/data, 
in the hierarchical directory format produced by Gnip-Stream-Connector-Metrics. 
A typical file might be `/mnt/data/2015/01/26/00/Twitter_2015-01-26_0049.counts`. 

Now, imagine you want to analyze data from hourly time buckets.
The first step is to run the rebin script for the desired time range, time bucket size, and rule.
We choose the full data, with 60 minute time buckets. 

`./src/rebin.py -a 20150126000000 -o 20150127000000 -r "my_favorite_rule" -b minute -n 60`

This will produce a file, `output.pkl`, 
which contains a (serialized) list of (TimeBucket, count) tuples.  

Then we run the analyze script, which reads from this file by default.
We use the default point-by-point Poisson model, with 95% confidence intervals:

`./src/analyze.py -m lc -a 0.95`

This will return list of tuples with the following fields:

| TimeBucket info | count | Poisson mean | eta |
| --------------  | ----- | ------------ | --- |


See the scripts' `-h` menus for more options.
