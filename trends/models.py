import collections
import sys
import pickle
import math

import scipy.stats.distributions as dists

"""
Classes in the module implement trend detection techniques.
For uniform interface, all classes must implement the following functions:
    get_result(): returns the relevant figure of merit based on the current
        state of the model
    update(kwargs): updates the model with new information;
        required keyword arguments may differ between models

"""

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

        if "lambda" in config:
            self.Lambda = float(config["lambda"])
        else:
            self.Lambda = 1

        from library import Library
        if "library_file_name" in config:
            self.library = pickle.load(open(config["library_file_name"]))
        else:
            self.library = Library()

    def update(self, **kwargs):
        """
        Calculate trend weights for time series based on latest data. 
        """
        
        # this must always exist
        current_count = kwargs["count"]

        check_for_self = False
        if "check_for_self" in kwargs:
            check_for_self = kwargs["check_for_self"]
           
        # add current data to series and get appropriately-sized sub-series
        self.total_series.append(current_count)
        current_series =  self.total_series[-self.series_length:-1]
        # don't return anything meaningful until total_series is long enough
        if len(self.total_series) < self.series_length:
            self.trend_weight = float(0)
            self.non_trend_weight = float(0)
            return

        # transform the test series just like the reference series
        current_series = self.library.transform_input(current_series,is_test_series=True)
        #print(current_series) 
        self.trend_weight = float(0)
        for reference_series in self.library.trends:  
            #print reference_series
            weight = self.weight(reference_series,current_series,check_for_self) 
            #print("trend wt: {}".format(weight))
            self.trend_weight += weight
        
        self.non_trend_weight = float(0)
        for reference_series in self.library.non_trends: 
            #print reference_series
            weight = self.weight(reference_series,current_series,check_for_self)
            #print("non trend wt: {}".format(weight))
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
                print("found self in library!")
                return 0

        min_distance = sys.float_info.max
        for sub_series in reference_series.get_subseries(self.series_length):
            d = getattr(self.distance_measures,self.distance_measure_name)(sub_series,test_series)  
            #print("Distance: {}".format(d))
            if d < min_distance:
                min_distance = d
        #print("min d: {}".format(min_distance))
        return math.exp(-float(min_distance) * self.Lambda )

    def set_up_distance_measures(self, config): 
        """
        Define and instantiate helper class for distance measures.
        """
        if "distance_measure_name" in config:
            self.distance_measure_name = config["distance_measure_name"]
        else:
            self.distance_measure_name = "euclidean"

        class DistanceMeasures(object):
            def __init__(self):
                pass
            def euclidean(self,a,b):
                sum = 0
                for ai,bi in zip(a,b):
                    sum += abs(ai - bi)
                return sum
        self.distance_measures = DistanceMeasures()

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
        tb = kwargs["time_bucket"]

        #manage last (previous) count
        self.last_count = self.current_count
        if "last_count" in kwargs:
            self.last_count = kwargs["last_count"]
        
        self.current_count = current_count 
        
        if self.mode == "lc":
            self.mean = self.last_count
        
        if self.mode == "a": 
            # create a ':'-separated string of the tb.start_time attributes, as specified by self.period_list 
            # this defines the key over which counts will be averaged
            period = ":".join([str(getattr(tb.start_time,p)) for p in self.period_list])
            
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
