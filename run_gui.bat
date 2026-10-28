@echo off
setlocal
cd /d "%~dp0"

py -3 --version >nul 2>&1
if not errorlevel 1 goto use_py
python --version >nul 2>&1
if not errorlevel 1 goto use_python
if exist "%USERPROFILE%\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe" goto use_bundled_python
echo Python was not found. Install Python 3.10 or later with Tkinter and try again.
pause
exit /b 1

:use_py
py -3 gui.py
goto finish

:use_python
python gui.py
goto finish

:use_bundled_python
"%USERPROFILE%\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe" gui.py

:finish
if not errorlevel 1 exit /b 0
echo The interface could not start. Confirm that Python includes Tkinter.
pause
exit /b 1
