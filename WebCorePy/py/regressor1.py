# -*- coding: utf-8 -*-
# запусть лучше в анаконде, в SQL Server - старый scikit-learn
# C:\ProgramData\Anaconda3\python.exe
# C:\Program Files\Microsoft SQL Server\MSSQL14.MSSQLSERVER\PYTHON_SERVICES\python.exe
# D:\WWW\IMET\IMETCorePy\2019_realValue4AspNetCore\DataFiles

ext = ""
csvSep = ";"
folderPath = "" #"D:\\WWW\\IMET\\IMETCorePy\\2019_realValue4AspNetCore\\DataFiles"
# Путь к файлам с исходными данными
sfilePathTrainExcel = ""
sfilePathPredictExcel = ""
sfilePathPredictExcelResults = ""
filePathTrainExcel = "" # folderPath + "\\TrainingSet.xls"    # обучающая выборка
filePathPredictExcel = "" # folderPath + "\\Prediction.xls"    # данные для прогнозирования
filePathPredictExcelResults = "" # folderPath + "\\Prediction_Results.xls"    # результаты прогнозирования
# Путь к файлу с логами
logFilePath = "" # folderPath + "\\Log.txt"


# Инициализация случайного значения (для воспроизводимости результатов) RND_init = 42
RND_init = 45
sSplit = None
X=[]
y=[]
json_object = None
frameLearn=None
framePredict=None
methodScoreData=[]
r2score = None
timeout4Method = 15     # 15 секунд на выполнение метода


# Python code demonstrate how to create  
# Pandas DataFrame by lists of dicts. 
#import pandas as pd 
  
# Initialise data to lists. 
#data = [{'a': 1, 'b': 2, 'c':3}, {'a':10, 'b': 20, 'c': 30}] 
  
# Creates DataFrame. 
#df = pd.DataFrame(data) 
  
# Print the data 
#df 


# Uncomment this call when using matplotlib to generate images
# rather than displaying interactive UI.
#import matplotlib
#matplotlib.use('Agg')

import numbers
import numpy as np
import time
import sys
# [OPTIONAL] Seaborn makes plots nicer
import seaborn
import multiprocessing
import time
import json
import traceback

# вывод строки в файл и на экран
def write(input_text):
    print(input_text)
    # stdout is saved
    save_stdout = sys.stdout

    fh = open(logFilePath, "a") # "w" - перезаписывает, "a" - дописывает
    sys.stdout = fh
    print(input_text)

    # return to normal:
    sys.stdout = save_stdout
    fh.close()


# =====================================================================

# первый столбец содержит заголовок объекта, второй - целевая ф-ция (0 или 1), остальные - признаки
def read_data(filePathTrainExcel, filePathPredictExcel):
    global frameLearn, framePredict, sfilePathPredictExcel, csvSep
    '''
    Downloads the data for this script into a pandas DataFrame.
    '''
    if ext=="xls" or ext=="xlsx":
        from pandas import read_excel
        frameLearn = read_excel(
            filePathTrainExcel,
            header=0,       # заголовки в первой строке
            index_col=0,    # в первом столбце названия веществ (None если нет)
            # Uncomment if the file needs to be decompressed
        )
        if sfilePathPredictExcel!="":
            framePredict = read_excel(
                filePathPredictExcel,
                header=0,       # заголовки в первой строке
                index_col=0,    # в первом столбце названия веществ (None если нет)
                # Uncomment if the file needs to be decompressed
            )
    elif ext=="csv" or ext=="txt": 
        from pandas import read_csv
        frameLearn = read_csv(
            filePathTrainExcel,
            sep=csvSep,        # разделитель
            header=0,       # заголовки в первой строке
            index_col=0,    # в первом столбце названия веществ (None если нет)
            # Uncomment if the file needs to be decompressed
        )
        if sfilePathPredictExcel!="":
            framePredict = read_csv(
                filePathPredictExcel,
                sep=csvSep,     # разделитель
                header=0,       # заголовки в первой строке
                index_col=0,    # в первом столбце названия веществ (None если нет)
                # Uncomment if the file needs to be decompressed
            )
    else:
        raise NameError('Unsupported filetype: ' + ext)
    # Return the entire frames
    return (frameLearn, framePredict)


# =====================================================================

