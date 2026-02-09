#!/usr/bin/env bash

set -e

echo "Starting Drone Simulation Web App..."

# Start FastAPI backend
uvicorn api.main:app --host 0.0.0.0 --port 8000 --reload &
API_PID=$!

# Give backend time to start
sleep 2

# Start Streamlit frontend
streamlit run webapp/app.py &
WEB_PID=$!

echo "Backend running on http://localhost:8000"
echo "Web UI running on http://localhost:8501"
echo "Press Ctrl+C to stop."

# Wait until user interrupts
wait

# Cleanup on exit
echo "Stopping services..."
kill $API_PID $WEB_PID
