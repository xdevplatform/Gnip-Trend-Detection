import collections
import datetime
import sys
import pickle
import math
import logging
from dateutil.parser import parse

import numpy as np
import scipy.stats.distributions as dists
from sklearn.linear_model import LinearRegression

from .mk_test import mk_test

"""
Classes in the module implement trend detection techniques.
For uniform interface, all classes must implement the following functions:
    get_result(): returns the relevant figure of merit based on the current
        state of the model
    update(kwargs): updates the model with new information;
        required keyword arguments may differ between models

"""

class MannKendall:
    def __init__(self, config):
        self.counts = []
        try:
            self.window_size = int(config['window_size'])
        except KeyError:
            self.window_size = None
        try:
            self.alpha = float(config['alpha'])
        except KeyError:
            self.alpha = 0.05

    def update(self, **kwargs):
        count = kwargs["count"]
        self.counts.append( count )

    def get_result(self):
        x = self.counts
        if self.window_size is not None:
            x = self.counts[-self.window_size:]
        return mk_test(x,self.alpha)[3]

class LinearRegressionModel(object):
    def __init__(self, config):
        self.counts = [] 
        self.averaged_counts = []
        self.min_points = int(config['min_points'])
        try:
            self.averaging_window_size = int(config["averaging_window_size"]) 
        except KeyError:
            self.averaging_window_size = 1
        try:
            self.norm_by_mean = bool(config['norm_by_mean'])
        except KeyError:
            self.norm_by_mean = False
        try:
            self.regression_window_size = int(config['regression_window_size']) 
        except KeyError:
            self.regression_window_size = None
        self.regression = LinearRegression()

    def update(self, **kwargs):
        count = kwargs["count"]
        self.counts.append( count )
        
        size = self.averaging_window_size
        if len(self.counts) >= size:
            self.averaged_counts.append( sum(self.counts[-size:])/float(size) ) 
        else:
            self.averaged_counts.append(0)

    def get_result(self):
        """ Run a linear fit on the averaged count,
        which will be the raw counts if not otherwise specified. """
        if len(self.averaged_counts) < self.min_points:
            return 0
        if self.regression_window_size is not None:
            y = np.array(self.averaged_counts[-self.regression_window_size:])  
        else:
            y = np.array(self.averaged_counts)  
        if self.norm_by_mean: 
            y = y/np.mean(y)
        x = range(len(y))
        X = [[i] for i in x]
        slope = self.regression.fit(X,y).coef_[0]
        return slope

class WeightedDataTemplates(object):
    def __init__(self, config): 
        """
        This class implements the data-template-based trend detection technique
        presented by Nikolov 
        (http://dspace.mit.edu/bitstream/handle/1721.1/85399/870304955.pdf)
        The auxiliary module "library" (or equivalent code) is required.
        """
        
        # set up basic member variables
        self.current_count = None
        self.total_series = []
        self.trend_weight = None
        self.non_trend_weight = None

        self.SMALL_NUMBER = 0.001

        # manage everything related to distance measurements
        self.set_up_distance_measures(config)

        # config handling
        if "series_length" in config:
            self.series_length = int(config["series_length"])  
        else:
            self.series_length = 50

        if "reference_length" in config:
            self.reference_length = int(config["reference_length"])
        else:
            self.reference_length = 210

        if "lambda" in config:
            self.Lambda = float(config["lambda"])
        else:
            self.Lambda = 1

        #if "logger" in config:
        #    self.logger = config["logger"]
        #else:
        #    self.logger = logging.getLogger("default_template_logger") 
        #self.logger = logr

        from .library import Library
        if "library_file_name" in config:
            self.library = pickle.load(open(config["library_file_name"],'rb'))
        else:
            self.library = library.Library(config={})

        self.config = config

    def update(self, **kwargs):
        """
        Calculate trend weights for time series based on latest data. 
        """
        
        # this must always exist
        current_count = kwargs["count"]

        check_for_self = False
        if "check_for_self" in kwargs:
            check_for_self = kwargs["check_for_self"]
           
        # add current data point to series 
        self.total_series.append(current_count)

        # don't return anything meaningful until total_series is long enough
        if len(self.total_series) < self.reference_length or sum(self.total_series) == 0: 
            self.trend_weight = float(0)
            self.non_trend_weight = float(0)
            return

        # transform a "reference_length"-sized sub-series
        #transformed_series = self.total_series[-self.reference_length:]
        #for transformation in self.library.test_transformations:
        #    transformed_series = transformation(transformed_series,self.config) 
        transformed_series = self.library.transform_input(self.total_series[-self.reference_length:],is_test_series=True,config=self.config)
        # get correctly-sized test series
        test_series =  transformed_series[-self.series_length:]

        self.trend_weight = float(0)
        for reference_series in self.library.trends:  
            weight = self.weight(reference_series,test_series,check_for_self) 
            #self.logger.debug("trend wt: {}".format(weight))
            self.trend_weight += weight
        
        self.non_trend_weight = float(0)
        for reference_series in self.library.non_trends: 
            weight = self.weight(reference_series,test_series,check_for_self)
            #self.logger.debug("non trend wt: {}".format(weight))
            self.non_trend_weight += weight

    def get_result(self):
        """
        Return result or figure-of-merit (ratio of weights, in this case) defined by the mode of operation
        """
        if self.trend_weight is None or self.non_trend_weight is None:
            return -1
        if self.non_trend_weight == 0:
            self.non_trend_weight = self.SMALL_NUMBER

        return self.trend_weight / self.non_trend_weight

    def weight(self,reference_series,test_series,check_for_self):
        """
        Get the minimum distance between the series and all test_series-length subset of reference_series.
        Exponentiate it and return the weight.
        """

        # account for case when reference_series in library is used as the test_series 
        if check_for_self:
            if reference_series == test_series: 
                #self.logger.debug("found self in library!")
                return 0

        min_distance = sys.float_info.max
        for sub_series in reference_series.get_subseries(self.series_length):
            d = getattr(self.distance_measures,self.distance_measure_name)(sub_series,test_series)  
            #self.logger.debug("Distance: {}".format(d))
            if d < min_distance:
                min_distance = d
        #self.logger.debug("min d: {}".format(min_distance))
        return math.exp(-float(min_distance) * self.Lambda )

    def set_up_distance_measures(self, config): 
        """
        Instantiate helper class for distance measures.
        """
        if "distance_measure_name" in config:
            self.distance_measure_name = config["distance_measure_name"]
        else:
            self.distance_measure_name = "euclidean"

        self.distance_measures = DistanceMeasures()