# получам данные для обучения и тестирования
def get_features_and_labels(frameLearn, framePredict):
    global sfilePathPredictExcel, X, y, sSplit   # разрешение на МОДИФИКАЦИЮ глобальной переменной
    # '''
    # Transforms and scales the input data and returns numpy arrays for
    # training and testing inputs and targets.
    # '''
    # Replace missing values with 0.0, or we can use
    # scikit-learn to calculate missing values (below)
    #frame[frame.isnull()] = 0.0
    # Convert values to floats
    arr1 = np.array(frameLearn, dtype=np.float)
    if sfilePathPredictExcel!="":
        arr2 = np.array(framePredict, dtype=np.float)
    else:
        arr2 = None

    # Первый столбец - целевой, все остальные - X
    X, y = arr1[:, 1:], arr1[:, 0]
    X_train = X
    y_train = y
    if sfilePathPredictExcel!="":
        X_predict, y_predictEMPTY = arr2[:, 1:], arr2[:, 0]
    else:
        X_predict = None
        y_predictEMPTY = None
    # Normalize the attribute values to mean=0 and variance=1
    from sklearn.preprocessing import StandardScaler
    scaler = StandardScaler()
    # To scale to a specified range, use MinMaxScaler
    #from sklearn.preprocessing import MinMaxScaler
    #scaler = MinMaxScaler(feature_range=(0, 1))
    
    # Fit the scaler based on the training data, then apply the same
    # scaling to both training and test sets.
    scaler.fit(X_train)
    X_train = scaler.transform(X_train)
    if sfilePathPredictExcel!="":
        X_predict = scaler.transform(X_predict)
    # Return the training and test sets
    return X_train, X_predict, y_train, y_predictEMPTY



# =====================================================================
def CrossValidation(classifier, classifierName, X_train, y_train, CVscMode):
    global writer
    from sklearn.model_selection import cross_val_score
    scores = cross_val_score(classifier, X_train, y_train, cv=5, scoring=CVscMode)        # scoring='f1_macro' - continuous is not supported        scoring='r2' (Dokukin)      'explained_variance'
    #write(classifierName+" Accuracy: %0.2f (+/- %0.2f)" % (scores.mean(), scores.std() * 2))
    return scores


# ==============================
# вынесли это сюда, чтобы запускать эту опасность в другом потоке с контролем по времени
def evaluateRegressor_FitScore(classifier, X_train, y_train):
    global r2score
    classifier.fit(X_train, y_train)
    r2score = classifier.score(X_train, y_train)


