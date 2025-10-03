# 🎤 Vast.ai Template Configuration

Use these exact settings in your Vast.ai template creation:

## Template Details

**Template Name:**
```
Secure Whisper ASR Service
```

**Template Description:**
```
Production-ready Whisper ASR service with TLS, WebSocket, monitoring, and GPU support
```

## Docker Repository And Environment

**Image Path:Tag:**
```
vastai/base-image:latest
```

**Version Tag:**
```
[Automatic]
```

## Environment Variables

Set these in the Environment Variables section:

| Variable Name | Value |
|---------------|--------|
| `OPEN_BUTTON_PORT` | `9443` |
| `OPEN_BUTTON_TOKEN` | `1` |
| `TLS_ENABLED` | `true` |
| `TLS_AUTO_GENERATE` | `true` |
| `REDIS_AUTH_ENABLED` | `false` |
| `DEBUG` | `true` |
| `JUPYTER_DIR` | `/workspace` |
| `DATA_DIRECTORY` | `/workspace` |
| `HOST` | `0.0.0.0` |
| `PORT` | `9443` |
| `WEBSOCKET_ENABLED` | `true` |
| `METRICS_ENABLED` | `true` |
| `ANALYTICS_ENABLED` | `true` |

## On-start Script

```bash
#!/bin/bash

# Vast.ai Provisioning Script for Secure Whisper ASR Service
set -e

echo "🚀 Starting Secure Whisper ASR Service on Vast.ai..."

# Set working directory
cd /workspace

# Clone repository
REPO_URL="https://github.com/designbyjr/vast-deploy.git"
PROJECT_DIR="/workspace/vast-deploy"

if [ -d "$PROJECT_DIR" ]; then
    echo "📁 Project exists, updating..."
    cd "$PROJECT_DIR"
    git pull
else
    echo "📥 Cloning repository..."
    git clone "$REPO_URL" "$PROJECT_DIR"
    cd "$PROJECT_DIR"
fi

# Install dependencies
echo "📦 Installing dependencies..."
pip install --no-cache-dir --upgrade pip
pip install --no-cache-dir -r requirements.txt

# Make scripts executable
chmod +x entrypoint.sh run.py docker-run.sh vastai-provision.sh

# Set environment variables
export OPEN_BUTTON_PORT=9443
export JUPYTER_DIR=/workspace
export DATA_DIRECTORY=/workspace

# Export to shell environment
env | grep _ >> /etc/environment || true

# Create directories
mkdir -p ./certs ./logs ./temp

echo "🎤 Starting Whisper ASR service..."
python run.py
```

## Docker Options

```bash
-p 9443:9443 -e OPEN_BUTTON_PORT=9443 -e OPEN_BUTTON_TOKEN=1
```

## Ports

Configure these port mappings:

| External Port | Internal Port | Protocol | Description |
|---------------|---------------|----------|-------------|
| `9443` | `9443` | TCP | HTTPS API & WebSocket |
| `8080` | `8080` | TCP | Optional HTTP redirect |

## Alternative: Using Provisioning Script URL

Instead of the inline on-start script, you can use:

**Provisioning Script URL:**
```
https://raw.githubusercontent.com/designbyjr/vast-deploy/main/vastai-provision.sh
```

## Quick Copy-Paste Values

For easy setup, here are the key values to copy:

### Environment Variables (as Docker options format):
```
-e OPEN_BUTTON_PORT=9443 -e OPEN_BUTTON_TOKEN=1 -e TLS_ENABLED=true -e REDIS_AUTH_ENABLED=false -e DEBUG=true -e JUPYTER_DIR=/workspace -e DATA_DIRECTORY=/workspace
```

### Port Mapping:
```
-p 9443:9443
```

### Image:
```
vastai/base-image:latest
```

### Provisioning Script URL:
```
https://raw.githubusercontent.com/designbyjr/vast-deploy/main/vastai-provision.sh
```

## Expected Behavior

Once deployed:
1. The "Open" button will connect to port 9443
2. Service accessible at `https://[instance-ip]:9443`
3. API documentation at `https://[instance-ip]:9443/docs`
4. Health check at `https://[instance-ip]:9443/health`
5. WebSocket endpoint at `wss://[instance-ip]:9443/ws/{connection_id}`

## Troubleshooting

If the service doesn't start:
1. Check the instance logs in Vast.ai console
2. Verify all environment variables are set
3. Ensure port 9443 is mapped correctly
4. Check that `OPEN_BUTTON_PORT=9443` is set