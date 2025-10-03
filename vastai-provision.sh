#!/bin/bash

# Vast.ai Provisioning Script for Secure Whisper ASR Service
# This script sets up the service directly from GitHub repository

set -e

echo "🚀 Vast.ai Provisioning: Secure Whisper ASR Service"
echo "=" * 60

# Set working directory
cd /workspace

# Print environment info
echo "📁 Working directory: $(pwd)"
echo "🏠 Home directory: $HOME"
echo "👤 Current user: $(whoami)"
echo "🐍 Python version: $(python --version)"

# Clone repository
REPO_URL="https://github.com/designbyjr/vast-deploy.git"
PROJECT_DIR="/workspace/vast-deploy"

if [ -d "$PROJECT_DIR" ]; then
    echo "📁 Project directory exists, updating..."
    cd "$PROJECT_DIR"
    git pull
else
    echo "📥 Cloning repository..."
    git clone "$REPO_URL" "$PROJECT_DIR"
    cd "$PROJECT_DIR"
fi

echo "✅ Repository cloned/updated"

# Install Python dependencies
echo "📦 Installing Python dependencies..."
pip install --no-cache-dir --upgrade pip setuptools wheel
pip install --no-cache-dir -r requirements.txt
echo "✅ Dependencies installed"

# Make scripts executable
chmod +x entrypoint.sh run.py docker-run.sh
echo "✅ Scripts made executable"

# Create necessary directories
mkdir -p ./certs ./logs ./temp
echo "✅ Directories created"

# Set Vast.ai specific environment variables
export OPEN_BUTTON_PORT=${OPEN_BUTTON_PORT:-9443}
export OPEN_BUTTON_TOKEN=${OPEN_BUTTON_TOKEN:-1}
export JUPYTER_DIR=${JUPYTER_DIR:-/workspace}
export DATA_DIRECTORY=${DATA_DIRECTORY:-/workspace}
export TLS_ENABLED=${TLS_ENABLED:-true}
export REDIS_AUTH_ENABLED=${REDIS_AUTH_ENABLED:-false}
export DEBUG=${DEBUG:-true}
export HOST=${HOST:-0.0.0.0}
export PORT=${PORT:-9443}

# Export environment variables for shell sessions (Vast.ai requirement)
echo "📤 Exporting environment variables..."
if [ -w /etc/environment ]; then
    env | grep _ >> /etc/environment || true
    echo "✅ Environment variables exported to /etc/environment"
else
    echo "⚠️  Could not write to /etc/environment"
fi

# Print configuration
echo "🔧 Service Configuration:"
echo "  - Open Button Port: $OPEN_BUTTON_PORT"
echo "  - TLS Enabled: $TLS_ENABLED"
echo "  - Authentication: $REDIS_AUTH_ENABLED"
echo "  - Debug Mode: $DEBUG"
echo "  - Working Dir: $(pwd)"

# Print access information
echo "=" * 60
echo "🎤 Starting Secure Whisper ASR Service..."
echo "🌐 Access Information:"
echo "  - Vast.ai 'Open' Button: Will connect to port $OPEN_BUTTON_PORT"
echo "  - Direct URL: https://[instance-ip]:$PORT"
echo "  - API Docs: https://[instance-ip]:$PORT/docs"
echo "  - Health Check: https://[instance-ip]:$PORT/health"
echo "  - WebSocket: wss://[instance-ip]:$PORT/ws/[connection-id]"
echo "=" * 60

# Start the service
echo "🚀 Launching service..."
exec python run.py