class DistanceMeasures(object):
    """
    Helper class for distance measures.
    """
    def __init__(self):
        pass
    def euclidean(self,a,b):
        sum = 0
        for ai,bi in zip(a,b):
            sum += abs(ai - bi)
        return sum

class Poisson(object):
    """
    This class implements Poisson background models. 
    It supports a small set of options for determining the Poisson mean.
    """
    def __init__(self, config = {"alpha":0.99,"mode":"lc","period_list":["hour"]}):
        
        self.mode = config["mode"]
        self.mean = None
        self.current_count = None
        
        if self.mode == "lc":
            self.alpha = float(config["alpha"])

        if self.mode == "a":
            self.periodic_data = collections.defaultdict(dict)
            self.alpha = float(config["alpha"])
            self.period_list = config["period_list"].split(",")

    def update(self, **kwargs):
        """
        Update the internal model with data supplied with kwargs;
        keyword "count" is required.
        """
        
        #this must always exist
        current_count = kwargs["count"]

        #this must always exist
        if isinstance(kwargs['interval_start_time'],datetime.datetime):
            start_time = kwargs['interval_start_time'] 
        elif isinstance(kwargs['interval_start_time'],str):
            start_time = parse(kwargs['interval_start_time'])
        else:
            raise TypeError("'interval_start_time' kw arg to update method must be 'str' or 'datetime'")

        #manage last (previous) count
        self.last_count = self.current_count
        if "last_count" in kwargs:
            self.last_count = kwargs["last_count"]
        
        self.current_count = current_count 
        
        if self.mode == "lc":
            self.mean = self.last_count
        
        if self.mode == "a": 
            # create a ':'-separated string of the start_time attributes, as specified by self.period_list 
            # this defines the key over which counts will be averaged
            period = ":".join([str(getattr(start_time,p)) for p in self.period_list])
            
            if "num" in self.periodic_data[period]:
                self.periodic_data[period]["num"] += current_count 
            else:
                self.periodic_data[period]["num"] = current_count
            if "denom" in self.periodic_data[period]:
                self.periodic_data[period]["denom"] += 1 
            else:
                self.periodic_data[period]["denom"] = 1

            self.mean = float(self.periodic_data[period]["num"])/self.periodic_data[period]["denom"]


    def get_relative_confidence_interval(self):
        """
        Get relative (fractional) confidence interval size, 
        based on "self.mean" attribute.
        """
        if self.mean is None:
            return None
        delta_r = dists.poisson.interval(self.alpha,self.mean)[1] - dists.poisson.interval(self.alpha,self.mean)[0]
        relative_confidence_interval = delta_r/self.mean
        return relative_confidence_interval

    def get_sensitivity(self): 
        """
        sensitivity is the relative change w.r.t the mean
        """
        if self.mean is None or self.current_count is None or self.mean == 0:
            return None
        Delta_r = abs(self.current_count - self.mean) 
        sensitivity = float(Delta_r)/self.mean
        return sensitivity

    def get_mean(self):
        """
        Safe access to the internally-stored mean
        """
        if self.mean is None:
            return 0
        else:
            return self.mean

    def get_result(self): 
        """
        Return result or figure-of-merit (eta, in this case) defined by the mode of operation
        """
        # calculate and return eta
        s = self.get_sensitivity()
        r = self.get_relative_confidence_interval()
        if s is None or r is None:
            return 0
        return s/r
