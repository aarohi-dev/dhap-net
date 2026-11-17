@echo off
echo Starting DHAP-NET API adapter...
echo Serving pre-computed pipeline outputs at http://localhost:8000
echo.
cd /d %~dp0..
python -m uvicorn backend.main:app --host 0.0.0.0 --port 8000 --reload
