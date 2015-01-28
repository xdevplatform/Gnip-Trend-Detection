# Example

Suppose you have data from January 26, 2015 stored at /mnt/data, 
in the hierarchical directory format produced by Gnip-Stream-Connector-Metrics. 
A typical file might be `/mnt/data/2015/01/26/00/Twitter_2015-01-26_0049.counts`. 

Now, imagine you want to analyze data from hourly time buckets.
The first step is to run the rebin script for the desired time range, time bucket size, and rule:

`./src/rebin.py -a 20150126000000 -o 20150127000000 -r "my_favorite_rule" -b minute -n 60`

This will produce a file, `output.pkl`, 
which contains a (serialized) list of (TimeBucket, count) tuples.  

Then we run the analyze script, which reads from this file by default:

`./src/analyze.py -m lc -a 0.95`

This will print to stdout the following fields for each data point:

| TimeBucket info | count | Poisson mean | eta |
| --------------  | ----- | ------------ | --- |

See the scripts' `-h` menus for more options.
