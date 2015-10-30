import datetime

class TimeBucket:
    def __init__(self,start_time,stop_time, datetime_format = None):
        
        if datetime_format is not None:
            self.datetime_format = datetime_format
        else:
            self.datetime_format = "%Y%m%d%H%M%S"

        if isinstance(start_time,datetime.datetime):
            self.start_time = start_time
        else:
            self.start_time = datetime.datetime.strptime(start_time,self.datetime_format)
        if isinstance(stop_time,datetime.datetime):
            self.stop_time = stop_time
        else:
            self.stop_time = datetime.datetime.strptime(stop_time,self.datetime_format)
    
        # sanity check
        assert self.stop_time > self.start_time

    def size(self):
        return self.stop_time - self.start_time
    
    def is_in_bucket(self,this_datetime):
        return this_datetime > self.start_time and this_datetime < self.stop_time
    
    def __repr__(self):
        return_str = "'{} - {}'".format(self.start_time.strftime(self.datetime_format),self.stop_time.strftime(self.datetime_format))
        return return_str

    def __gt__(self, obj):
        if isinstance(obj,TimeBucket):
            return obj.stop_time < self.start_time
        else:
            raise NotImplemented
    
    def __lt__(self, obj):
        if isinstance(obj,TimeBucket):
            return self.stop_time < obj.start_time
        else:
            raise NotImplemented

    def __eq__(self, obj):
        if isinstance(obj,TimeBucket):
            return obj.start_time == self.start_time and obj.stop_time == self.stop_time
        else:
            raise NotImplemented

    def __ne__(self, obj):
        if isinstance(obj,TimeBucket):
            return obj.start_time != self.start_time or obj.stop_time != self.stop_time
        else:
            raise NotImplemented

    def __ge__(self, obj):
        if isinstance(obj,TimeBucket):
            return self.__gt__(obj) or self.__eq__(obj)
        else:
            raise NotImplemented
    
    def __le__(self, obj):
        if isinstance(obj,TimeBucket):
            return self.__lt__(obj) or self.__eq__(obj)
        else:
            raise NotImplemented

    def __contains__(self, obj):
        if isinstance(obj,TimeBucket):
            return obj.start_time >= self.start_time and obj.stop_time <= self.stop_time
        else:
            raise NotImplemented
    
    def lowerlaps(self,obj):
        if isinstance(obj,TimeBucket):
            cond1 = self.stop_time > obj.start_time and self.stop_time <= obj.stop_time
            cond2 = self.start_time < obj.start_time
            return cond1 and cond2
        else:
            raise NotImplemented

    def upperlaps(self,obj):
        if isinstance(obj,TimeBucket):
            cond1 = self.start_time >= obj.start_time and self.start_time < obj.stop_time
            cond2 = self.stop_time > obj.stop_time
            return cond1 and cond2
        else:
            raise NotImplemented

    def is_upperlapped_by(self, obj):
        if isinstance(obj,TimeBucket):
            cond1 = obj.start_time >= self.start_time and obj.start_time <= self.stop_time
            cond2 = obj.stop_time > self.stop_time
            return cond1 and cond2
        else:
            raise NotImplemented
    
    def is_lowerlapped_by(self, obj):
        if isinstance(obj,TimeBucket):
            cond1 = obj.stop_time >= self.start_time and obj.stop_time <= self.stop_time
            cond2 = obj.start_time < self.start_time
            return cond1 and cond2
        else:
            raise NotImplemented
    
    def intersects(self, obj):
        if isinstance(obj,TimeBucket):
            return self.lowerlaps(obj) or self.upperlaps(obj) or obj.lowerlaps(self) or obj.upperlaps(self) or self in obj or obj in self
            #cond1 = self.start_time >= obj.start_time and self.start_time <= obj.stop_time
            #cond2 = self.stop_time >= obj.start_time and self.stop_time <= obj.stop_time
            #cond3 = obj.start_time >= self.start_time and obj.start_time <= self.stop_time
            #cond4 = obj.stop_time >= self.start_time and obj.stop_time <= self.stop_time
            #return cond1 or cond2 or cond3 or cond4
        else:
            raise NotImplemented

    def get_fraction_overlapped_by(self, obj):
        if self.is_lowerlapped_by(obj):
            overlap = obj.stop_time - self.start_time
            fraction = overlap.total_seconds() / self.size().total_seconds() 
            return float(fraction)
        elif self.is_upperlapped_by(obj):
            overlap = self.stop_time - obj.start_time
            fraction = overlap.total_seconds() / self.size().total_seconds()
            return float(fraction) 
        elif obj in self:
            return float(obj.size().total_seconds() / self.size().total_seconds())
        else:
            return float(0)
