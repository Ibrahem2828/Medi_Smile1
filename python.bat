@echo off
setlocal
set "VENV_PY=%~dp0venv\Scripts\python.exe"
if exist "%VENV_PY%" (
  "%VENV_PY%" %*
  exit /b %ERRORLEVEL%
)
echo Virtual environment not found at %VENV_PY%.
echo Please create the venv first.
exit /b 1
