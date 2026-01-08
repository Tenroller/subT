#!/bin/bash

# Function to handle cleanup on exit
cleanup() {
    echo ""
    echo "Shutting down..."
    kill $BACKEND_PID $FRONTEND_PID 2>/dev/null
    exit
}

trap cleanup SIGINT SIGTERM EXIT

# Start the Backend
echo "🚀 Starting backend..."
cd backend
# Check if venv exists to avoid interactive prompts
if [ ! -d ".venv" ]; then
    echo "Creating virtual environment..."
    uv venv
fi
source .venv/bin/activate
uvicorn main:app --reload --host 0.0.0.0 --port 8000 &
BACKEND_PID=$!

# Start the Frontend
echo "🚀 Starting frontend..."
cd ../frontend
npm run dev &
FRONTEND_PID=$!

echo "✅ Both services are starting..."
echo "Backend: http://localhost:8000"
echo "Frontend: Check output above for port (usually http://localhost:5173)"
echo "Press Ctrl+C to stop both."

wait
