import time
import random
import sys
import argparse
import json
import traceback
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

    return df, features.values, target.values

def validated_predict(model, X, y, validator, steps):
    result = np.zeros_like(y)
    
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

def forecast(model, tX, ty, fX, steps):
    with redirect_stderr(sys.stdout):
        scaler = StandardScaler().fit(tX)
        model.fit(scaler.transform(tX), ty)
    
    report_progress(round((steps - 1) / steps, 2))
    
    with redirect_stderr(sys.stdout):
        result = model.predict(scaler.transform(fX))

    report_progress(1.0)

    return result

def get_model(algorithm):
    package_name = algorithm['package']
    method_name = algorithm['name']
    parameters = algorithm['settings']

    module = import_module(package_name)
    model = getattr(module, method_name)(**parameters)
    return model

def extend_status(status, extension):
    if status is None:
        status = extension
    else:
        status += ',' + extension

parser = argparse.ArgumentParser(prog='evaluator')
parser.add_argument('-a', '--algorithm', help='JSON parameters of an algorithm')
parser.add_argument('-e', '--evaluate', type=int, help='number of validation folds, 0 - LOO, -1 - don\'t evaluate')
parser.add_argument('-t', '--train', help='training dataset filename')
parser.add_argument('-p', '--predict', help='predicting dataset filename')
args = parser.parse_args()

try:
    algorithm = json.loads(args.algorithm)
    # TODO: log with timestamps
    print('Processing method {}'.format(algorithm['name']), flush=True)

    results = {
        'folds': args.evaluate,
        'method': algorithm['name'],
        'r2': None,
        'mae': None,
        'mse': None,
        'time': None,
        'status': None,
        'results': None
    }

    model = get_model(algorithm)
    _, tX, ty = load_sample(args.train)
    print('Training sample \'{}\' loaded'.format(args.train), flush=True)

    if args.evaluate < 0:
        validator = None
        steps = 0
    else:
        if args.evaluate == 0:
            validator = LeaveOneOut()
            steps = tX.shape[0]
        else: 
            validator = KFold(args.evaluate)
            steps = args.evaluate

    if args.predict is not None:
        fdf, fX, fy = load_sample(args.predict)
        print('Predicting sample \'{}\' loaded'.format(args.predict), flush=True)
        steps += 2

    start = datetime.now()
    if validator is not None:
        predicted = validated_predict(model, tX, ty, validator, steps)
        results['r2'] = r2_score(ty, predicted)
        results['mae'] = mean_absolute_error(ty, predicted)
        results['mse'] = mean_squared_error(ty, predicted)
        results['time'] = (datetime.now() - start).total_seconds()
        results['status'] = extend_status(results['status'], 'ok')

    if args.predict is not None:
        forecasted = forecast(model, tX, ty, fX, steps)
        fdf[fdf.columns[0]] = forecasted
        filename = args.predict.rsplit('predicting', 1)[0] + 'results.xlsx'
        with pd.ExcelWriter(filename, engine='openpyxl', mode='a', if_sheet_exists="replace") as writer:  
            fdf.to_excel(writer, sheet_name=algorithm['name'])
        results['time'] = (datetime.now() - start).total_seconds()
        results['results'] = "{}[{}]".format(filename, algorithm['name'])
        results['status'] = extend_status(results['status'], 'ok')

except Exception as e:
    error = traceback.format_exc();
    print(error)
    results['time'] = (datetime.now() - start).total_seconds()
    results['status'] = extend_status(results['status'], str(e))

print(results, flush=True)
report_results(results)

report_progress(1)
