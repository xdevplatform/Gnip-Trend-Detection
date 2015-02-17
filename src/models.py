import scipy.stats.distributions as dists
import collections

"""
modes of operation:

"lc" -> "last count"
"h" -> (NOT IMPLEMENTED)

lc:
    Poisson mean is the count previous in the time series

h:  NOT IMPLEMENTED
    
"""

class Poisson():
    def __init__(self, alpha = 0.99, mode = "lc"):
        self.alpha = alpha
        self.mean = None
        self.current_count = None
        self.mode = mode

        if self.mode == "h":
            self.hourly_data = collections.defaultdict(dict)

    def update(self, **kwargs):
        
        #this must always exist
        current_count = kwargs["count"]

        #manage last count
        self.last_count = self.current_count
        if "last_count" in kwargs:
            self.last_count = kwargs["last_count"]
        
        self.current_count = current_count 
        
        if self.mode == "lc":
            self.mean = self.last_count

        if self.mode == "h": 
            if "num" in self.hourly_data[kwargs["hour"]]:
                self.hourly_data[kwargs["hour"]]["num"] += current_count 
            else:
                self.hourly_data[kwargs["hour"]]["num"] = current_count
            if "denom" in self.hourly_data[kwargs["hour"]]:
                self.hourly_data[kwargs["hour"]]["denom"] += 1 
            else:
                self.hourly_data[kwargs["hour"]]["denom"] = 1

            self.mean = float(self.hourly_data[kwargs["hour"]]["num"])/self.hourly_data[kwargs["hour"]]["denom"]

    def get_relative_confidence_interval(self):
        if self.mean is None:
            return None
        delta_r = dists.poisson.interval(self.alpha,self.mean)[1] - dists.poisson.interval(self.alpha,self.mean)[0]
        relative_confidence_interval = delta_r/self.mean
        return relative_confidence_interval

    def get_sensitivity(self):
        if self.mean is None or self.current_count is None or self.mean == 0:
            return None
        Delta_r = abs(self.current_count - self.mean) 
        sensitivity = float(Delta_r)/self.mean
        return sensitivity

    def get_mean(self):
        if self.mean is None:
            return 0
        else:
            return self.mean

    def get_eta(self): 
        s = self.get_sensitivity()
        r = self.get_relative_confidence_interval()
        if s is None or r is None:
            return 0
        return s/r
