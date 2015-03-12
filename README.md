# Introduction

This repository contains the "Trend Detection in Social Data" whitepaper
and software that implements the models discussed in the paper. 
The software consists of code for creating even-sized time buckets ("bins"),
running point-by-point trend detection models on the data,
and plotting relevant time series. 

# Whitepaper

The trends whitepaper source can be found in the `paper` directory, which
also includes a subdirectory for the figures `figs`. A PDF version of the 
paper is included but it is not gaurenteed to be up-to-date. 

# Software

This software is designed to work easily with the [Gnip-Stream-Collector-Metrics]
(https://github.com/DrSkippy/Gnip-Stream-Collector-Metrics) package, configured to read
from a Gnip PowerTrack stream. However, any time series data can be easily
transformed into form useable by the scripts in this package. 

## Requirements

 * scipy

## Structure

The work is divided into three basic tasks:

* Bin choice - The original data is collected into larger, even-sized bins,
sized to the user's wish. This is performed by `trends/rebin.py`. 
* Analysis - Each data point is analyzed according to a model implemented in
the `trends/models.py` file. Models return a figure-of-merit (eta) for each point.
* Plotting - The original time series is plotted and overlaid with a plot of the eta values. 
This is performed by `trends.plot.py`. 

## Configuration

All the scripts mentioned in the previous section assume the presence of a configuration
file. By default, its name is `config.cfg`. You can find a template at `config.cfg.example`.
A few parameters can by set with command-line argument. Use the scripts' `-h` option
for more details.

## Example

A full example has been provided in the `example` directory. In it, you will find
formatted time series data for mentions of the "#scotus" hashtag in August-September 2014.
This file is `example/scotus.txt`. In the same directory, there is a configuration file.

The first step to to use the "rebin" script to get appropriately and evenly sized time buckets.
Let's use 2-hour buckets and put the output (which is pickled) back in the the example directory.

`python trends/rebin.py -i example/scotus.txt -o example/scotus.pkl -c example/config.cfg`

Next, we will run the analysis script, which when run alone, should return nothing.
Remember, all the modeling specification is in the config file.

`python trends/analyze.py -i example/scotus.pkl -c example/config.cfg`

To see more interesting results, let's run the plotting after the analysis, both of which 
are packaged in the plotting script:

`python trends/plot.py -i example/scotus.pkl -c example/config.cfg` 

The output PNG should be in the example directory and look like:

![scotus](https://github.com/jeffakolb/Gnip-Trend-Detection/blob/master/example/scotus.png?raw=true) 


