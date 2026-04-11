import time
import random
import sys
import argparse
import json
from datetime import datetime

from contextlib import redirect_stderr
from importlib import import_module

import pandas as pd
import numpy as np
from sklearn.preprocessing import StandardScaler
from sklearn.model_selection import LeaveOneOut, KFold
from sklearn.metrics import r2_score, mean_absolute_error, mean_squared_error

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
        print('Training step {} with {} objects'.format(step + 1, train_index.shape[0]), flush=True)
        X_train, X_test = X[train_index], X[test_index]
        y_train, y_test = y[train_index], y[test_index]
    
        with redirect_stderr(sys.stdout):
            scaler = StandardScaler().fit(X_train)
            model.fit(scaler.transform(X_train), y_train)
            result[test_index] = model.predict(scaler.transform(X_test))

        report_progress(round((step + 1) / steps, 2))

    return result

def get_model(algorithm):
    package_name = algorithm["package"]
    method_name = algorithm["name"]
    parameters = algorithm["settings"]

    module = import_module(package_name)
    model = getattr(module, method_name)(**parameters)
    return model

parser = argparse.ArgumentParser(prog='evaluator')
parser.add_argument('-a', '--algorithm', help='JSON parameters of an algorithm')
parser.add_argument('-f', '--folds', type=int, help='number of validation folds')
parser.add_argument('-d', '--data', help='dataset filename')
args = parser.parse_args()

try:
    algorithm = json.loads(args.algorithm)
    # TODO: log with timestamps
    print('Validating method {}'.format(algorithm['name']), flush=True)

    validator = LeaveOneOut() if args.folds == 0 else KFold(args.folds)

    model = get_model(algorithm)
    X, y = load_sample(args.data)
    print('Sample \'{}\' loaded'.format(args.data), flush=True)

    start = datetime.now()
    predicted = validated_predict(model, X, y, args.folds)

    results = {
        "folds": args.folds,
        "method": algorithm["name"],
        "r2": r2_score(y, predicted),
        "mae": mean_absolute_error(y, predicted),
        "mse": mean_squared_error(y, predicted),
        "time": (datetime.now() - start).total_seconds(),
        "status": "ok"
    }
except Exception as e:
    results = {
        "folds": args.folds,
        "method": algorithm["name"],
        "r2": None,
        "mae": None,
        "mse": None,
        "time": (datetime.now() - start).total_seconds() if 'start' in locals() else None,
        "status": str(e)
    }

print(results, flush=True)
report_results(results)

report_progress(1)
