# This Python file uses the following encoding: UTF-8

import numpy as np
import pandas as pd
import sys
import subprocess
from subprocess import PIPE, STDOUT
from ctypes import windll
from sklearn.base import BaseEstimator, RegressorMixin

# v 240221 ---------------------------------------------------------------

class FragmentRegressor(BaseEstimator, RegressorMixin):

    def __init__(self,
                 neighbors=1,  # 2,
                 min_crit_val=1,
                 path='',
                 exe='FragmOneAgainstAll.exe',
                 ):

        assert sys.platform.startswith("win"), 'Windows platform support only'
        self._encoding = 'cp{e}'.format(e=windll.kernel32.GetOEMCP())
        self._output_first_byte = str.encode('0', self._encoding)[0]

        # params
        self.neighbors = str(neighbors)
        self.min_crit_val = str(min_crit_val)

        self.exe = ('' if exe is None else exe)
        path = str(path).replace('/', '\\')
        self.path = path
        # path = str(path).replace('/', '\\')
        # self.path = path + ('' if exe is None else exe)
        self._full_path = path + ('' if exe is None else exe)
        self.obj_names_fea_name = 'n'
        self.targ_fea_name = '0'
        self.params = None
        self.lrn_data = None

    def fit(self, x, y):

        assert x.shape[0] == len(y)
        columns_count = x.shape[1]

        # create param data

        # param_dict = {
        #     u'Имя признака целевой функции:':	self.targ_fea_name,
        #     u'Номера признаков для построения модели:': '3	%d' % (columns_count + 2),
        #     u'Число классов': '2',
        #     u'Границы классов:': '0',
        #     u'Включение классов в построение правил:': '1	1',
        #     u'Автоматическое формирование весов объектов :': '0',
        #     u'Веса объектов в классе:': '60	1',
        #     u'Коэффициент квантования :':	'0',  #''0.25',
        #     u'Число квантилей :':	'0',  #'6',
        #     u'Макс число правил для пары классов :':	'60',  #'30',
        #     u'Mаксимальное число плоскостей в правиле:':	'1',  #'4',
        #     u'Использовать лучший признак в правиле только один раз:':	'0',
        #     u'Использовать все признаки только один раз:':	'0',
        #     u'Номер критерия:':	'2',
        #     u'Минимальное число состругиваемых объектов :':	16,  #'15',
        #     u'Максимальное число объектов другого класса при состругивании :':	'38',  #'7',
        #     u'Масимальная часть объектов другого класса :':	'0.1',  #'0',
        #     u'Останов по абсолютному числу оставшихся объектов :':	'1',
        #     u'абсолютное число оставшихся объектов для останова :':	'0',  #'1',
        #     u'часть оставшихся объектов для останова :':	'0'
        # }

        param_dict = {
            'Target :': self.targ_fea_name,
            'Feat_nums :':    '3	%d' % (columns_count + 2),
            'NClass :': '2',
            'Class_bou :': '0',
            'Incl_class :': '1	 1',
            'AutoWgh :': '0',
            'Weights :': '60	 1',
            'Epsil :': '0',
            'NQuant :': '0',  #'5',
            'NRules :': '60',  #'45',
            'NPlosk :': '1',  #'2',
            'BlokFirstFeat :': '0',
            'BlokAllFeat :': '0',
            'CriterNum :': '2',
            'MinSostr :': '16',  #'15',
            'MaxOther :': '38',  #'36',
            'MaxPartOther :': '0.1',  #'1',
            'StopAbs :': '1',
            'AbsNObj :': '0',
            'RestPartStop :': '0'
        }
        self.params = '\n'.join('\t'.join([e[0], str(e[1])]) for e in param_dict.items()) + '\n'

        # create lrn data
        self.lrn_data = (x, y)

        return self

    def predict(self, x):

        # run exe
        p = subprocess.Popen([self._full_path, self.neighbors, self.min_crit_val],
                              stdout=PIPE, stdin=PIPE, stderr=STDOUT)

        # prepare data to send
        input = '\n'.join([self.params,
                           pd.DataFrame(
                               data=np.concatenate((np.array([self.lrn_data[1]]).T, self.lrn_data[0]), axis=1)
                           ).to_csv(None,
                                    sep='\t',
                                    index_label=self.obj_names_fea_name),
                           pd.DataFrame(
                               data=np.concatenate((np.full((x.shape[0], 1), np.nan, dtype=x.dtype), x), axis=1)
                           ).to_csv(None,
                                    sep='\t',
                                    index_label=self.obj_names_fea_name)
                           ])

        # send request & receive result data
        b_output, b_err = p.communicate(str.encode(input))

        # raise exception if the result is not correct
        if len(b_output) == 0 or b_output[0] != self._output_first_byte:
            raise Exception('\n'.join(['{exe} module error.'.format(exe=self._full_path),
                                       b_err.decode(self._encoding) if b_err is not None else '',
                                       b_output.decode(self._encoding)]
                                      ))

        # get result
        res_lines = b_output.decode(self._encoding).strip('\r\n').split('\r\n')
        res = np.full((x.shape[0],), np.nan)
        assert res.shape[0] == len(res_lines)
        for i in range(res.shape[0]):
            res_val = res_lines[i].split('\t')[-1].strip()
            if len(res_val) > 0 and res_val != '*':
                res[i] = float(res_val)

        return res