# =====================================================================
# X_learn, X_predict, y_learn, y_predict
def evaluateRegressor(classifier, classifierName, classifierMode, X_train, X_test, y_train, y_testEMPTY):
    global timeout4Method, frameLearn, framePredict, writer, methodScoreData, r2score
    '''
    Run multiple times with different classifiers to get an idea of the
    relative performance of each configuration.

    Returns a sequence of tuples containing:
        (title, precision, recall)
    for each learner.
    '''
    # We will calculate the P-R curve for each classifier
    from sklearn.metrics import precision_recall_curve, accuracy_score, roc_auc_score
    from sklearn.model_selection import cross_val_score
    # Test the linear support vector classifier
    start_time = time.time()    # засекли время начала
    # Fit the classifier
    repString = ""
    write("   " + time.strftime("%H:%M:%S", time.localtime()) + " Start evaluateRegressor(timeout=" + str(timeout4Method) + ") " + classifierName + "...")
    try:
        if timeout4Method<1:    # INPROCESS - Без защиты!
            evaluateRegressor_FitScore(classifier, X_train, y_train)
        else:
            p = multiprocessing.Process(target=evaluateRegressor_FitScore, args=(classifier, X_train, y_train))
            p.start()
            # Wait for 15 seconds or until process finishes
            p.join(timeout4Method)
            # If thread is still active
            if p.is_alive():
                write(classifierName + " is still running... let's kill it...")
                # Terminate - may not work if process is stuck for good
                p.terminate()
                # OR Kill - will work for sure, no chance for process to finish nicely however
                # p.kill()
                p.join()
                raise NameError(classifierName + " was killed, since took more than {0:.3f} seconds".format(timeout4Method))
            #else:
                #p.terminate()


        #evaluateRegressor_FitScore(classifier, X_train, y_train)
        #https://scikit-learn.org/stable/modules/model_evaluation.html
        CVscMode = 'explained_variance' #ARDRegression - лидер
        #CVscMode = 'r2'     # чуть хуже (ниже), чем 'explained_variance'
        #CVscMode = 'neg_mean_absolute_error'     # all is negative     -- НАДО
        #CVscMode = 'neg_mean_squared_error'     # all is negative       -- НАДО
        #CVscMode = 'neg_mean_squared_log_error'     # в половине алгоритмов ошибки при использовании 
        #CVscMode = 'neg_median_absolute_error'     # all is negative
        #scoresCV = CrossValidation(classifier, classifierName, X_train, y_train, CVscMode)
        scoresCV_EV = CrossValidation(classifier, classifierName, X_train, y_train, 'explained_variance')
        scoresCV_Abs = CrossValidation(classifier, classifierName, X_train, y_train, 'neg_mean_absolute_error')
        scoresCV_Sq = CrossValidation(classifier, classifierName, X_train, y_train, 'neg_mean_squared_error')

        if sfilePathPredictExcel!="":
            y_predict = classifier.predict(X_test) # предсказания
            if r2score>0.5:
                framePredict['a, A [' + classifierName+"_{0:.3f}".format(r2score)+']'] = y_predict
            else:
                framePredict['a, A [BAD_' + classifierName+"_{0:.3f}".format(r2score)+']'] = y_predict

        #write("BEGIN ======== " + classifierName + " (R2={0:.3f})".format(r2score) + " ========")
        # write("len(X_train)={}".format(len(X_train)))
        # write("len(X_test)={}".format(len(X_test)))

        #for i in range(len(y_predict)): 
        #    write("Правильное значение: {0:.3f}; спрогнозированное значение: {1:.3f}. Дельта: {2:.3f}".format(y_test[i], y_predict[i], abs(y_test[i]-y_predict[i])))
    except BaseException as err:
        r2score = -1
        repString = "ERROR: " + classifierName + " " + str(err) + " " + traceback.format_exc()

    elapsed_time = time.time() - start_time    # получаем длительность
    #repString = classifierName+' (r2score={0:.3f}, time={1:.2f})'.format(r2score, elapsed_time) + " CrossValid("+CVscMode+"): Accuracy: %0.2f (+/- %0.2f)" % (scoresCV.mean(), scoresCV.std() * 2)
    if repString=="":
        repString = classifierName+' (r2score={0:.3f}, time={1:.2f})'.format(r2score, elapsed_time) + " CrossValid(explained_variance): mean: %0.2f (std() * 2: +/- %0.2f)" % (scoresCV_EV.mean(), scoresCV_EV.std() * 2) + "; CrossValid(neg_mean_absolute_error): mean: %0.2f (std() * 2: +/- %0.2f)" % (scoresCV_Abs.mean(), scoresCV_Abs.std() * 2) + "; CrossValid(neg_mean_squared_error): mean: %0.2f (std() * 2: +/- %0.2f)" % (scoresCV_Sq.mean(), scoresCV_Sq.std() * 2)
        methodScoreData.append({'MethodName': classifierName, 'r2score': r2score,
            'CVExplainedVariance_mean': scoresCV_EV.mean(), 'CVExplainedVariance_std +/-': (scoresCV_EV.std() * 2),
            'CVNegMeanAbsoluteError_mean': scoresCV_Abs.mean(), 'CVNegMeanAbsoluteError_std +/-': (scoresCV_Abs.std() * 2),
            'CVNegMeanSquaredError_mean': scoresCV_Sq.mean(), 'CVNegMeanSquaredError_std +/-': (scoresCV_Sq.std() * 2),
            'time': elapsed_time, 'ErrorMessage': ''})
    else:
        methodScoreData.append({'MethodName': classifierName, 'r2score': r2score,
            'CVExplainedVariance_mean': None, 'CVExplainedVariance_std +/-': None,
            'CVNegMeanAbsoluteError_mean': None, 'CVNegMeanAbsoluteError_std +/-': None,
            'CVNegMeanSquaredError_mean': None, 'CVNegMeanSquaredError_std +/-': None,
            'time': elapsed_time, 'ErrorMessage': repString})

    write(repString)
    #write("END ======== " + classifierName + " ========")
    return repString, r2score, elapsed_time
# =====================================================================



# =====================================================================
# проверка классификатора
def procRegressor(classifier, classifierName, classifierMode, X_learn, X_predict, y_learn, y_predict, results):
    repString, scoreAcc, scoreAUC = evaluateRegressor(classifier, classifierName, classifierMode, X_train=X_learn, X_test=X_predict, y_train=y_learn, y_testEMPTY=y_predict)
    results.append((repString, scoreAcc, scoreAUC))


