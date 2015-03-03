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
        index = 0
        while index + length <= len(self):
            yield self[index:index+length]
            index += 1

class Library(object):

    def __init__(self, **kwargs):
        """
        set up internal lists
        """
        self.trends = []
        self.non_trends = []
        self.transformations = []

        self.set_up_transformations(kwargs)

    def add_series(self,series,is_trend=True):
        """
        add a time series to the internal lists,
        after transforming it 
        """
        self.config["is_trend"] = is_trend
        series = self.transform_input(series)
        if is_trend:
            self.trends.append( TopicSeries(series) )
        else:
            self.non_trends.append( TopicSeries(series) )

    def transform_input(self,series):
        """
        Run series sequentially through the functions 
        in the transformations list
        """
        for transformation in self.transformations:
            series = transformation(series,self.config)

        return series

    def set_up_transformations(self, config):
        """
        Convenience method to be called in ctor.
        Transformation functions are defined globally and added here to list.
        """
        self.transformations.append(unit_normalization)
        self.transformations.append(spike_normalization)
        self.transformations.append(smoothing)
        self.transformations.append(logarithmic_scaling)
        self.transformations.append(sizing)

        self.config = {}
        self.config["reference_length"] = 60
        self.config["n_smooth"] = 4
        self.config["alpha"] = 1.2

        self.config.update(config)

    def combine(self, lib):
        """
        Manage all attributes of class that are important for combinations. 
        Take care not to allow duplicates.
        """
        self.trends = list(set(self.trends.extend(lib.trends)))
        self.non_trends = list(set(self.non_trends.extend(lib.non_trends)))
        #self.transformations = set(self.transformations.extend(lib.transformations))

def unit_normalization(series, config):
    size = len(series)
    new_series = []
    for pt in series:
        new_series.append(float(pt)/size)
    return new_series

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
    N_smooth = int(config["n_smooth"])
    queue = collections.deque()
    new_series = []
    for pt in series:
        queue.append(pt)
        if len(queue) > N_smooth:
            queue.popleft()
        new_series.append( sum(queue) )
    return new_series

def logarithmic_scaling(series, config): 
    new_series = []
    series_min = min(series)
    for pt in series:
        new_series.append(math.log10(pt + series_min + 1))
    return new_series

def sizing(series, config):
    size_r = config["reference_length"]
    
    if bool(config["is_trend"]):
        max_idx = None
        max_pt = -5000
        idx = 0
        for pt in series:
            if pt > max_pt:
                max_idx = idx
                max_pt = pt
            idx += 1
        #print("returning {} - {}".format(series[max_idx - size_r],series[max_idx]))
        #print(series[max_idx - size_r:max_idx])
        return series[max_idx - size_r:max_idx]
    else:
        random.seed()
        index = random.randint(0,len(series)-size_r) 
        return series[index:index+size_r]

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
    lib.add_series(series,trend = args.is_trend)
    merge_library(lib,args.lib_file_name)
    save_library(lib,args.lib_file_name)
