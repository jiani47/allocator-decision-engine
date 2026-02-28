#!/usr/bin/env bash
set -e

cd "$(dirname "$0")"

# Create venv if it doesn't exist
if [ ! -d ".venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv .venv
fi

# Activate venv
source .venv/bin/activate

# Install dependencies
echo "Installing dependencies..."
pip install -q -r requirements.txt

# Ensure project root is on Python path
export PYTHONPATH="$(pwd):${PYTHONPATH:-}"

# Run the app
echo ""
echo "Starting Equi..."
echo "Open http://localhost:8501 in your browser"
echo ""
streamlit run app/ui.py
