del "D:\WWW\IMET\IMETCorePy\WebCorePy\wwwroot\Upload\log.txt" 2>NUL
del "D:\WWW\IMET\IMETCorePy\WebCorePy\wwwroot\Upload\result.xls" 2>NUL
set PATH=C:\ProgramData\Anaconda3\Scripts;C:\ProgramData\Anaconda3;%PATH%
set root=C:\ProgramData\Anaconda3
call %root%\Scripts\activate base
%root%\python.exe "D:\WWW\IMET\IMETCorePy\WebCorePy\wwwroot\py\regressor.py" "D:\WWW\IMET\IMETCorePy\WebCorePy\wwwroot\Upload" "TrainingSet.xls" "Prediction.xls" "result.xls" "log.txt"
call %root%\Scripts\deactivate.bat