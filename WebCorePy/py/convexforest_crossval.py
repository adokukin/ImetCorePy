#!python2
from __future__ import print_function

import pandas as pd
import numpy as np

from sklearn.model_selection import LeaveOneOut
from sklearn.metrics import r2_score

import inmc3
from convexforest import DecorrelatedConvexForestRegressor

# df = pd.read_excel('A(II)B(II)C(IV)O7/a/a_crossval_AB2C2O7.xls')
# target_idx = 'a'
# df = pd.read_excel('A(II)B(II)C(IV)O7/c/c_crossval_AB2C2O7.xls')
# target_idx = 'c'
# df = pd.read_excel('A(II)B(III)C(IV)O7/a/a_crossval_AIIB(IV)2CIII2O7.xls')
# target_idx = 'a'
df = pd.read_excel('A(II)B(III)C(IV)O7/c/c_crossval_AIIB(IV)2CIII2O7.xls')
target_idx = 'c'
sample = inmc3.Sample.from_pandas(df, target_idx)

# TODO: replace with library version
def leave_one_out_predict(sample, model):
    loo = LeaveOneOut()
    result = np.zeros(sample.y.shape)

    for train_index, test_index in loo.split(sample.X):
        print(test_index)
        X_train, X_test = sample.X[train_index], sample.X[test_index]
        y_train, y_test = sample.y[train_index], sample.y[test_index]
        model.fit(X_train, y_train)
        result[test_index] = model.predict(X_test)
        
    return result
    
forest_params = dict(min_samples_leaf=3, n_estimators=50, random_state=6)
convex_combinations_params_loop = dict(n_combinations=400, generation_threshold=0.999, decorrelation_type='loop')
convex_combinations_params_final = dict(n_combinations=400, generation_threshold=0.999, decorrelation_type='final')
elnet_params=dict(normalize=True, max_iter=100000, l1_ratio=0.4)

available_models = {
    'Forest': DecorrelatedConvexForestRegressor(
        forest_params = forest_params,
        convex_combinations_params = None,
        elnet_params = None),
    'Forest with elastic net': DecorrelatedConvexForestRegressor(
        forest_params = forest_params,
        convex_combinations_params = None,
        elnet_params = elnet_params),
    'Convex with loop reduction': DecorrelatedConvexForestRegressor(
        forest_params = None,
        convex_combinations_params = convex_combinations_params_loop,
        elnet_params = None),
    'Convex with final reduction': DecorrelatedConvexForestRegressor(
        forest_params = None,
        convex_combinations_params = convex_combinations_params_final,
        elnet_params = None),
    'Convex with loop reduction and elastic net': DecorrelatedConvexForestRegressor(
        forest_params = None,
        convex_combinations_params = convex_combinations_params_loop,
        elnet_params = elnet_params),
    'Convex forest with loop reduction and elastic net': DecorrelatedConvexForestRegressor(
        forest_params = forest_params,
        convex_combinations_params = convex_combinations_params_loop,
        elnet_params = elnet_params),
    'Convex forest with final reduction and elastic net': DecorrelatedConvexForestRegressor(
        forest_params = forest_params,
        convex_combinations_params = convex_combinations_params_final,
        elnet_params = elnet_params),
    'Elastic net': DecorrelatedConvexForestRegressor(
        forest_params = None,
        convex_combinations_params = None,
        elnet_params = elnet_params)
}

enabled_models = [
    'Forest',
    'Forest with elastic net',
    'Convex with loop reduction',
    'Convex with final reduction',
    'Convex with loop reduction and elastic net',
    'Convex forest with loop reduction and elastic net',
    'Convex forest with final reduction and elastic net',
    'Elastic net'
]

for key in enabled_models:
    result = leave_one_out_predict(sample, available_models[key])
    print('%s corr: %f' % (key, np.corrcoef(result, sample.y)[0,1]))
    print('%s r2sc: %f' % (key, r2_score(result, sample.y)))
    print('-----\r\n')

