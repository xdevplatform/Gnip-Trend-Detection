import sys
import json
import argparse

sys.path.insert(0,"/home/jkolb/Gnip-Trend-Detection/src/")
import library

parser = argparse.ArgumentParser() 
parser.add_argument("-t",dest="is_trend",action="store_true",default=False) 
parser.add_argument("-r",dest="reference_length",type=int,default=50) 
parser.add_argument("-l",dest="library_file_name",default="test_librarly.pkl")
args = parser.parse_args()

lib = library.Library(args.reference_length=60)

for line in sys.stdin:
    data = json.loads(line)
    for topic,series in data.items():
        print(u"adding {}".format(topic))
        lib.add_series(series,args.is_trend)

library.merge_library(lib,args.library_file_name)
library.save_library(lib,args.library_file_name)

