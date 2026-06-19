#!/bin/bash
echo "============================================"
echo "  Cold Chain Weather Aggregation Service"
echo "============================================"
echo ""

if [ ! -d ".venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv .venv
fi

echo "Activating virtual environment..."
source .venv/bin/activate

echo "Installing dependencies..."
pip install -r requirements.txt

if [ ! -f ".env" ]; then
    echo "Copying .env.example to .env..."
    cp .env.example .env
    echo ""
    echo "NOTE: Please edit .env file to configure your API keys!"
fi

echo ""
echo "Starting server on http://localhost:8000 ..."
echo "API docs: http://localhost:8000/docs"
echo ""
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
