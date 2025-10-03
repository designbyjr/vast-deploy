"""
Authentication middleware for secure whisper ASR service.
Provides Redis-based bearer token validation for both HTTP and WebSocket connections.
"""

import json
import logging
from typing import Optional, Dict, Any, Tuple
from datetime import datetime, timezone

import redis.asyncio as aioredis
from fastapi import HTTPException, status, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response

from app.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


class RedisAuthManager:
    """Manages Redis connections and token validation operations."""
    
    def __init__(self):
        self.redis_pool: Optional[aioredis.ConnectionPool] = None
        self.redis_client: Optional[aioredis.Redis] = None
        
    async def initialize(self):
        """Initialize Redis connection pool."""
        if not settings.REDIS_AUTH_ENABLED:
            logger.warning("Redis authentication is disabled")
            return
            
        try:
            self.redis_pool = aioredis.ConnectionPool.from_url(
                settings.REDIS_URL,
                password=settings.REDIS_PASSWORD,
                db=settings.REDIS_TOKEN_DB,
                max_connections=settings.REDIS_MAX_CONNECTIONS,
                socket_timeout=settings.REDIS_TIMEOUT,
                health_check_interval=30,
                retry_on_timeout=True
            )
            
            self.redis_client = aioredis.Redis(
                connection_pool=self.redis_pool,
                decode_responses=True
            )
            
            # Test connection
            await self.redis_client.ping()
            logger.info("Redis authentication manager initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize Redis authentication: {e}")
            if settings.DEBUG:
                raise
            
    async def close(self):
        """Close Redis connections."""
        if self.redis_client:
            await self.redis_client.close()
        if self.redis_pool:
            await self.redis_pool.disconnect()
            
    async def validate_token(self, token: str) -> Tuple[bool, Optional[Dict[str, Any]]]:
        """
        Validate bearer token against Redis.
        
        Args:
            token: Bearer token to validate
            
        Returns:
            Tuple of (is_valid, user_data)
        """
        if not settings.REDIS_AUTH_ENABLED or not self.redis_client:
            logger.warning("Redis authentication disabled - allowing all requests")
            return True, {"user_id": "anonymous", "permissions": ["read", "write"]}
            
        try:
            # Check if token exists in Redis
            token_key = f"auth:token:{token}"
            token_data = await self.redis_client.get(token_key)
            
            if not token_data:
                logger.warning(f"Invalid token attempted: {token[:10]}...")
                return False, None
                
            # Parse token data
            user_data = json.loads(token_data)
            
            # Check token expiration
            if "expires_at" in user_data:
                expires_at = datetime.fromisoformat(user_data["expires_at"])
                if expires_at < datetime.now(timezone.utc):
                    logger.warning(f"Expired token attempted: {token[:10]}...")
                    # Remove expired token
                    await self.redis_client.delete(token_key)
                    return False, None
                    
            # Update last used timestamp
            user_data["last_used"] = datetime.now(timezone.utc).isoformat()
            await self.redis_client.setex(
                token_key, 
                settings.TOKEN_TTL if hasattr(settings, 'TOKEN_TTL') else 3600,
                json.dumps(user_data)
            )
            
            logger.debug(f"Valid token authenticated for user: {user_data.get('user_id', 'unknown')}")
            return True, user_data
            
        except json.JSONDecodeError as e:
            logger.error(f"Invalid JSON in token data: {e}")
            return False, None
        except Exception as e:
            logger.error(f"Redis token validation error: {e}")
            return False, None
    
    async def log_authentication_event(self, event_type: str, token: str, user_data: Optional[Dict] = None, 
                                     request_info: Optional[Dict] = None):
        """Log authentication events to Redis for monitoring."""
        if not self.redis_client:
            return
            
        try:
            event_data = {
                "type": event_type,
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "token_preview": token[:10] + "..." if token else None,
                "user_id": user_data.get("user_id") if user_data else None,
                "request_info": request_info or {}
            }
            
            # Publish to monitoring channel
            await self.redis_client.publish(
                "auth_events",
                json.dumps(event_data)
            )
            
            # Store in auth log (with retention)
            log_key = f"auth:log:{datetime.now().strftime('%Y%m%d')}"
            await self.redis_client.lpush(log_key, json.dumps(event_data))
            await self.redis_client.expire(log_key, 86400 * 7)  # 7 days retention
            
        except Exception as e:
            logger.error(f"Failed to log authentication event: {e}")


