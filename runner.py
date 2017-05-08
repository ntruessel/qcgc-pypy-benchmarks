"""Benchmark runner
"""

from argparse import ArgumentParser
from datetime import datetime
import json
import subprocess

benchmarks = {
        'nbody': 'nbody.py',
        'splay': 'splay.py'
        }


def parse_args():
    parser = ArgumentParser()
    parser.add_argument('-n',
                        default=100,
                        type=int,
                        help='How many times to run each benchmark')
    parser.add_argument('interpreter',
                        help='Path to the python interpreter')
    return parser.parse_args()


def execute_benchmarks(interpreter, n):
    results = {}
    for b_name, b_file in benchmarks.items():
        results[b_name] = execute_benchmark(b_file, interpreter, n)
    return results


def execute_benchmark(b_file, interpreter, n):
    out = subprocess.check_output([interpreter, b_file, '-n', str(n)])
    return list(out.decode('utf-8').split())


def print_results(results):
    print(json.dumps({
        'date': datetime.now().isoformat(),
        'results': results
        }))


def main():
    args = parse_args()
    results = execute_benchmarks(args.interpreter, args.n)
    print_results(results)


if __name__ == "__main__":
    main()
