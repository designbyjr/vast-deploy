# 🎤 Secure Whisper ASR Service

A production-ready, self-contained Docker containerized Whisper ASR service with comprehensive security, monitoring, and WebSocket support.

## ✨ Features

- **🔐 Security First**: TLS encryption, authentication middleware, security headers
- **🏗️ Self-Contained**: Runs entirely in Docker with no external dependencies required
- **📡 WebSocket Support**: Real-time audio processing with secure WebSocket connections
- **📊 Monitoring**: Built-in analytics, health checks, and system metrics
- **🔄 Pub/Sub Integration**: Optional Redis/Upstash integration for distributed systems
- **🚀 Production Ready**: Proper logging, error handling, and resource management

## 🚀 Quick Start

### Prerequisites
- Docker installed and running
- Port 9443 available (or modify in docker-run.sh)

### 1. Clone and Navigate
```bash
git clone <repository-url>
cd whisper-asr-secure
```

### 2. Build and Run
```bash
# Build and start the service
./docker-run.sh run

# The service will be available at:
# https://localhost:9443
# API Documentation: https://localhost:9443/docs
```

### 3. Check Status
```bash
# View container status
./docker-run.sh status

# Follow logs
./docker-run.sh logs

# Check health
curl -k https://localhost:9443/health
```

## 🐳 Docker Management

Use the included `docker-run.sh` script for easy container management:

```bash
# Build the Docker image
./docker-run.sh build

# Run the container (builds if needed)
./docker-run.sh run

# Stop the container
./docker-run.sh stop

# View logs (follow mode)
./docker-run.sh logs

# Check container status
./docker-run.sh status

# Open shell in container
./docker-run.sh shell

# Restart container (rebuild + run)
./docker-run.sh restart

# Clean up (remove container and image)
./docker-run.sh clean
```

## 📋 API Endpoints

### Health & Monitoring
- `GET /health` - Simple health check
- `GET /health/detailed` - Detailed component status
- `GET /ready` - Kubernetes readiness probe
- `GET /live` - Kubernetes liveness probe
- `GET /metrics` - Service metrics (requires auth)
- `GET /status` - Overall service status (requires auth)

### WebSocket
- `WS /ws/{connection_id}` - Secure WebSocket endpoint

### ASR (Placeholder)
- `POST /asr/transcribe` - Audio transcription (requires auth)
- `GET /asr/models` - Available models (requires auth)

### Configuration
- `GET /config` - Service configuration (requires auth)
- `GET /config/validate` - Validate configuration (requires auth)

### Security
- `GET /tls/info` - TLS certificate information (requires auth)
- `POST /tls/renew` - Renew TLS certificate (requires auth)

## 🔧 Configuration

The service is configured via environment variables. Key settings:

```bash
# Security
TLS_ENABLED=true           # Enable HTTPS
TLS_AUTO_GENERATE=true     # Auto-generate self-signed certs
REDIS_AUTH_ENABLED=false   # Disable Redis auth for self-contained mode

# Service
HOST=0.0.0.0
PORT=9443
DEBUG=true                 # Enable debug mode for development

# WebSocket
WEBSOCKET_ENABLED=true
WEBSOCKET_MAX_CONNECTIONS=100

# Monitoring
ANALYTICS_ENABLED=true
METRICS_ENABLED=true
HEALTH_CHECK_INTERVAL=30
```

## 🏗️ Architecture

The service follows a modular architecture:

- **`app/main.py`** - FastAPI application with lifespan management
- **`app/config.py`** - Centralized configuration with validation
- **`app/middleware/auth.py`** - Authentication and authorization
- **`app/websocket/handler.py`** - WebSocket connection management
- **`app/utils/tls_manager.py`** - TLS certificate handling
- **`app/utils/redis_pubsub.py`** - Redis pub/sub integration
- **`app/monitoring/analytics.py`** - Metrics collection and monitoring
- **`app/health/checks.py`** - Health check system

## 🔐 Security Features

- **TLS Encryption**: Auto-generated self-signed certificates
- **Authentication**: Bearer token system with Redis backing
- **Security Headers**: HSTS, CSP, and security middleware
- **Non-root Container**: Runs as unprivileged user
- **Resource Limits**: Memory and CPU constraints
- **Security Options**: `no-new-privileges` and other hardening

## 📊 Monitoring

### Health Checks
- System resource monitoring (CPU, memory, disk)
- Component health (Redis, TLS, WebSocket)
- Service dependency checks
- Background health monitoring

### Metrics
- API request/response metrics
- WebSocket connection statistics
- System performance metrics
- Port and connection monitoring

### Logging
- Structured logging with multiple levels
- Container log aggregation
- Optional Redis pub/sub log shipping
- Health check event logging

## 🔗 WebSocket Usage

Connect to the WebSocket endpoint with authentication:

```javascript
// WebSocket connection with token
const ws = new WebSocket('wss://localhost:9443/ws/my-connection-id?token=YOUR_TOKEN');

// Or via Authorization header (if supported by client)
const ws = new WebSocket('wss://localhost:9443/ws/my-connection-id', [], {
    headers: {
        'Authorization': 'Bearer YOUR_TOKEN'
    }
});
```

## 🚨 Troubleshooting

### Container won't start
```bash
# Check container logs
./docker-run.sh logs

# Check container status
./docker-run.sh status

# Verify port availability
netstat -ln | grep 9443
```

### TLS Certificate Issues
The service auto-generates self-signed certificates. For production, replace with proper certificates:

```bash
# Check certificate info
curl -k https://localhost:9443/tls/info

# Manually replace certificates in ./certs/ directory
```

### Health Check Failures
```bash
# Test health endpoint
curl -k https://localhost:9443/health

# Check detailed health status
curl -k https://localhost:9443/health/detailed
```

## 📈 Performance

### Resource Requirements
- **Minimum**: 512MB RAM, 0.5 CPU cores
- **Recommended**: 2GB RAM, 1.0 CPU cores
- **Storage**: ~500MB for image + model cache

### Scaling
- Horizontal scaling via multiple containers
- Load balancer for HTTPS termination
- Redis cluster for distributed auth

## 🛠️ Development

### Local Development
```bash
# Install dependencies
pip install -r requirements.txt

# Run locally (without Docker)
python run.py

# Run tests (when implemented)
pytest
```

### Adding ASR Models
Uncomment Whisper dependencies in `requirements.txt`:
```bash
# Uncomment in requirements.txt:
torch==2.1.0
faster-whisper==0.9.0

# Rebuild container
./docker-run.sh restart
```

## 📝 License

This project is licensed under the MIT License.

## 🤝 Contributing

1. Fork the repository
2. Create your feature branch
3. Commit your changes
4. Push to the branch
5. Create a Pull Request

## 🆘 Support

For issues and questions:
1. Check the troubleshooting section
2. Review container logs: `./docker-run.sh logs`
3. Verify configuration: `curl -k https://localhost:9443/config`
4. Open an issue with detailed information