# Global auth manager instance
auth_manager = RedisAuthManager()

# HTTP Bearer security scheme
security = HTTPBearer(auto_error=False)


async def verify_token(credentials: Optional[HTTPAuthorizationCredentials] = None) -> Dict[str, Any]:
    """
    Verify bearer token and return user data.
    
    Args:
        credentials: HTTP authorization credentials
        
    Returns:
        User data dictionary
        
    Raises:
        HTTPException: If authentication fails
    """
    if not credentials:
        await auth_manager.log_authentication_event("missing_token", "")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing authentication token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    is_valid, user_data = await auth_manager.validate_token(credentials.credentials)
    
    if not is_valid:
        await auth_manager.log_authentication_event("invalid_token", credentials.credentials)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    await auth_manager.log_authentication_event("successful_auth", credentials.credentials, user_data)
    return user_data


class AuthenticationMiddleware(BaseHTTPMiddleware):
    """Middleware for handling authentication on all requests."""
    
    # Paths that don't require authentication
    PUBLIC_PATHS = {"/health", "/ready", "/live", "/docs", "/openapi.json", "/favicon.ico"}
    
    async def dispatch(self, request: Request, call_next) -> Response:
        """Process request through authentication middleware."""
        
        # Skip authentication for public paths
        if request.url.path in self.PUBLIC_PATHS:
            return await call_next(request)
            
        # Skip authentication for static assets
        if request.url.path.startswith("/assets/"):
            return await call_next(request)
        
        try:
            # Extract authorization header
            auth_header = request.headers.get("Authorization")
            if not auth_header or not auth_header.startswith("Bearer "):
                await auth_manager.log_authentication_event(
                    "missing_bearer_header",
                    "",
                    request_info={
                        "path": request.url.path,
                        "method": request.method,
                        "client_ip": request.client.host if request.client else None
                    }
                )
                return Response(
                    content='{"detail": "Missing or invalid authorization header"}',
                    status_code=401,
                    media_type="application/json",
                    headers={"WWW-Authenticate": "Bearer"}
                )
            
            # Extract token
            token = auth_header.split(" ", 1)[1]
            
            # Validate token
            is_valid, user_data = await auth_manager.validate_token(token)
            
            if not is_valid:
                await auth_manager.log_authentication_event(
                    "invalid_token_middleware",
                    token,
                    request_info={
                        "path": request.url.path,
                        "method": request.method,
                        "client_ip": request.client.host if request.client else None
                    }
                )
                return Response(
                    content='{"detail": "Invalid authentication token"}',
                    status_code=401,
                    media_type="application/json",
                    headers={"WWW-Authenticate": "Bearer"}
                )
            
            # Add user data to request state
            request.state.user = user_data
            request.state.authenticated = True
            
            await auth_manager.log_authentication_event(
                "middleware_success",
                token,
                user_data,
                request_info={
                    "path": request.url.path,
                    "method": request.method,
                    "client_ip": request.client.host if request.client else None
                }
            )
            
            response = await call_next(request)
            return response
            
        except Exception as e:
            logger.error(f"Authentication middleware error: {e}")
            return Response(
                content='{"detail": "Authentication service error"}',
                status_code=500,
                media_type="application/json"
            )


async def verify_websocket_auth(token: str) -> Tuple[bool, Optional[Dict[str, Any]]]:
    """
    Verify authentication for WebSocket connections.
    
    Args:
        token: Bearer token from WebSocket headers or query params
        
    Returns:
        Tuple of (is_valid, user_data)
    """
    if not token:
        await auth_manager.log_authentication_event("websocket_missing_token", "")
        return False, None
        
    is_valid, user_data = await auth_manager.validate_token(token)
    
    if not is_valid:
        await auth_manager.log_authentication_event("websocket_invalid_token", token)
        return False, None
        
    await auth_manager.log_authentication_event("websocket_auth_success", token, user_data)
    return True, user_data


# Startup and shutdown handlers
async def init_auth():
    """Initialize authentication system."""
    await auth_manager.initialize()


async def cleanup_auth():
    """Cleanup authentication system."""
    await auth_manager.close()