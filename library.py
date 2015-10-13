import pickle 
import os
import math
import collections
import random

class TopicSeries(list):
    """
    Derived "list" class, with ability to return
    all subsets of a particular length
    """
    def get_subseries(self,length):
        """ Generator that returns all sub-lists of self 
        that are length "length"
        """
        index = 0
        while index + length <= len(self):
            yield self[index:index+length]
            index += 1

class Library(object):

    def __init__(self, **kwargs):
        """
        set up internal lists, get parameter values, 
        and set up transformation functions
        """
        self.trends = []
        self.non_trends = []
        
        self.config = {}
        # default values
        self.config["reference_length"] = 210
        self.config["n_smooth"] = 80
        self.config["alpha"] = 1.2
        # add values passed into ctor
        self.config.update(kwargs["config"])

        # Transformation functions are defined globally and added here to list.
        
        # transformations to be run on reference series
        self.transformations = []
        self.transformations.append(add_one)
        self.transformations.append(unit_normalization)
        self.transformations.append(logarithmic_scaling)
        self.transformations.append(smoothing)
        self.transformations.append(sizing)
        
        # transformations to be run on test series 
        self.test_transformations = []
        self.test_transformations.append(add_one)
        self.test_transformations.append(unit_normalization)
        self.test_transformations.append(logarithmic_scaling)
        self.test_transformations.append(smoothing)
       
    def add_reference_series(self,series,is_trend=True):
        """
        add a reference time series to the internal lists,
        after transforming it 
        """
        self.config["is_trend"] = is_trend
        series = self.transform_input(series,is_test_series=False) 
        if is_trend:
            self.trends.append( TopicSeries(series) )
        else:
            self.non_trends.append( TopicSeries(series) )

    def transform_input(self,series,is_test_series,config=None):
        """
        Run series sequentially through the functions 
        in the transformations list
        """

        transformations = self.transformations
        if is_test_series:
            transformations = self.test_transformations
        
        for transformation in transformations:
            if config is not None:
                series = transformation(series,config) 
            else:
                series = transformation(series,self.config)

        return series

    def combine(self, lib):
        """
        Manage all attributes of class that are important for combinations. 
        Take care not to allow duplicates.
        """
        if lib.trends != []:
            assert self.trends == []
            self.trends = lib.trends

        if lib.non_trends != []: 
            assert self.non_trends == []
            self.non_trends = lib.non_trends

def add_one(series, config):
    """ Add a count of 1 to every count in the series """
    return [ ct+1 for ct in series ]

def unit_normalization(series, config):
    """ Do unit normalization based on "reference_length" number of bins
    at the end of the series"""
    reference_length = int(config["reference_length"])
    SMALL_NUMBER = 0.00001
    offset = int(config["baseline_offset"])
    lower_idx = -(int(config["reference_length"]) + offset)
    upper_idx = -offset
    total = sum(series[lower_idx:upper_idx])/float(reference_length)
    if total == 0:
        total = SMALL_NUMBER
    return [float(pt)/total for pt in series]

def spike_normalization(series, config):
    alpha = float(config["alpha"])
    new_series = []
    prev_pt = 0
    for pt in series: 
        if pt == 0:
            new_pt = 0
        else:
            new_pt = math.pow(abs(pt - prev_pt), alpha)
        new_series.append(new_pt)
        prev_pt = pt
    return new_series

def smoothing(series,config): 
    n_smooth = int(config["n_smooth"])
    queue = collections.deque()
    new_series = []
    for pt in series:
        queue.append(pt)
        new_series.append( float(sum(queue))/len(queue) )
        if len(queue) >= n_smooth:
            queue.popleft()
    return new_series

def slow_smoothing(series,config): 
    n_smooth = int(config["n_smooth"])
    queue = []
    new_series = []
    for pt in series:
        queue.append(pt)
        new_series.append( float(sum(queue))/len(queue) )
        if len(queue) >= n_smooth:
            del queue[0]
    return new_series

def index_smoothing(series,config): 
    n_smooth = int(config["n_smooth"])
    new_series = []
    idx = 1
    while idx < len(series):
        lower_idx = max(0,idx-n_smooth)
        sub_series = series[lower_idx:idx]
        new_series.append( float(sum(sub_series))/len(sub_series) )
        idx+=1

    return new_series

def logarithmic_scaling(series, config): 
    new_series = []
    
    for pt in series:
        if pt <= 0:
            pt = 0.00001
        new_series.append(math.log10(pt))
    return new_series

def sizing(series, config): 
    new_series = series[-int(config["reference_length"]):]
    return new_series

def save_library(library, file_name):
    pickle.dump(library,open(file_name,"w"))

def load_library(file_name):
    try:
        return pickle.load(open(file_name)) 
    except EOFError:
        return Library()

def merge_library(library, file_name): 
    """
    if file exists, get Library object from it,
    and combine with library passed to function
    """
    if os.path.exists( os.path.join(os.getcwd(),file_name) ):
        lib_from_file = load_library(file_name)
        library.combine(lib_from_file)
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
    lib.add_reference_series(series,trend = args.is_trend)
    merge_library(lib,args.lib_file_name)
    save_library(lib,args.lib_file_name)
