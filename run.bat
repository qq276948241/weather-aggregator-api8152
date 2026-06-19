@echo off
echo ============================================
echo   Cold Chain Weather Aggregation Service
echo ============================================
echo.

if not exist .venv (
    echo Creating virtual environment...
    python -m venv .venv
)

echo Activating virtual environment...
call .venv\Scripts\activate.bat

echo Installing dependencies...
pip install -r requirements.txt

if not exist .env (
    echo Copying .env.example to .env...
    copy .env.example .env
    echo.
    echo NOTE: Please edit .env file to configure your API keys!
)

echo.
echo Starting server on http://localhost:8000 ...
echo API docs: http://localhost:8000/docs
echo.
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
