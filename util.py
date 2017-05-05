"""Utility function to execute benchmark
"""

from optparse import OptionParser
from time import time as time


def run_benchmark(benchmark):
    parser = OptionParser()
    parser.add_option('-n',
            default=100,
            type=int,
            help='How many times to run the benchmark')
    opts, args = parser.parse_args()
    n = opts.n

    times = []
    for i in xrange(n):
        t_start = time()
        benchmark()
        t_end = time()
        times.append(t_end - t_start)

    for t in times:
        print t
