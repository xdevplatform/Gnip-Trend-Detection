#!/bin/bash

# This script takes a list of topic names,
# runs search API queries that produce time series of counts,
# removes series that have more than 10% zero-counts,
# and saves the series to a JSON-formatted file.

start_time="2015-02-01T00:00"
end_time="2015-02-20T00:00"
unit="hour"

input_file_name=$1
output_file_name="series_`echo $input_file_name | sed 's/\..*$//'`"
output_dir=counts

rm -f counts/*
while read topic; do
    echo "Doing $topic"
    search_api.py -f "\"$topic\"" -s $start_time -e $end_time -b $unit timeline | jq -c "{\"${topic}\":"' [.results[] | .count]}' | python cull_series.py >> ${output_dir}/${output_file_name}.json
    sleep 0.3
done < $input_file_name
