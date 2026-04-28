@echo off
cd /d "%~dp0"
call venv\Scripts\activate.bat
python src\scraper_app.py
