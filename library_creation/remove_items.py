import sys

"""
This script assume that a sequence of strings are provided via stdin,
and that the single command-line argument is a filename.
The filename referes to a file of strings.
Strings from stdin are passed to stdout if they are not found in the file.

The expected use to to pass randomly chosen topic names through stdin
and remove those found in the provided trending topics file. 
"""

trends = [line for line in open(sys.argv[1])]
for topic in sys.stdin:
    if topic not in trends:
        sys.stdout.write(topic)
    else:
        sys.stderr.write("removed " + topic) 
