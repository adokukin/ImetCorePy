import time
import random
import sys
import argparse
import json

from contextlib import redirect_stderr

import pandas as pd
import numpy as np
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

def get_validator(folds = 0):
  if folds == 0:
    validator = LeaveOneOut()
  else:
    validator = KFold(n_splits = folds, shuffle = True) # TODO: random_state
  return validator

def validated_predict(model, X, y, folds=0):
    validator = get_validator(folds)
    result = np.zeros_like(y)
    steps = X.shape[0] if folds==0 else folds

    for step, (train_index, test_index) in enumerate(validator.split(X)):
        # TODO: print step info
        X_train, X_test = X[train_index], X[test_index]
        y_train, y_test = y[train_index], y[test_index]
    
        model.fit(X_train, y_train)
        result[test_index] = model.predict(X_test)

        report_progress(round((step + 1) / steps, 2))

    return result

def get_model(algorithm):
    pass

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