# проверка классификаторов из списка
def procAllRegressors(classifierList, X_learn, X_predict, y_learn, y_predict, results):
    for classifier, classifierName, classifierMode in classifierList:
        procRegressor(classifier, classifierName, classifierMode, X_learn=X_learn, X_predict=X_predict, y_learn=y_learn, y_predict=y_predict, results=results)

# =====================================================================


def readArgsJson():
    global json_object, timeout4Method, ext, folderPath, filePathTrainExcel, filePathPredictExcel, filePathPredictExcelResults, sfilePathTrainExcel, sfilePathPredictExcel, sfilePathPredictExcelResults, logFilePath
    #for idx, item in enumerate(sys.argv):
    #    write('Argument('+ str(idx) +') = ' + item)
    jsonFilePath = sys.argv[1]
    json_object = None
    with open(jsonFilePath, mode="r", encoding="utf-8") as content:
        json_object = json.load(content)

    folderPath = json_object["folderPath"] #sys.argv[1] #"D:\\MyProjects\\Python\\2019_realValue4AspNetCore\\DataFiles"
    # Путь к файлам с исходными данными
    sfilePathTrainExcel = json_object["fileTrain"] # sys.argv[2]
    sfilePathPredictExcel = json_object["filePredict"] # sys.argv[3] 
    timeout4Method = json_object["timeout4Method"] # 0
    #if len(sys.argv)>4:
    #    timeout4Method = int(sys.argv[4])

    import os.path
    ext = os.path.splitext(sfilePathTrainExcel)[1][1:].lower()

    #sfilePathPredictExcelResults = "result.xlsx"
    sfilePathPredictExcelResults = "result." + ext    # sys.argv[4]
    filePathTrainExcel = folderPath + "\\Upload\\" + sfilePathTrainExcel    # folderPath + "\\ "TrainingSet.xls"    # обучающая выборка
    filePathPredictExcel = folderPath + "\\Upload\\" + sfilePathPredictExcel # folderPath + "\\Prediction.xls"    # данные для прогнозирования
    filePathPredictExcelResults = folderPath + "\\Upload\\" + sfilePathPredictExcelResults # folderPath + "\\Prediction_Results.xls"    # результаты прогнозирования
    # Путь к файлу с логами
    # logFilePath = folderPath + "\\Upload\\" + sys.argv[5] # folderPath + "\\Log.txt"
    logFilePath = folderPath + "\\Upload\\log.txt"

    # write("sys.version = " + sys.version + "; sys.executable = " + sys.executable + "; ext = '" + ext + "'")
    
    global filePathSANDMethodParam
    sfilePathMethodParam = "sandRegressor_134spinel.txt"
    filePathSANDMethodParam = folderPath + "\\py\\" + sfilePathMethodParam

    #write("sys.version = " + sys.version + "; sys.executable = " + sys.executable)
    #write('Argument List (' + str(len(sys.argv)) + ' items):' + str(sys.argv))

    #write("1. folderPath = {}".format(folderPath))
    #write("2. filePathTrainExcel = {}".format(filePathTrainExcel))
    #write("3. filePathPredictExcel = {}".format(filePathPredictExcel))
    #write("4. filePathPredictExcelResults = {}".format(filePathPredictExcelResults))
    #write("5. logFilePath = {}".format(logFilePath))
    #write("6. filePathSANDMethodParam = {}".format(filePathSANDMethodParam))


