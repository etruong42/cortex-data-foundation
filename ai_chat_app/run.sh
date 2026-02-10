#!/bin/bash
set -e

# Navigate to app directory
cd "$(dirname "$0")"

# Activate virtual environment
if [ ! -d ".venv" ]; then
    echo "Virtual environment not found. Please run 'python3 -m venv .venv && source .venv/bin/activate && pip install -r backend/requirements.txt' first."
    exit 1
fi

source .venv/bin/activate

# Check for API Key
if [ -z "$GEMINI_API_KEY" ]; then
    echo "WARNING: GEMINI_API_KEY environment variable is not set."
    echo "Please export GEMINI_API_KEY='your_api_key' before running this script."
    echo "Continuing anyway (might fail)..."
fi

# Run the server
echo "Starting AI Chat App on http://localhost:8000"
exec uvicorn backend.chat_service:app --host 0.0.0.0 --port 8000
