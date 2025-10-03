"""
Main FastAPI application for secure whisper ASR service.
Integrates all components: authentication, WebSockets, TLS, monitoring, and health checks.
"""

import asyncio
import logging
import uvicorn
from contextlib import asynccontextmanager
from fastapi import FastAPI, Depends, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request

from app.config import get_settings, validate_configuration
from app.middleware.auth import (
    AuthenticationMiddleware, 
    verify_token, 
    init_auth, 
    cleanup_auth
)
from app.websocket.handler import (
    SecureWebSocketHandler, 
    websocket_manager, 
    init_websocket_manager, 
    cleanup_websocket_manager
)
from app.utils.tls_manager import init_tls, cleanup_tls, tls_manager
from app.utils.redis_pubsub import init_redis_pubsub, cleanup_redis_pubsub, redis_pubsub
from app.monitoring.analytics import (
    metrics_collector, 
    MonitoringMiddleware, 
    init_monitoring, 
    cleanup_monitoring
)
from app.health.checks import health_manager, init_health_checks, cleanup_health_checks

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

settings = get_settings()
security = HTTPBearer()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager for startup and shutdown events."""
    logger.info("Starting Secure Whisper ASR Service...")
    
    try:
        # Initialize all components in order
        logger.info("Initializing TLS certificate system...")
        await init_tls()
        
        logger.info("Initializing authentication system...")
        await init_auth()
        
        logger.info("Initializing Redis pub/sub system...")
        await init_redis_pubsub()
        
        logger.info("Initializing WebSocket manager...")
        await init_websocket_manager()
        
        logger.info("Initializing monitoring system...")
        await init_monitoring()
        
        logger.info("Initializing health check system...")
        await init_health_checks()
        
        # Publish startup event
        if redis_pubsub.is_connected:
            await redis_pubsub.publish_system_event("service_fully_started", {
                "version": settings.APP_VERSION,
                "components": [
                    "tls", "authentication", "websockets", 
                    "monitoring", "health_checks", "redis_pubsub"
                ]
            })
        
        logger.info("✅ All components initialized successfully!")
        logger.info(f"🚀 Service ready on {'https' if settings.TLS_ENABLED else 'http'}://{settings.HOST}:{settings.PORT}")
        
        yield
        
    except Exception as e:
        logger.error(f"Failed to initialize service: {e}")
        raise
    
    finally:
        # Cleanup all components
        logger.info("Shutting down Secure Whisper ASR Service...")
        
        try:
            await cleanup_health_checks()
            await cleanup_monitoring()
            await cleanup_websocket_manager()
            await cleanup_redis_pubsub()
            await cleanup_auth()
            await cleanup_tls()
            
            logger.info("✅ Service shutdown complete")
            
        except Exception as e:
            logger.error(f"Error during service shutdown: {e}")


# Create FastAPI app with lifespan management
app = FastAPI(
    title="Secure Whisper ASR Service",
    description="Production-ready Whisper ASR with authentication, monitoring, and secure WebSocket support",
    version=settings.APP_VERSION,
    docs_url="/docs" if settings.DEBUG else None,
    redoc_url="/redoc" if settings.DEBUG else None,
    lifespan=lifespan
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.get_cors_origins(),
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["*"],
)

# Add monitoring middleware
app.add_middleware(MonitoringMiddleware)

# Add authentication middleware
app.add_middleware(AuthenticationMiddleware)


# === HEALTH ENDPOINTS ===

@app.get("/health", tags=["Health"])
async def health_simple():
    """Simple health check endpoint."""
    return health_manager.get_simple_health()


@app.get("/health/detailed", tags=["Health"])
async def health_detailed():
    """Detailed health check with all component status."""
    return await health_manager.run_all_checks()


@app.get("/ready", tags=["Health"])
async def readiness_check():
    """Kubernetes-style readiness check."""
    health_status = health_manager.get_simple_health()
    if health_status["healthy"]:
        return {"status": "ready"}
    else:
        raise HTTPException(status_code=503, detail="Service not ready")


@app.get("/live", tags=["Health"])
async def liveness_check():
    """Kubernetes-style liveness check."""
    return {"status": "alive", "timestamp": health_manager.last_check_time}


# === MONITORING ENDPOINTS ===

@app.get("/metrics", tags=["Monitoring"])
async def get_metrics(user_data: dict = Depends(verify_token)):
    """Get comprehensive service metrics."""
    return {
        "api_stats": metrics_collector.get_api_statistics(),
        "websocket_stats": metrics_collector.get_websocket_statistics(),
        "system_stats": metrics_collector.get_system_statistics(),
        "port_stats": metrics_collector.get_port_statistics()
    }


@app.get("/status", tags=["Monitoring"])
async def get_service_status(user_data: dict = Depends(verify_token)):
    """Get overall service status."""
    config_validation = validate_configuration()
    health_summary = health_manager.get_simple_health()
    ws_stats = await websocket_manager.get_connection_stats()
    
    return {
        "service": "whisper-asr-secure",
        "version": settings.APP_VERSION,
        "status": health_summary["status"],
        "uptime": health_summary.get("timestamp"),
        "configuration": {
            "valid": config_validation["valid"],
            "tls_enabled": settings.TLS_ENABLED,
            "websocket_enabled": settings.WEBSOCKET_ENABLED,
            "redis_enabled": settings.REDIS_AUTH_ENABLED,
            "monitoring_enabled": settings.METRICS_ENABLED
        },
        "connections": ws_stats,
        "components": {
            "authentication": "active" if settings.REDIS_AUTH_ENABLED else "disabled",
            "websockets": "active" if settings.WEBSOCKET_ENABLED else "disabled",
            "monitoring": "active" if settings.METRICS_ENABLED else "disabled",
            "tls": "active" if settings.TLS_ENABLED else "disabled"
        }
    }


# === WEBSOCKET ENDPOINTS ===

@app.websocket("/ws/{connection_id}")
async def websocket_endpoint(websocket: WebSocket, connection_id: str):
    """Secure WebSocket endpoint with authentication."""
    await SecureWebSocketHandler.handle_websocket_connection(
        websocket, connection_id
    )


# === ASR ENDPOINTS (Placeholder) ===

@app.post("/asr/transcribe", tags=["ASR"])
async def transcribe_audio(user_data: dict = Depends(verify_token)):
    """Transcribe audio using Whisper ASR."""
    # This is a placeholder for the actual ASR implementation
    # TODO: Integrate with actual Whisper models
    return {
        "status": "not_implemented",
        "message": "ASR transcription endpoint placeholder",
        "user": user_data.get("user_id"),
        "supported_formats": settings.get_upload_allowed_types(),
        "max_file_size": settings.MAX_FILE_SIZE
    }


@app.get("/asr/models", tags=["ASR"])
async def get_available_models(user_data: dict = Depends(verify_token)):
    """Get available ASR models."""
    return {
        "current_engine": settings.ASR_ENGINE,
        "current_model": settings.ASR_MODEL,
        "available_models": ["tiny", "base", "small", "medium", "large"],
        "device": settings.ASR_DEVICE,
        "quantization": settings.ASR_QUANTIZATION
    }


# === CONFIGURATION ENDPOINTS ===

@app.get("/config", tags=["Configuration"])
async def get_configuration(user_data: dict = Depends(verify_token)):
    """Get service configuration (sanitized)."""
    config_validation = validate_configuration()
    
    # Remove sensitive information
    safe_config = config_validation["config"].copy()
    if "redis" in safe_config:
        safe_config["redis"]["password"] = "***" if safe_config["redis"]["password"] else None
        safe_config["redis"]["url"] = safe_config["redis"]["url"][:20] + "..."
    
    return {
        "valid": config_validation["valid"],
        "errors": config_validation["errors"],
        "warnings": config_validation["warnings"],
        "config": safe_config
    }


@app.get("/config/validate", tags=["Configuration"])
async def validate_config(user_data: dict = Depends(verify_token)):
    """Validate current configuration."""
    return validate_configuration()


# === TLS CERTIFICATE ENDPOINTS ===

@app.get("/tls/info", tags=["Security"])
async def get_tls_info(user_data: dict = Depends(verify_token)):
    """Get TLS certificate information."""
    if not settings.TLS_ENABLED:
        return {"status": "disabled", "message": "TLS is disabled"}
    
    return await tls_manager.get_certificate_info()


@app.post("/tls/renew", tags=["Security"])
async def renew_tls_certificate(user_data: dict = Depends(verify_token)):
    """Renew TLS certificate."""
    if not settings.TLS_ENABLED:
        raise HTTPException(status_code=400, detail="TLS is disabled")
    
    success = await tls_manager.renew_certificate()
    if success:
        return {"status": "success", "message": "Certificate renewed successfully"}
    else:
        raise HTTPException(status_code=500, detail="Certificate renewal failed")


# === ERROR HANDLERS ===

@app.exception_handler(404)
async def not_found_handler(request: Request, exc):
    return JSONResponse(
        status_code=404,
        content={"detail": "Endpoint not found", "path": request.url.path}
    )


@app.exception_handler(500)
async def internal_error_handler(request: Request, exc):
    logger.error(f"Internal server error: {exc}")
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error", "timestamp": health_manager.last_check_time}
    )


if __name__ == "__main__":
    # Development server
    ssl_keyfile = settings.TLS_KEY_PATH if settings.TLS_ENABLED else None
    ssl_certfile = settings.TLS_CERT_PATH if settings.TLS_ENABLED else None
    
    uvicorn.run(
        "app.main:app",
        host=settings.HOST,
        port=settings.PORT,
        ssl_keyfile=ssl_keyfile,
        ssl_certfile=ssl_certfile,
        reload=settings.DEBUG,
        log_level=settings.LOGGING_LEVEL.lower(),
        workers=1  # Always use 1 worker for development
    )