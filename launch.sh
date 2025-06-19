#!/bin/bash

# Navigate to the script's directory (project root)
cd "$(dirname "$0")"

# Activate the Python virtual environment (assuming it's named 'venv')
# Check if the virtual environment directory exists before activating
if [ -d "venv" ]; then
    echo "Activating virtual environment..."
    source venv/bin/activate
else
    echo "Virtual environment 'venv' not found. Please run 'python -m venv venv' and 'pip install -r requirements.txt'."
    # Optionally exit or continue without venv
    # exit 1
fi

# Start the backend server in the background
echo "Starting backend server..."
uvicorn api:app --reload &

# Navigate to the frontend directory
echo "Navigating to frontend directory..."
cd frontend

# Start the frontend development server in the background
echo "Starting frontend development server..."
npm run dev &

# Add a small delay to allow servers to start
echo "Waiting for servers to start..."
sleep 10 # Adjust delay if needed

# Open the frontend URL in the default browser
echo "Opening application in browser..."
open http://localhost:5173/

echo "Launch script finished."
