#!/bin/bash

##
# This script gets one random file from each hour/day/month/year
# combination. From these data, we run a term frequency analysis
# to generate a list of random topics.
#
# Requirements: 
#  `term_frequency.py`, from pypi package: "sngrams" 
#  `jq` - http://stedolan.github.io/jq/
#  a corpus of Twitter data, organized by date 
##

year=2015
month=02
day_list=`seq -f%02g 1 25`
hour_list="00 03 06 09 12 15 18 21"
num_lines=50000

data_dir=/mnt2/archives/twitter

for day in $day_list; do
    for hour in $hour_list; do
        file_list=`find ${data_dir}/${year}/${month}/${day}/${hour}/ -name \*gz`
        
        echo "Doing ${day}/${hour}" 1>&2

        # get randomly-selected file from list
        upper_bound=`echo $file_list | wc -w`   
        lower_bound=0
        number=0
        while [ "$number" -le $lower_bound ]; do
            number=$RANDOM 
            let "number %= $upper_bound"
        done
        file=`echo $file_list | cut -d" " -f$number`

        # get just the Tweet bodies
        zcat $file | head -${num_lines} | jq '.body'
    done 
done | term_frequency.py -w -k4 -c4 -n3000 | grep -v 'percent of total' > random_topics.txt

