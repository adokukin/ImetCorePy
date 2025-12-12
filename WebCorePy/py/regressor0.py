# -*- coding: utf-8 -*-
# запусть лучше в анаконде, в SQL Server - старый scikit-learn
# C:\ProgramData\Anaconda3\python.exe
# C:\Program Files\Microsoft SQL Server\MSSQL14.MSSQLSERVER\PYTHON_SERVICES\python.exe
# D:\MyProjects\Python\2019_realValue4AspNetCore\DataFiles

ext = ""
csvSep = ";"
folderPath = "" #"D:\\MyProjects\\Python\\2019_realValue4AspNetCore\\DataFiles"
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
frameLearn=None
framePredict=None
methodScoreData=[]


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


# =====================================================================
# X_learn, X_predict, y_learn, y_predict
def evaluateRegressor(classifier, classifierName, classifierMode, X_train, X_test, y_train, y_testEMPTY):
    global frameLearn, framePredict, writer, methodScoreData
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

    try:
        classifier.fit(X_train, y_train)
        r2score = classifier.score(X_train, y_train)
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
        repString = "ERROR: " + classifierName + str(err)

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
    #write("procRegressor = " + classifierName)
    repString, scoreAcc, scoreAUC = evaluateRegressor(classifier, classifierName, classifierMode, X_train=X_learn, X_test=X_predict, y_train=y_learn, y_testEMPTY=y_predict)
    results.append((repString, scoreAcc, scoreAUC))


# проверка классификаторов из списка
def procAllRegressors(classifierList, X_learn, X_predict, y_learn, y_predict, results):
    for classifier, classifierName, classifierMode in classifierList:
        procRegressor(classifier, classifierName, classifierMode, X_learn=X_learn, X_predict=X_predict, y_learn=y_learn, y_predict=y_predict, results=results)

# =====================================================================
def readArgs():
    global ext, folderPath, filePathTrainExcel, filePathPredictExcel, filePathPredictExcelResults, sfilePathTrainExcel, sfilePathPredictExcel, sfilePathPredictExcelResults, logFilePath
    #for idx, item in enumerate(sys.argv):
    #    write('Argument('+ str(idx) +') = ' + item)
    folderPath = sys.argv[1] #"D:\\MyProjects\\Python\\2019_realValue4AspNetCore\\DataFiles"
    # Путь к файлам с исходными данными
    sfilePathTrainExcel = sys.argv[2]
    sfilePathPredictExcel = sys.argv[3] 
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