# https://scikit-learn.org/stable/supervised_learning.html#supervised-learning
def GetClassifierList(X_learn):
    global json_object
    # 1.1.1. Ordinary Least Squares
    # 1.1.2. Ridge regression and classification
    # 1.1.3. Lasso
    # - 1.1.4. Multi-task Lasso = MultiTaskLasso - # ValueError: For mono-task outputs, use ElasticNet
    # 1.1.5. Elastic-Net
    # - 1.1.6. Multi-task Elastic-Net = MultiTaskElasticNet - # ValueError: For mono-task outputs, use ElasticNet
    # + 1.1.7. Least Angle Regression   # куча варнингов и бред в результатах # classifierList.append((linear_model.Lars(), "linear_model.Lars", "predictONLY"))    # ConvergenceWarning: Regressors in active set degenerate. Dropping a regressor, after 3 iterations, i.e. alpha=1.662e-02, with an active set of 3 regressors, and the smallest cholesky pivot element being 2.220e-16. Reduce max_iter or increase eps parameters.
    # 1.1.8. LARS Lasso
    # 1.1.9. Orthogonal Matching Pursuit (OMP)
    # 1.1.10.1. Bayesian Ridge Regression
    # 1.1.10.2. Automatic Relevance Determination - ARD
    # + 1.1.11. Logistic regression    # classifierList.append((linear_model.LogisticRegression(random_state=RND_init), "linear_model.LogisticRegression", "predict_proba")) # ValueError: Unknown label type: 'continuous'
    # + 1.1.12. Generalized Linear Regression - TweedieRegressor # на тест
    # + 1.1.13. Stochastic Gradient Descent - SGD - SGDRegressor # на тест # ValueError: Unknown label type:
    # + 1.1.14. Perceptron # на тест # ValueError: Unknown label type:
    # + 1.1.15. Passive Aggressive Algorithms # на тест 
    # + 1.1.16.2. RANSAC: RANdom SAmple Consensus# ValueError: min_samples may not be larger than number of samples X.shape[0].
    # 1.1.16.3. Theil-Sen estimator: generalized-median-based estimator
    # 1.1.16.4. Huber Regression
    # + 1.1.17. Quantile Regression
    from sklearn import linear_model
    from sklearn import discriminant_analysis
    # 1.3. Kernel ridge regression
    from sklearn.kernel_ridge import KernelRidge
    # + 1.4.2. Regression (1.4. Support Vector Machines): SVR, NuSVR and LinearSVR
    from sklearn import svm  #svm.SVR, svm.NuSVR, svm.LinearSVR
    # 1.5. Stochastic Gradient Descent => 1.1.13. Stochastic Gradient Descent
    # + 1.6.3. Nearest Neighbors Regression
    from sklearn import neighbors
    # + 1.7.1. Gaussian Process Regression (GPR)
    from sklearn.gaussian_process import GaussianProcessRegressor
    # + 1.8.3. PLSRegression
    from sklearn.cross_decomposition import PLSRegression
    # + 1.10. Decision Trees => 1.10.2. Regression
    from sklearn import tree
    # + 1.11.2.2. Extremely Randomized Trees
    # + 1.11.4. Gradient Tree Boosting
    # +++ПОДУМАТЬ 1.11.7. Voting Regressor
    from sklearn import ensemble
    # +++ПОДУМАТЬ 1.15. Isotonic regression
    from sklearn.cross_decomposition import PLSCanonical
    # 1.17.3. Neural network models (supervised) => Regression
    from sklearn import neural_network
    import sand3_09 as sand
    import fragment_r_03 as fragment

    # "predictONLY"   "predict_proba"   "decision_function"
    classifierList = []
    for algorithm in json_object["algorithms"]:
        classifier = None
        #print(f"   algorithm.name = {algorithm['name']}, algorithm.class = {algorithm['class']}")
        #print(f"classifier = {algorithm['class']}")
        #classifier = get_class("algorithm['class']")
        classifier = eval(algorithm['class'])
        #exec(f"classifier = {algorithm['class']}")
        #print(f"type(classifier) = {type(classifier).__name__}")
        for key, value in algorithm["settings"].items():
            #print(f" 0. {key} = {value}")
            #print('   typeof(value)=' + type(value).__name__)
            if type(value).__name__== 'str':
                exec(f'classifier.{key} = r"{value}"') # SyntaxError: EOL while scanning string literal
                #classifier.path = r'D:\MyProjects\Python\2019_realValue4AspNetCore\DataFiles\Upload\ '
                #exec(rf'classifier.{key} = """' + value + '"""') # добавление {}
                #exec(f'classifier.{key} = classifier.{key} + r"\"') # добавление {}
                #exec(f'classifier.%s = "%s"'%(key, value)) # добавление {}
                #exec(f'classifier.{key} = ''{value}''') # добавление {}
                #exec(f'classifier.{key} = list(''{value}'')[0]') # a bytes-like object is required, not 'str'
                #exec(f'classifier.{key} = \'{value}\'') # SyntaxError: EOL while scanning string literal
                #exec(r'classifier.{0} = "{1}"'.format(key, value)) # SyntaxError: EOL while scanning string literal
            else:
                exec(f'classifier.{key} = {value}')
            #print(f" 1. {key} = {value}")
        #print(f"classifier = {classifier}")
        classifierList.append((classifier, algorithm['name'], algorithm['mode']))
    #print("=== END LOOP ===")
    return classifierList


