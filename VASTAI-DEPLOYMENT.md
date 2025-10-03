# 🚀 Vast.ai Deployment Guide

Deploy the Secure Whisper ASR Service on Vast.ai GPU cloud platform.

## 📋 Quick Setup

### 1. Prepare Docker Image

You have two options for the Docker image:

#### Option A: Use Vast.ai Optimized Dockerfile
```bash
# Build using the Vast.ai specific Dockerfile
docker build -f Dockerfile.vastai -t your-username/whisper-asr-secure:vastai .
docker push your-username/whisper-asr-secure:vastai
```

#### Option B: Use GitHub Raw Files (Recommended)
Use the GitHub repository directly in Vast.ai template configuration.

### 2. Vast.ai Template Configuration

Use these settings in your Vast.ai template:

#### **Template Name**
```
Secure Whisper ASR Service
```

#### **Template Description**
```
Production-ready Whisper ASR service with TLS, WebSocket, and monitoring
```

#### **Docker Repository And Environment**
- **Image Path:Tag**: `your-username/whisper-asr-secure:vastai` (or GitHub URL)
- **Version Tag**: `[Automatic]`

#### **Docker Options**
```bash
-p 9443:9443 -p 8080:8080 -e OPEN_BUTTON_PORT=9443 -e OPEN_BUTTON_TOKEN=1 -e TLS_ENABLED=true -e REDIS_AUTH_ENABLED=false -e DEBUG=true -e JUPYTER_DIR=/workspace -e DATA_DIRECTORY=/workspace
```

#### **Environment Variables**

Configure these in the Vast.ai environment variables section:

| Variable | Value | Description |
|----------|-------|-------------|
| `OPEN_BUTTON_PORT` | `9443` | Port for the "Open" button in Vast.ai panel |
| `OPEN_BUTTON_TOKEN` | `1` | Enable open button |
| `TLS_ENABLED` | `true` | Enable HTTPS (recommended) |
| `TLS_AUTO_GENERATE` | `true` | Auto-generate SSL certificates |
| `REDIS_AUTH_ENABLED` | `false` | Disable Redis auth for self-contained mode |
| `DEBUG` | `true` | Enable debug mode |
| `JUPYTER_DIR` | `/workspace` | Jupyter directory (Vast.ai standard) |
| `DATA_DIRECTORY` | `/workspace` | Data directory |
| `HOST` | `0.0.0.0` | Bind to all interfaces |
| `PORT` | `9443` | Service port |
| `WEBSOCKET_ENABLED` | `true` | Enable WebSocket support |
| `METRICS_ENABLED` | `true` | Enable monitoring |
| `ANALYTICS_ENABLED` | `true` | Enable analytics |

#### **On-start Script**
```bash
entrypoint.sh
```

#### **Ports**
- **External Port**: `9443` → **Internal Port**: `9443` (HTTPS API)
- **External Port**: `8080` → **Internal Port**: `8080` (Optional HTTP redirect)

## 🐳 GitHub-based Deployment (Alternative)

If you want to deploy directly from GitHub without building a custom Docker image:

#### **Provisioning Script URL**
```
https://raw.githubusercontent.com/designbyjr/vast-deploy/main/vastai-provision.sh
```

Create this script:

```bash
#!/bin/bash
# vastai-provision.sh

# Clone repository
git clone https://github.com/designbyjr/vast-deploy.git /workspace/vast-deploy
cd /workspace/vast-deploy

# Install dependencies
pip install -r requirements.txt

# Make scripts executable
chmod +x entrypoint.sh run.py

# Set environment variables for Vast.ai
export OPEN_BUTTON_PORT=9443
export JUPYTER_DIR=/workspace
export DATA_DIRECTORY=/workspace

# Start the service
./entrypoint.sh
```

## 🌐 Access Your Service

Once deployed on Vast.ai:

1. **Via Vast.ai Panel**: Click the "Open" button (port 9443)
2. **Direct Access**: `https://[instance-ip]:9443`
3. **API Documentation**: `https://[instance-ip]:9443/docs`
4. **Health Check**: `https://[instance-ip]:9443/health`

## 🔧 Configuration Options

### SSL/TLS Configuration
```bash
# Enable TLS (recommended for production)
TLS_ENABLED=true
TLS_AUTO_GENERATE=true

# Or disable for development
TLS_ENABLED=false
```

### Authentication Configuration
```bash
# Self-contained mode (no external Redis)
REDIS_AUTH_ENABLED=false

# Or enable with external Redis
REDIS_AUTH_ENABLED=true
REDIS_URL=redis://your-redis-host:6379
REDIS_PASSWORD=your-password
```

### WebSocket Configuration
```bash
WEBSOCKET_ENABLED=true
WEBSOCKET_MAX_CONNECTIONS=100
```

### Monitoring Configuration
```bash
METRICS_ENABLED=true
ANALYTICS_ENABLED=true
HEALTH_CHECK_INTERVAL=30
```

## 🚨 Troubleshooting

### Service Won't Start
1. Check the container logs in Vast.ai console
2. Verify port 9443 is exposed correctly
3. Check environment variables are set properly

### Can't Access Service
1. Ensure `OPEN_BUTTON_PORT=9443` is set
2. Verify the port mapping `-p 9443:9443`
3. Check if TLS certificates generated successfully

### Performance Issues
1. Select appropriate GPU instance size
2. Monitor system resources via `/metrics` endpoint
3. Check health status via `/health/detailed` endpoint

## 🔒 Security Considerations

### For Development
- TLS enabled with self-signed certificates
- Authentication disabled for simplicity
- Debug mode enabled

### For Production
- Use proper SSL certificates
- Enable Redis authentication
- Set strong passwords
- Disable debug mode
- Configure proper CORS origins

## 📊 Monitoring

The service includes built-in monitoring:

- **Health Checks**: `/health`, `/health/detailed`
- **Metrics**: `/metrics` (authentication required in production)
- **System Status**: `/status`
- **Real-time WebSocket**: `/ws/{connection_id}`

## 🎯 Example Vast.ai Template

Complete template configuration:

```yaml
Template Name: Secure Whisper ASR Service
Description: Production-ready Whisper ASR with TLS, WebSocket, and monitoring

Docker Image: vastai/base-image:latest
On-start Script: entrypoint.sh

Environment Variables:
  OPEN_BUTTON_PORT: 9443
  OPEN_BUTTON_TOKEN: 1
  TLS_ENABLED: true
  REDIS_AUTH_ENABLED: false
  DEBUG: true
  JUPYTER_DIR: /workspace
  DATA_DIRECTORY: /workspace

Docker Options: -p 9443:9443 -e OPEN_BUTTON_PORT=9443

Provisioning Script: https://raw.githubusercontent.com/designbyjr/vast-deploy/main/vastai-provision.sh
```

## 🆘 Support

For Vast.ai specific issues:
1. Check Vast.ai documentation: https://docs.vast.ai
2. Review instance logs in the Vast.ai console
3. Test locally first with Docker before deploying
4. Use the health endpoints to diagnose issues