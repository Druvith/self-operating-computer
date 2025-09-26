#!/bin/bash

# Start the virtual framebuffer in the background on display :99
# The -screen option configures a single screen with 1920x1080 resolution and 24-bit color
Xvfb :99 -screen 0 1920x1080x24 -ac & 

# Optional: Add a small delay to ensure the display and window manager are fully ready
sleep 2

# Set the DISPLAY environment variable for all subsequent commands
export DISPLAY=:99

# Generate a dummy .Xauthority file to satisfy pyautogui's requirement
xauth generate $DISPLAY . trusted

# Start the window manager in the background
fluxbox & 

# Start a terminal in the background
xterm & 

# Start the FastAPI application using uvicorn
# --host 0.0.0.0 makes it accessible from outside the container
echo "Starting FastAPI server..."
exec python3 -m uvicorn api.main:app --host 0.0.0.0 --port 8000
