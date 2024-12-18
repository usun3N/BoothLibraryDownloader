@echo off
if exist ".venv\" goto AlreadyExist
echo %PATH% | findstr "Python" > NUL
if %errorlevel%==1 goto NoPython
echo "making venv..."
python -m venv .venv
echo "downloading requirements..."
"./.venv/Scripts/python.exe" -m pip install -r requirements.txt
echo "Finish"
goto end

:AlreadyExist
echo "venv is already exist"
goto end

:NoPython
echo "please install python first"
goto end

:end
pause
exit