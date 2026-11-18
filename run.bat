@echo off
python run.py --config build.json
if errorlevel 1 exit /b %errorlevel%
