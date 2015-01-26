#!/usr/bin/env python

import pickle
import sys

import models
import time_bucket

m = models.Poisson()

for line in pickle.load(open("output.pkl")):
    tb = line[0]
    count = line[1]
    m.update(count)
    print("{0} {1} {2:.2f}".format(tb,str(count),m.get_eta()))

