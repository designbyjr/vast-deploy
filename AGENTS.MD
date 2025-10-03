# Secure Whisper ASR Service Architecture

## Overview
This project implements a secure, containerized version of the whisper-asr-webservice with enhanced security, authentication, monitoring, and Redis integration. The service provides speech-to-text capabilities through both REST API and WebSocket connections, all protected by bearer token authentication via Redis.

## Architecture Components

### 1. Base Service
- **Foundation**: Modified version of [whisper-asr-webservice](https://github.com/ahmetoner/whisper-asr-webservice/)
- **Framework**: FastAPI (Python) for both API endpoints and WebSocket handling
- **Core Functionality**: Speech-to-text processing using OpenAI Whisper model

### 2. Security Layer

#### Authentication Middleware
- **Redis Integration**: Bearer token verification against Upstash Redis instance
- **Scope**: Applies to both REST API calls and WebSocket connections
- **Implementation**: Custom FastAPI middleware with Redis token validation
- **Token Flow**: 
  1. Client sends Bearer token in Authorization header
  2. Middleware queries Redis for token validation
  3. Request proceeds only if token is valid and active

#### TLS/SSL Security
- **TLS-First Approach**: All connections must be TLS encrypted
- **Certificate Management**: Automated TLS certificate creation and renewal
- **WebSocket Security**: TLS-encrypted WebSocket connections (WSS)
- **Certificate Storage**: Secure certificate storage within container

### 3. WebSocket Implementation

#### Multi-threaded WebSocket Handler
- **Concurrency**: Multi-threaded WebSocket connection handling
- **Security**: TLS-only WebSocket connections (wss://)
- **Authentication**: Bearer token validation for WebSocket upgrades
- **Connection Management**: API-controlled WebSocket lifecycle
- **Default Connections**: Health check WebSockets created on startup

#### WebSocket Lifecycle
- **Startup**: Default WebSocket connections established for health monitoring
- **API Management**: New WebSocket connections created via REST API requests
- **Monitoring**: Active socket tracking and analytics
- **Cleanup**: Graceful connection termination and resource cleanup

### 4. Monitoring & Analytics

#### Real-time Monitoring
- **Active Connections**: Track all active WebSocket connections
- **Port Monitoring**: Monitor all active ports and services
- **API Call Tracking**: Log and analyze all REST API requests
- **Performance Metrics**: Response times, throughput, error rates

#### Logging System
- **Structured Logging**: JSON-formatted logs for easy parsing
- **Log Levels**: Configurable logging levels (DEBUG, INFO, WARN, ERROR)
- **Log Rotation**: Automated log file rotation and management
- **External Integration**: Logs forwarded to external monitoring systems

### 5. Redis Integration (Upstash)

#### Authentication Store
- **Token Validation**: Bearer tokens stored and validated in Redis
- **Session Management**: User session tracking and management
- **Token Expiration**: Automatic token expiration handling

#### Pub/Sub System
- **Log Publishing**: Real-time log events published to Redis channels
- **External Server Integration**: External server subscribes to log channels
- **Event Broadcasting**: System events and alerts broadcasted via pub/sub
- **Channel Structure**: Organized channel hierarchy for different event types

### 6. Health Check System

#### Comprehensive Health Monitoring
- **API Health**: REST API endpoint availability and response time checks
- **WebSocket Health**: Default WebSocket connection status monitoring
- **Service Dependencies**: Redis connectivity and service health checks
- **Startup Validation**: Complete system health validation on container startup

#### Health Check Endpoints
- **Basic Health**: `/health` - Simple alive check
- **Detailed Health**: `/health/detailed` - Comprehensive system status
- **Ready Check**: `/ready` - Service readiness for traffic
- **Live Check**: `/live` - Liveness probe for container orchestration

### 7. Container Architecture

#### Docker Configuration
- **Base Image**: Python 3.11 slim with security hardening
- **Multi-stage Build**: Optimized build process with minimal runtime image
- **Security**: Non-root user execution, minimal attack surface
- **Volume Mounts**: Separate volumes for certificates, logs, and temporary files

#### Network Security
- **Port Exposure**: Only necessary ports exposed (HTTPS/WSS)
- **Internal Communication**: Secure internal service communication
- **Network Isolation**: Container network isolation and segmentation
- **TLS Termination**: TLS termination at application level

### 8. Configuration Management

#### Environment Variables
- **Redis Configuration**: Upstash Redis connection parameters
- **TLS Settings**: Certificate paths and TLS configuration
- **Monitoring Settings**: Analytics and logging configuration
- **Service Settings**: API and WebSocket service parameters

#### Configuration Files
- **Service Config**: YAML-based service configuration
- **Logging Config**: Structured logging configuration
- **Security Config**: Security policy and authentication settings
- **Docker Config**: Container runtime configuration

## Development Notes

### Technology Stack
- **Backend**: FastAPI (Python 3.11+)
- **Authentication**: Redis (Upstash) with bearer tokens
- **Security**: TLS/SSL with automatic certificate management
- **Monitoring**: Custom analytics with Redis pub/sub integration
- **Containerization**: Docker with security hardening
- **WebSockets**: FastAPI WebSocket with multi-threading support

### Developer Context
- **Primary Developer**: PHP developer adapting to Python/FastAPI
- **Focus Areas**: Security-first design, comprehensive monitoring
- **External Dependencies**: Upstash Redis (requires configuration pause)
- **Deployment**: Docker-based with container orchestration support

## Implementation Phases

### Phase 1: Foundation Setup
1. Project structure creation
2. Base whisper-asr-webservice examination
3. Docker configuration setup
4. Basic FastAPI application structure

### Phase 2: Security Implementation
1. TLS certificate management system
2. Authentication middleware with Redis integration
3. Secure WebSocket handler implementation
4. Security hardening and testing

### Phase 3: Monitoring & Analytics
1. Analytics system implementation
2. Logging infrastructure setup
3. Health check system development
4. Performance monitoring integration

### Phase 4: Redis Integration (Requires Upstash Config)
1. **PAUSE POINT**: Upstash Redis configuration required
2. Authentication token management
3. Pub/sub system implementation
4. External server integration testing

### Phase 5: Final Integration
1. End-to-end testing and validation
2. Documentation completion
3. Deployment preparation
4. Security audit and validation

## Security Considerations

### Authentication & Authorization
- Bearer token validation on every request
- Token expiration and refresh mechanisms
- Secure token storage in Redis
- Rate limiting and abuse prevention

### Network Security
- TLS-only communication (no HTTP fallback)
- Certificate validation and management
- Secure WebSocket connections (WSS only)
- Network isolation and firewall rules

### Container Security
- Non-root container execution
- Minimal base image with security updates
- Read-only filesystem where possible
- Resource limits and constraints

### Data Security
- Secure handling of audio data
- Temporary file encryption and cleanup
- Secure logging without sensitive data exposure
- Memory-safe data processing

## Monitoring & Observability

### Metrics Collection
- Request/response metrics
- WebSocket connection metrics
- Authentication success/failure rates
- Resource utilization monitoring

### Alerting System
- Failed authentication alerts
- Service unavailability alerts
- Performance degradation warnings
- Security incident notifications

### Dashboard Integration
- Real-time service status
- Performance metrics visualization
- Security event tracking
- System health overview

---

**Note**: This architecture requires Upstash Redis configuration before full implementation of authentication and pub/sub features. The implementation will pause at the Redis integration phase to gather necessary connection details and API keys.