import pickle 
import os

class TopicSeries(list):
    """
    Derived "list" class, with ability to return
    all subsets of a particular length
    """
    def get_subtopics(self,length):
        index = 0
        while index + length <= len(self):
            yield self[index:index+length]
            index += 1

class Library(object):

    def __init__(self):
        self.trends = []
        self.non_trends = []

    def add_series(self,series,trend=True):
        
        series = self.transform_input(series)
        if trend:
            self.trends.append(TopicSeries(series))
        else:
            self.non_trends.append(TopicSeries(series))

    def transform_input(self.series):
        return series

def save_library(library, file_name):
    pickle.dump(library,open(file_name,"w"))

def get_library(file_name):
    try:
        return pickle.load(open(file_name)) 
    except EOFError:
        return Library()

def merge_library(library, file_name): 
    if os.path.exists( os.path.join(os.getcwd(),file_name) ):
        lib_from_file = get_library(file_name)
        library.trends.extend(lib_from_file.trends)
        library.non_trends.extend(lib_from_file.non_trends)
    return library

if __name__ == "__main__":
    import sys
    import argparse

    parser = argparse.ArgumentParser() 
    parser.add_argument("-t",dest="is_trend",default=False,action="store_true")
    parser.add_argument("-f",dest="lib_file_name",default="library.pkl")
    args = parser.parse_args()

    series = []
    for ct in sys.stdin: 
        series.append(ct)

    lib = Library()
    lib.add_series(series,trend = args.is_trend)
    merge_library(lib,args.lib_file_name)
    save_library(lib,args.lib_file_name)
