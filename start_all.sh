#!/bin/bash

# Function to clean up background processes on exit
cleanup() {
    echo ""
    echo "Stopping all services..."
    # Kill all background jobs started by this script
    kill $(jobs -p) 2>/dev/null || true
    
    # Ensure the ports are actually freed (Next.js sometimes leaves zombie processes)
    echo "Ensuring ports are freed..."
    fuser -k 3000/tcp 2>/dev/null || true
    fuser -k 8000/tcp 2>/dev/null || true
    fuser -k 8501/tcp 2>/dev/null || true
    exit 0
}

# Trap Ctrl+C (SIGINT) and SIGTERM to run the cleanup function
trap cleanup SIGINT SIGTERM

echo "Cleaning up any lingering processes on ports 3000, 8000, 8501..."
fuser -k 3000/tcp 2>/dev/null || true
fuser -k 8000/tcp 2>/dev/null || true
fuser -k 8501/tcp 2>/dev/null || true

echo "Starting PostgreSQL database via Docker..."
docker compose up -d db

if [ ! -d "venv" ]; then
    echo "❌ Virtual environment not found. Please run ./setup_local.sh first to install dependencies."
    exit 1
fi

echo "Activating virtual environment..."
source venv/bin/activate

echo "Starting FastAPI backend (port 8000)..."
python api_server.py &
API_PID=$!

echo "Starting Next.js frontend (port 3000)..."
cd frontend
npm run dev &
NEXT_PID=$!
cd ..

echo "Starting Streamlit UI (port 8501)..."
streamlit run app.py --server.port=8501 --server.address=localhost &
STREAMLIT_PID=$!

echo ""
echo "==========================================================="
echo "✅ All services started! Logs will appear below."
echo "   Next.js Frontend: http://localhost:3000"
echo "   FastAPI Backend:  http://localhost:8000"
echo "   Streamlit App:    http://localhost:8501"
echo "==========================================================="
echo "Press Ctrl+C to stop all services cleanly."
echo ""

# Wait for all background jobs so the script doesn't exit immediately
wait $API_PID $NEXT_PID $STREAMLIT_PID
