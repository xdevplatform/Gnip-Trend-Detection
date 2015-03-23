import sys
import json
import argparse
import ConfigParser

sys.path.insert(0,"/home/jkolb/Gnip-Trend-Detection/src/")
import library

parser = argparse.ArgumentParser() 
parser.add_argument("-t",dest="is_trend",action="store_true",default=False) 
parser.add_argument("-c",dest="config_file_name",default="config.cfg") 
parser.add_argument("-l",dest="library_file_name",default="test_librarly.pkl")
args = parser.parse_args()

cp = ConfigParser.ConfigParser()
cp.read(args.config_file_name)
model_config = dict(cp.items("WeightedDataTemplates_model"))

lib = library.Library(config=model_config)

for line in sys.stdin:
    data = json.loads(line)
    for topic,series in data.items():
        print(u"adding {}".format(topic))
        lib.add_series(series,args.is_trend)

library.merge_library(lib,args.library_file_name)
library.save_library(lib,args.library_file_name)

