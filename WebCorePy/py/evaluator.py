import time
import random
import sys
import argparse
import json

from contextlib import redirect_stderr

import pandas as pd
from sklearn.model_selection import LeaveOneOut, KFold

def eprint(*args, **kwargs):
    print(*args, file=sys.stderr, **kwargs, flush=True)

def report_progress(progress):
    message = {'type': 'progress', 'progress': progress}
    eprint(json.dumps(message))

def report_results(results):
    message = dict(results, type = 'results')
    eprint(json.dumps(message))

def load_sample(filename):
  df = pd.read_excel(filename, index_col=0, header=0)
  
  target_idx = df.columns[0]
  features = df.drop([target_idx], axis=1)
  target = df[target_idx]

  return features.values, target.values

parser = argparse.ArgumentParser(prog='evaluator')
parser.add_argument('-a', '--algorithm', help='JSON parameters of an algorithm')
parser.add_argument('-f', '--folds', type=int, help='number of validation folds')
parser.add_argument('-d', '--data', help='dataset filename')
args = parser.parse_args()

# TODO: is parameters check needed here?
algorithm = json.loads(args.algorithm)
validator = LeaveOneOut() if args.folds == 0 else KFold(args.folds)

TOTAL = 10
for i in range(TOTAL):
    report_progress(i / TOTAL)
    time.sleep(.5)
    print('Method output: {} s remaining ({})'.format(TOTAL - i, algorithm['name']), flush=True)
    time.sleep(.5)
report_progress(1)
