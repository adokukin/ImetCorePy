import time
import random
import sys
import argparse
import json

def eprint(*args, **kwargs):
    print(*args, file=sys.stderr, **kwargs, flush=True)

def report_progress(progress):
    # TODO: decorate additionally if methods use stderr too
    eprint('{:.2f}'.format(progress))

parser = argparse.ArgumentParser(prog='evaluator')
parser.add_argument('-a', '--algorithm', help='JSON parameters of an algorithm')
parser.add_argument('-f', '--folds', type=int, help='number of validation folds')
parser.add_argument('-d', '--data', help='dataset filename')
args = parser.parse_args()
print(args.data, flush=True)

algorithm = ''
if args.algorithm:
    algorithm = ' ({})'.format(json.loads(args.algorithm)['name'])

TOTAL = 10
for i in range(TOTAL):
    report_progress(i / TOTAL)
    time.sleep(.5)
    print('Method output: {} s remaining'.format(TOTAL - i) + algorithm, flush=True)
    time.sleep(.5)
report_progress(1)
