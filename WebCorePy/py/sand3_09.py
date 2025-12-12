#!/usr/bin/python2.7

import numpy as np
from sklearn.base import BaseEstimator, RegressorMixin

# ---------------------------------------------------------------


class SimpleSyndromeRegressor(BaseEstimator, RegressorMixin):

    def __init__(self,
                 min_features=1,            # min features count to include as symptom
                 max_features=None,         # max features count to include as symptom
                 min_sympt_on_count=1,      # min objects count, activated by symptom to corresponded feature include
                 max_sympt_on_count=1000,   # max objects count, activated by symptom to corresponded feature include
                 max_syndr_on_count=1000,  # 5,      # max allowed objects count, activated by syndrome while th choice process
                 min_syndr_on_count=2,  # 1,      # min required objects count, activated by syndrome while th choice process
                 target_interval=0.15,  # 0.05,      # part of feature values range as target interval
                 estimation='weighing',         # value estimation method ('mean', 'weighing')
                 min_syndr_low_th=1,        # min allowed syndrome threshold while th choice process
                 syndr_th=None,             # predefined syndrome (th_min, th_max), corresponded to lrn-objects for target value estimation (min_syndr_on_count, min_syndr_low_th ignored if not None)
                 targ_interval_find_method='range_part'     # symptom target interval defining method ('range_part', 'by_distribution')
                 ):

        # params
        self.min_features = min_features
        self.max_features = max_features
        self.max_syndr_on_count = max_syndr_on_count
        self.min_syndr_on_count = min_syndr_on_count
        self.min_sympt_on_count = min_sympt_on_count
        self.max_sympt_on_count = max_sympt_on_count
        self.target_interval = target_interval
        self.estimation = estimation
        self.syndr_th = syndr_th
        self.min_syndr_low_th = min_syndr_low_th
        self.targ_interval_find_method = targ_interval_find_method

        self.columns = None
        self.y = None
        self.sympt_columns = None
        self.sympt_left_th = None
        self.sympt_right_th = None
        self.sympt_interval_radius = None
        self.syndr_val = None                   # syndrome value for each lrn data object
        self.mov_average_columns = None

        # for save internal info
        self.save_internal_res_data = False     # save tmp internal data to future analysis
        self.res_sdr_val_th = None
        self.res_syndr_on_count = None
        self.res_syndr_vals = None
        self.res_nb_min = None
        self.res_nb_max = None

    def fit(self, x, y):

        assert x.shape[0] == len(y)

        # data columns prepare
        self.columns = np.transpose(x)
        self.y = y
        # self.columns[0][0] = np.nan

        columns_count = len(self.columns)
        obj_count = len(y)
        target_radius = x.dtype.type(self.target_interval / 2)

        self.sympt_columns = np.empty((columns_count, obj_count), dtype=np.bool_)
        self.sympt_left_th = np.empty(columns_count, dtype=x.dtype)
        self.sympt_right_th = np.empty(columns_count, dtype=x.dtype)
        self.syndr_val = np.empty(obj_count, dtype=np.uint32)
        self.symt_on_count = np.empty(columns_count, dtype=np.uint32)
        self.syndr_on = np.empty(obj_count, dtype=np.bool_)
        self.syndr_on_tmp = np.empty(obj_count, dtype=np.bool_)

        if self.targ_interval_find_method == 'range_part':
            # interval radius
            columns_min = np.fromiter((np.nanmin(column) for column in self.columns), x.dtype, count=columns_count)
            columns_max = np.fromiter((np.nanmax(column) for column in self.columns), x.dtype, count=columns_count)
            self.sympt_interval_radius = np.multiply(np.subtract(columns_max, columns_min), target_radius)
        elif self.targ_interval_find_method == 'by_distribution':
            # moving average
            self.mov_average_columns = np.empty(columns_count, dtype=object)
            win_len = self.target_interval
            for col_idx, column in enumerate(self.columns):
                column = np.sort(column[~np.isnan(column)])
                r_count = len(column)
                self.mov_average_columns[col_idx] = \
                    np.convolve(
                        np.insert(column,
                                  [0, r_count],
                                  [column[0] - (column[1] - column[0]), column[r_count - 1] + (column[r_count - 1] - column[r_count - 2])]),
                        np.ones((win_len,)) / win_len,
                        mode='valid')
        else:
            raise ValueError("targ_interval_find_method = '%s' not recognized" % self.targ_interval_find_method)

        return self

    def predict(self, x):

        columns_count = len(self.columns)
        lrn_obj_count = len(self.y)

        assert x.shape[1] == columns_count

        res = np.full(x.shape[0], np.nan, dtype=self.y.dtype)
        greater_equal_left = np.empty(self.y.shape[0], dtype=np.bool_)
        less_right = np.empty(self.y.shape[0], dtype=np.bool_)
        # syndr_on = np.empty(lrn_obj_count, dtype=np.bool_)

        if self.save_internal_res_data:
            self.res_sdr_val_th = np.empty(x.shape[0], dtype=np.uint32)
            self.res_syndr_on_count = np.empty(x.shape[0], dtype=np.uint32)
            self.res_syndr_vals = np.empty((x.shape[0], lrn_obj_count), dtype=np.uint32)
            self.res_nb_min = np.empty(x.shape[0], dtype=self.y.dtype)
            self.res_nb_max = np.empty(x.shape[0], dtype=self.y.dtype)

        for row_idx, row in enumerate(x):

            if self.targ_interval_find_method == 'range_part':
                np.subtract(row, self.sympt_interval_radius, out=self.sympt_left_th)
                np.add(row, self.sympt_interval_radius, out=self.sympt_right_th)
            elif self.targ_interval_find_method == 'by_distribution':
                win_len = self.target_interval
                for column_idx in range(0, columns_count):
                    if np.isnan(row[column_idx]):
                        self.sympt_left_th[column_idx] = np.nan
                        self.sympt_right_th[column_idx] = np.nan
                        continue
                    t_count = len(self.mov_average_columns[column_idx])
                    min_th_delta = self.mov_average_columns[column_idx][t_count - 1] - self.mov_average_columns[column_idx][0]
                    for l_i in range(0, t_count - win_len):
                        cur_th_delta = abs((row[column_idx] - self.mov_average_columns[column_idx][l_i]) - (self.mov_average_columns[column_idx][l_i + win_len - 1] - row[column_idx]))
                        if cur_th_delta < min_th_delta:
                            min_th_delta = cur_th_delta
                            self.sympt_left_th[column_idx] = self.mov_average_columns[column_idx][l_i]
                            self.sympt_right_th[column_idx] = self.mov_average_columns[column_idx][l_i + win_len - 1]

            for column_idx in range(0, columns_count):
                np.greater_equal(self.columns[column_idx], self.sympt_left_th[column_idx], out=greater_equal_left)
                np.less(self.columns[column_idx], self.sympt_right_th[column_idx], out=less_right)
                np.logical_and(greater_equal_left, less_right, out=self.sympt_columns[column_idx])
                self.symt_on_count[column_idx] = np.sum(self.sympt_columns[column_idx], dtype=np.uint32)

            sorted_features_idx = np.argsort(self.symt_on_count)

            # remove unconditioned features but save the required minimum
            i = 0
            while (i < columns_count
                   and self.symt_on_count[sorted_features_idx[i]] < self.min_sympt_on_count
                   and (columns_count - i) > self.min_features):
                i += 1
            j = i
            while (j < columns_count
                   and self.symt_on_count[sorted_features_idx[j]] <= self.max_sympt_on_count
                   or (j - i) < self.min_features):
                j += 1
            sorted_features_idx = sorted_features_idx[i:j]

            # get the best (with smaller activated symtoms)
            if self.max_features is not None and len(sorted_features_idx) > self.max_features:
                sorted_features_idx = sorted_features_idx[:self.max_features]

            for lrn_row_idx in range(0, lrn_obj_count):
                self.syndr_val[lrn_row_idx] = np.sum((self.sympt_columns[column_idx][lrn_row_idx] for column_idx in sorted_features_idx))

            if self.syndr_th is None:
                sdr_val_th = np.max(self.syndr_val)  # max_sdr_val
                # best syndrome th search
                syndr_on_count = 0
                while sdr_val_th >= self.min_syndr_low_th:
                    np.greater_equal(self.syndr_val, sdr_val_th, out=self.syndr_on)
                    syndr_on_count = np.sum(self.syndr_on)
                    if syndr_on_count >= self.min_syndr_on_count:
                        break
                    sdr_val_th -= 1
            else:
                # try to get objects with exactly defined th interval
                min_th = self.syndr_th[0]
                max_th = self.syndr_th[1]
                gr = np.greater_equal(self.syndr_val, min_th)
                ls = np.less_equal(self.syndr_val, max_th)
                # np.equal(self.syndr_val, self.syndr_th, out=self.syndr_on)
                np.logical_and(gr, ls, out=self.syndr_on)
                syndr_on_count = np.sum(self.syndr_on)
                sdr_val_th = -1  # self.syndr_th

            # save internal data
            if self.save_internal_res_data:
                self.res_sdr_val_th[row_idx] = sdr_val_th
                self.res_syndr_on_count[row_idx] = syndr_on_count
                self.res_syndr_vals[row_idx] = self.syndr_val
                self.res_nb_min[row_idx] = np.min(self.y[self.syndr_on])
                self.res_nb_max[row_idx] = np.max(self.y[self.syndr_on])

            if sdr_val_th == 0 or syndr_on_count == 0 or syndr_on_count > self.max_syndr_on_count:
                # recognition failure (nan value remais)
                continue

            # estimate value by target values of selected from lrn-data objects
            if self.estimation == 'mean':
                # v1 (simple mean)
                res[row_idx] = np.mean(self.y[self.syndr_on])
            elif self.estimation == 'weighing':  # 'distance':
                # v2 by weighing (fixed /former distances/)
                # SDR SUM instead the DIST  (weighted sum of squares)
                dist = np.empty(syndr_on_count, dtype=np.float32)
                np.multiply(self.syndr_val[self.syndr_on], self.syndr_val[self.syndr_on], out=dist)
                sum_dist = np.sum(dist)
                np.multiply(dist, self.y[self.syndr_on], out=dist)
                res[row_idx] = np.sum(dist) / sum_dist if sum_dist > 0 else np.mean(self.y[self.syndr_on])
            else:
                raise ValueError("estimation = '%s' not recognized" % self.estimation)

        return res