def procTask():
    readArgsJson()
    start_time = time.time()    # засекли время начала
    #for idx, item in enumerate(sys.argv):
    #    write('Argument('+ str(idx) +') = ' + item)

    write("BEGIN =================================================================")
    import sklearn as sk
    write('The scikit-learn version is {}.'.format(sk.__version__))
    write("0. timeout == {}".format(timeout4Method))
    write("1. Читаем данные из файла {} для обучения".format(sfilePathTrainExcel))
    if sfilePathPredictExcel!="":
        write("1b. Читаем данные из файла {} для прогнозирования".format(sfilePathPredictExcel))

    frameLearn, framePredict = read_data(filePathTrainExcel, filePathPredictExcel)
    elapsed_time = time.time() - start_time    # получаем длительность
    if sfilePathPredictExcel!="":
        write("2. Чтение выполнено за {0:.2f} сек. Обучаемся на объектах: {1} с {2} атрибутами. Прогнозируем объектов: {3}".format(elapsed_time, len(frameLearn.index), len(frameLearn.columns), len(framePredict.index)))
    else:
        framePredict=None
        write("2. Чтение выполнено за {0:.2f} сек. Обучаемся на объектах: {1} с {2} атрибутами.".format(elapsed_time, len(frameLearn.index), len(frameLearn.columns)))

    # Process data into feature and label arrays
    start_time = time.time()    # засекли время начала
    X_learn, X_predict, y_learn, y_predict = get_features_and_labels(frameLearn, framePredict)
    elapsed_time = time.time() - start_time    # получаем длительность
    if sfilePathPredictExcel!="":
        write("3. Отмасштабированы признаки и подготовлены выборки (обучение+прогнозирование) за {:.2f} сек.".format(elapsed_time))
    else:
        write("3. Отмасштабированы признаки и подготовлена выборка для обучения за {:.2f} сек.".format(elapsed_time))
    # write("Простые методы:")
    results = []

    classifierList = GetClassifierList(X_learn)

    procAllRegressors(classifierList=classifierList, X_learn=X_learn, X_predict=X_predict, y_learn=y_learn, y_predict=y_predict, results=results)
    
    # сохраним результат оценки классификаторов
    import pandas as pd 
    dfScore = pd.DataFrame(methodScoreData, columns = ['MethodName', 'r2score', 
'CVExplainedVariance_mean', 'CVExplainedVariance_std +/-',
'CVNegMeanAbsoluteError_mean', 'CVNegMeanAbsoluteError_std +/-',
'CVNegMeanSquaredError_mean', 'CVNegMeanSquaredError_std +/-',
'time', 'ErrorMessage']) 
    if ext=="xls" or ext=="xlsx":
        from pandas import ExcelWriter
        # сохраним результат
        writer = ExcelWriter(folderPath + "\\Upload\\resultScore." + ext)
        dfScore.to_excel(writer, 'Results')
        writer.save()
        write("4. Файл с результатами оценки алгоритмов сохранен: " + "resultScore." + ext)
    elif ext=="csv" or ext=="txt": 
        # framePredict.to_csv(filePathPredictExcelResults, sep=csvSep, encoding='utf-8')    # without BOM
        dfScore.to_csv(folderPath + "\\Upload\\resultScore." + ext, sep=csvSep, encoding='utf-8-sig')  # with BOM
        write("4. Файл с результатами оценки алгоритмов сохранен: " + "resultScore." + ext)
    else:
        raise NameError('Unsupported filetype: ' + ext)



    # сохраним результат прогнозирования
    if sfilePathPredictExcel!="":
        if ext=="xls" or ext=="xlsx":
            from pandas import ExcelWriter
            # сохраним результат прогнозирования
            writer = ExcelWriter(filePathPredictExcelResults)
            framePredict.to_excel(writer, 'Results')
            writer.save()
            write("5. Файл с результатами сохранен: " + sfilePathPredictExcelResults)
        elif ext=="csv" or ext=="txt": 
            # framePredict.to_csv(filePathPredictExcelResults, sep=csvSep, encoding='utf-8')    # without BOM
            framePredict.to_csv(filePathPredictExcelResults, sep=csvSep, encoding='utf-8-sig')  # with BOM
            write("5. Файл с результатами сохранен: " + sfilePathPredictExcelResults)
        else:
            raise NameError('Unsupported filetype: ' + ext)
    
    write("END =================================================================")



if __name__ == '__main__':
    procTask()
    quit()