def procTask():
    readArgs()
    start_time = time.time()    # засекли время начала
    write("BEGIN =================================================================")
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
    from sklearn import linear_model
    from sklearn import discriminant_analysis
    from sklearn.kernel_ridge import KernelRidge
    from sklearn.gaussian_process import GaussianProcessClassifier
    from sklearn.svm import LinearSVC
    from sklearn.svm import NuSVC
    from sklearn.neighbors import KNeighborsClassifier
    from sklearn import ensemble

    import sand3_05 as sand

    # "predictONLY"   "predict_proba"   "decision_function"

    classifierList = []
    
    classifierList.append((linear_model.LinearRegression(), "LinearRegression", "predictONLY"))  # NO random_state!!!
    classifierList.append((linear_model.Ridge(random_state=RND_init), "Ridge", "predictONLY"))

    classifierList.append((linear_model.Lasso(random_state=RND_init), "Lasso", "predictONLY"))
    
    #classifierList.append((linear_model.MultiTaskLasso(), "linear_model.MultiTaskLasso", "predictONLY"))     # ValueError: For mono-task outputs, use ElasticNet
    
    classifierList.append((linear_model.ElasticNet(max_iter=10000, random_state=RND_init), "ElasticNet", "predictONLY")) # ValueError: Can't handle mix of binary and continuous
    
    #classifierList.append((linear_model.MultiTaskElasticNet(), "linear_model.MultiTaskElasticNet", "predictONLY"))   # ValueError: For mono-task outputs, use ElasticNet
    
    # куча варнингов и бред в результатах
    # classifierList.append((linear_model.Lars(), "linear_model.Lars", "predictONLY"))    # ConvergenceWarning: Regressors in active set degenerate. Dropping a regressor, after 3 iterations, i.e. alpha=1.662e-02, with an active set of 3 regressors, and the smallest cholesky pivot element being 2.220e-16. Reduce max_iter or increase eps parameters.
    
    classifierList.append((linear_model.LassoLars(), "LassoLars", "predictONLY"))  # NO random_state!!!
    classifierList.append((linear_model.OrthogonalMatchingPursuit(), "OrthogonalMatchingPursuit", "predictONLY"))  # NO random_state!!!
    classifierList.append((linear_model.BayesianRidge(), "BayesianRidge", "predictONLY"))  # NO random_state!!!
    classifierList.append((linear_model.HuberRegressor(), "HuberRegressor", "predictONLY"))  # NO random_state!!!
    
    #classifierList.append((linear_model.RANSACRegressor(), "linear_model.RANSACRegressor", "predictONLY"))   # ValueError: min_samples may not be larger than number of samples X.shape[0].
    classifierList.append((linear_model.TheilSenRegressor(), "TheilSenRegressor", "predictONLY"))

    ### TODO : 1.1.16. Polynomial regression:
    #classifierList.append((discriminant_analysis.LinearDiscriminantAnalysis(), "discriminant_analysis.LinearDiscriminantAnalysis", "predict_proba")) # ValueError: Unknown label type: (array([8.0294, 8.4   , 8.2833, 8.25  , 8.1315, 8.0007, 7.8348, 8.1709, 8.1725, 8.635 , 8.1616, 7.419 , 8.0138, 8.108 ]),)
    #classifierList.append((discriminant_analysis.QuadraticDiscriminantAnalysis(), "discriminant_analysis.QuadraticDiscriminantAnalysis", "predict_proba")) # ValueError: Unknown label type: 'continuous'
    
    classifierList.append((KernelRidge(), "KernelRidge", "predictONLY"))  # NO random_state!!!
    from sklearn.cross_decomposition import PLSCanonical
    ### TODO ПРОВЕРИТЬ - вылетает при форматировании!!!
    # classifierList.append((PLSCanonical(), "PLSCanonical", "predictONLY"))  # TypeError: unsupported format string passed to numpy.ndarray.__format__
    
    from sklearn.cross_decomposition import PLSRegression
    ### TODO ПРОВЕРИТЬ - вылетает при форматировании!!!
    # classifierList.append((PLSRegression(), "PLSRegression", "predictONLY"))  # TypeError: unsupported format string passed to numpy.ndarray.__format__
    #classifierList.append((linear_model.SGDClassifier(random_state=RND_init), "linear_model.SGDClassifier", "decision_function"))   # ValueError: Unknown label type: (array([7.419 , 7.8348, 8.0007, 8.0138, 8.0294, 8.108 , 8.1315, 8.1616, 8.1709, 8.1725, 8.25  , 8.2833, 8.4   , 8.635 ]),)
    #classifierList.append((linear_model.Perceptron(random_state=RND_init), "linear_model.Perceptron", "decision_function")) # ValueError: Unknown label type: (array([7.419 , 7.8348, 8.0007, 8.0138, 8.0294, 8.108 , 8.1315, 8.1616, 8.1709, 8.1725, 8.25  , 8.2833, 8.4   , 8.635 ]),)
    #classifierList.append((linear_model.PassiveAggressiveClassifier(loss='hinge', random_state=RND_init), "linear_model.PassiveAggressiveClassifier(loss='hinge')", "decision_function")) # ValueError: Unknown label type: (array([7.419 , 7.8348, 8.0007, 8.0138, 8.0294, 8.108 , 8.1315, 8.1616, 8.1709, 8.1725, 8.25  , 8.2833, 8.4   , 8.635 ]),)
    #classifierList.append((linear_model.PassiveAggressiveClassifier(loss='squared_hinge', random_state=RND_init), "linear_model.PassiveAggressiveClassifier(loss='squared_hinge')", "decision_function")) # ValueError: Unknown label type: (array([7.419 , 7.8348, 8.0007, 8.0138, 8.0294, 8.108 , 8.1315, 8.1616, 8.1709, 8.1725, 8.25  , 8.2833, 8.4   , 8.635 ]),)
    #classifierList.append((LinearSVC(random_state=RND_init), "LinearSVC", "decision_function")) # ValueError: Unknown label type: 'continuous'
    #classifierList.append((NuSVC(nu=0.1, random_state=RND_init), "NuSVC(nu=0.1)", "decision_function")) # ValueError: Unknown label type: 'continuous'
    #classifierList.append((NuSVC(nu=0.3, random_state=RND_init), "NuSVC(nu=0.3)", "decision_function")) # ValueError: Unknown label type: 'continuous'
    
    classifierList.append((linear_model.ARDRegression(), "ARDRegression", "predictONLY")) # долго работает (50 сек)
    
    # classifierList.append((linear_model.LogisticRegression(random_state=RND_init), "linear_model.LogisticRegression", "predict_proba")) # ValueError: Unknown label type: 'continuous'
    #classifierList.append((GaussianProcessClassifier(random_state=RND_init), "GaussianProcessClassifier", "predict_proba")) # ValueError: Unknown label type: (array([8.0294, 8.4   , 8.2833, 8.25  , 8.1315, 8.0007, 7.8348, 8.1709, 8.1725, 8.635 , 8.1616, 7.419 , 8.0138, 8.108 ]),)
    from sklearn.naive_bayes import GaussianNB
    #classifierList.append((GaussianNB(), "GaussianNB (Gaussian Naive Bayes)", "predict_proba"))  # ValueError: Unknown label type: (array([7.419 , 7.8348, 8.0007, 8.0138, 8.0294, 8.108 , 8.1315, 8.1616, 8.1709, 8.1725, 8.25  , 8.2833, 8.4   , 8.635 ]),)
    from sklearn import tree
    # classifierList.append((tree.DecisionTreeClassifier(random_state=RND_init), "tree.DecisionTreeClassifier", "predict_proba")) # ValueError: Unknown label type: 'continuous'
    # classifierList.append((KNeighborsClassifier(n_neighbors=5), "KNeighborsClassifier(n_neighbors=5)", "predict_proba"))     # ValueError: Unknown label type: 'continuous'
    
    from sklearn import neural_network
    # classifierList.append((neural_network.MLPClassifier(random_state=RND_init), "neural_network.MLPClassifier", "predict_proba")) # ValueError: Unknown label type: (array([8.0294, 8.4   , 8.2833, 8.25  , 8.1315, 8.0007, 7.8348, 8.1709, 8.1725, 8.635 , 8.1616, 7.419 , 8.0138, 8.108 ]),)


    target_interval = 0.14
    min_syndr_on_count = 1  # 2
    fea_to_use = X_learn.shape[1]
    clf = sand.SimpleSyndromeRegressor(max_features=fea_to_use, #  - 5,
                                       min_sympt_on_count=2,  # 2,
                                       max_syndr_on_count=15,  # 5
                                       min_syndr_on_count=min_syndr_on_count,
                                       # estimation='distance',
                                       target_interval=target_interval)
    classifierList.append((clf, "SAND_SimpleSyndromeRegressor", "predictONLY"))


    procAllRegressors(classifierList=classifierList, X_learn=X_learn, X_predict=X_predict, y_learn=y_learn, y_predict=y_predict, results=results)
    
    # сохраним результат оценци классификаторов
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

