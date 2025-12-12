#!python2
from __future__ import print_function

import pandas as pd
import numpy as np

from sklearn.ensemble import RandomForestRegressor
from sklearn.linear_model import ElasticNetCV
from sklearn.base import BaseEstimator, RegressorMixin

from sklearn.model_selection import train_test_split
from sklearn.model_selection import LeaveOneOut
from sklearn.model_selection import cross_val_predict

import inmc3

class DecorrelatedConvexForestRegressor(BaseEstimator, RegressorMixin):
    
    def __init__(self,
        forest_params = {
            'min_samples_leaf': 3,
            'n_estimators': 50
        },
        convex_combinations_params = {
            'n_combinations': 400,
            'generation_threshold': 0.99
        },
        elnet_params={
            'normalize':True,
            'max_iter':100000
        }):
        
        self.forest_params = forest_params
        self.convex_combinations_params = convex_combinations_params
        self.elnet_params = elnet_params
    
    def fit(self, X, y = None, debug = False):
        """
        X is inmc3.utils.Sample.X, y is inmc3.utils.Sample.y
        TODO: use BaseEstimator format
        """
        if debug:
            print('training')
        
        self.X = X
        self.y = y
        training_sample = inmc3.Sample(self.X, self.y)
        
        # forest stage
        if self.forest_params is not None:
            if debug:
                print('stage: forest')
            self.random_forest_regressor = RandomForestRegressor(**self.forest_params)
            self.random_forest_regressor.fit(training_sample.X, training_sample.y)
            forest_X = self.get_forest_sample(training_sample.X)
            training_sample = inmc3.Sample(forest_X, self.y)
        
        # convex combinations stage
        if self.convex_combinations_params is not None:
            if debug:
                print('stage: convex')
            assert 'generation_threshold' in self.convex_combinations_params
            assert 'n_combinations' in self.convex_combinations_params
            
            self.convex_trainer = inmc3.MaxCorrelationTrainer(
                generation_threshold=self.convex_combinations_params['generation_threshold'],
                parallel_profile='threads-4',
                skip_selection=False,
                decorrelation_type = self.convex_combinations_params['decorrelation_type'],
                decorrelated_num = self.convex_combinations_params['n_combinations']
            )
            self.decorrelated_combinations = self.convex_trainer.train(training_sample)
            
            convex_X = inmc3.trainer.FeatureGenerator.from_combinations(training_sample, training_sample, self.decorrelated_combinations)
            training_sample = inmc3.Sample(convex_X, self.y)
        
        # elastic net stage
        if self.elnet_params is not None:
            if debug:
                print('stage: elastic net')
            self.elastic_net_classifier = ElasticNetCV(**self.elnet_params)
            self.elastic_net_classifier.fit(training_sample.X, training_sample.y)
        
        return self
    
    def predict(self, X, y = None, debug = False):
        """
        X is inmc3.utils.Sample.X
        TODO: use BaseEstimator format
        """
        if debug:
            print('prediction')

        training_sample = inmc3.Sample(self.X, self.y)
        testing_sample = inmc3.Sample(X, np.array([0])) # second arg is a stub
        
        # forest stage
        if self.forest_params is not None:
            forest_X = self.get_forest_sample(training_sample.X)
            training_sample = inmc3.Sample(forest_X, self.y)
            
            forest_testing_X = self.get_forest_sample(testing_sample.X)
            result_y = self.random_forest_regressor.predict(testing_sample.X)
            testing_sample = inmc3.Sample(forest_testing_X, np.array([0]))
        
        # convex combinations stage
        if self.convex_combinations_params is not None:
            # TODO: convex_X is not needed for elastic net, but should be prepared if stages change
            convex_testing_X = inmc3.trainer.FeatureGenerator.from_combinations(training_sample, testing_sample, self.decorrelated_combinations)
            # TODO: perform prediction without elastic net here
            # TODO: return new features from the forecast method
            result_y = self.convex_trainer.forecast(training_sample, testing_sample, all_results=False)
            testing_sample = inmc3.Sample(convex_testing_X, np.array([0]))
        
        if self.elnet_params is not None:
            result_y = self.elastic_net_classifier.predict(testing_sample.X)

        return result_y
        
    def get_forest_sample(self, X):
        # make sure to call if self.random_forest_regressor is trained
        forest_dataframe = None
        
        for tree in self.random_forest_regressor.estimators_:
            res = tree.predict(X)
            if forest_dataframe is None:
                forest_dataframe = pd.DataFrame(res)
            else:
                forest_dataframe = pd.concat([forest_dataframe, pd.Series(res)], axis=1)
        
        return forest_dataframe.values
