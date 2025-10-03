#!/bin/bash

# Vast.ai Secure Whisper ASR Service Entrypoint
# This script handles the startup process on Vast.ai infrastructure

set -e

echo "🎤 Starting Secure Whisper ASR Service on Vast.ai..."
echo "=" * 60

# Print environment info
echo "📁 Working directory: $(pwd)"
echo "🏠 Home directory: $HOME"
echo "👤 Current user: $(whoami)"
echo "🌐 Host: $HOST"
echo "🔌 Port: $PORT"
echo "🔐 TLS Enabled: $TLS_ENABLED"

# Export Vast.ai specific environment variables
export OPEN_BUTTON_PORT=${OPEN_BUTTON_PORT:-9443}
export JUPYTER_DIR=${JUPYTER_DIR:-/workspace}
export DATA_DIRECTORY=${DATA_DIRECTORY:-/workspace}

# Create necessary directories
mkdir -p ./certs ./logs ./temp
echo "📂 Created directories: certs, logs, temp"

# Export environment variables for shell sessions (Vast.ai requirement)
echo "📤 Exporting environment variables to /etc/environment..."
if [ -w /etc/environment ]; then
    env | grep _ >> /etc/environment || true
    echo "✅ Environment variables exported"
else
    echo "⚠️  Could not write to /etc/environment (permission denied)"
fi

# Check Python and dependencies
echo "🐍 Python version: $(python --version)"
echo "📦 Checking key dependencies..."
python -c "import fastapi, uvicorn, redis, aiohttp; print('✅ Core dependencies available')" || {
    echo "❌ Missing dependencies, installing..."
    pip install -r requirements.txt
}

# Print service configuration
echo "🔧 Service Configuration:"
echo "  - TLS: $TLS_ENABLED"
echo "  - Authentication: $REDIS_AUTH_ENABLED"
echo "  - WebSocket: $WEBSOCKET_ENABLED"
echo "  - Monitoring: $METRICS_ENABLED"
echo "  - Debug: $DEBUG"

# Print access information
echo "=" * 60
echo "🚀 Service starting on Vast.ai..."
echo "🌐 Access URLs:"
echo "  - Main Service: https://[instance-ip]:$OPEN_BUTTON_PORT"
echo "  - API Documentation: https://[instance-ip]:$OPEN_BUTTON_PORT/docs"
echo "  - Health Check: https://[instance-ip]:$OPEN_BUTTON_PORT/health"
echo "  - WebSocket: wss://[instance-ip]:$OPEN_BUTTON_PORT/ws/[connection-id]"
echo "=" * 60

# Handle signals for graceful shutdown
trap 'echo "🛑 Received shutdown signal, stopping service..."; exit 0' SIGTERM SIGINT

# Start the service
exec python run.py