import scipy.stats.distributions as dists
import collections

"""
Classes in the module implement trend detection techniques.
For uniform interface, all classes must implement the following functions:
    get_result(): returns the relevant figure of merit based on the current
        state of the model
    update(kwargs): updates the model with new information

"""

class WeightedDataTemplates(object):
    def __init__(self, config): 
        """
        This class implements the data-template-based trend detection technique
        presented by Nikolov 
        (http://dspace.mit.edu/bitstream/handle/1721.1/85399/870304955.pdf)
        This auxiliary module "library" (or equivalent code) is required.
        """
        
        self.current_count = None
        self.ratio = float(-1)

        self.set_up_distance_measures()

        if "series_length" in config:
            self.series_length = config["series_length"] 
        else:
            self.series_length = 12

        if "lambda" in config:
            self.lambda_1 = config["lambda"] 
        else:
            self.lambda_1 = 1

        self.current_series = []

        from sample_library import Library
        self.library = Library()

    def update(self, kwargs):
        """
        Calculate trend ratio of weights for time series based on latest data. 
        """
        
        # this must always exist
        current_count = kwargs["count"]

        check_for_self = False
        if "check_for_self" in kwargs:
            check_for_self = kwargs["check_for_self"]
            
        self.update_current_series(self.current_count)
        self.series = self.get_current_series()

        trend_weight = 0
        for item in self.library.trends: 
            trend_weight += self.weight(item,self.series,check_for_self)
        
        non_trend_weight = 0
        for item in self.library.non_trends: 
            non_trend_weight += self.weight(item,self.series,check_for_self)

        self.ratio = trend_weight / non_trend_weight

    def get_result(self):
        """
        Return result or figure-of-merit (ratio of weights, in this case) defined by the mode of operation
        """
        return self.ratio

    def update_current_series(self,new_count):
        """
        add new data to time series
        """
        self.series.append(new_count)

    def get_current_series(self):
        """
        Get time series appropriate to latest data
        """
        return self.series[-self.series_length:-1]

    def weight(self,topic,series,check_for_self):
        """
        Get the minimum distance between the series and all series-length subset of topic.
        Exponentiate it and return the weight.
        """

        # account for case when topic in library is used as the series 
        if check_for_self:
            if topic == series:
                return 0

        min_distance = sys.float_info.max
        for sub_topic in topic.get_subtopics(self.series_length):
            d = getattr(self.distance_measures,self.distance_measure_name)(sub_topic,series)  
            if d < min_distance:
                min_distance = d

        return math.exp(-float(min_distance) * self.lambda_1 )

    def set_up_distance_measures(self):
        """
        Define and instantiate helper class for distance measures.
        """
        class DistanceMeasures(self):
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
    This class implements Poisson-based background models. 
    It supports a small set of options for determining the Poisson mean.
    """
    def __init__(self, mode = "lc", config = {"alpha":0.99}):
        
        self.mode = mode
        self.mean = None
        self.current_count = None
        
        if self.mode == "lc":
            self.alpha = float(config["alpha"])

        if self.mode == "a":
            self.periodic_data = collections.defaultdict(dict)
            self.alpha = float(config["alpha"])

    def update(self, **kwargs):
        """
        Update the internal model with data supplied with kwargs;
        keyword "count" is required.
        """
        
        #this must always exist
        current_count = kwargs["count"]

        #manage last (previous) count
        self.last_count = self.current_count
        if "last_count" in kwargs:
            self.last_count = kwargs["last_count"]
        
        self.current_count = current_count 
        
        if self.mode == "lc":
            self.mean = self.last_count

        if self.mode == "a": 
            period = kwargs["period"]
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
        For use with Poisson-based methods:
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
