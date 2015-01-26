#!/usr/bin/env python 

import datetime
import time_bucket 
import time
import sys

a = time_bucket.TimeBucket(datetime.datetime.utcnow(),datetime.datetime.utcnow() + datetime.timedelta(seconds=30))
time.sleep(1)
b = time_bucket.TimeBucket(datetime.datetime.utcnow(),datetime.datetime.utcnow() + datetime.timedelta(seconds=1))  
time.sleep(3)
c = time_bucket.TimeBucket(datetime.datetime.utcnow(),datetime.datetime.utcnow() + datetime.timedelta(seconds=60))  

op_list = [
    " < "
    ," > "
    ," in "
    ,".intersects("
    ,".upperlaps("
    ,".lowerlaps("
    ,".is_upperlapped_by("
    ,".is_lowerlapped_by(" 
    ,".get_fraction_overlapped_by("
]

for op in op_list:
    for one,two in [('a','b'),('b','a'),('a','c'),('c','a'),('b','c'),('c','b')]:
        eval_str = one + op + two 
        if op[-1] == "(":
            eval_str += ")"
        print(eval_str)
        print(eval(eval_str))

sys.exit()
print("a < b")
print(a < b)
print("a > b")
print(a > b)
print("a < c")
print(a < c)
print("a > c")
print(a > c)
print("b < c")
print(b < c)
print("b > c")
print(b > c)

print("a in b")
print(a in b)
print("b in a")
print(b in a)
print("a in c")
print(a in c)
print("c in a")
print(c in a)
print("b in c")
print(b in c)
print("c in b")
print(c in b)

