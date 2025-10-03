"""
Redis pub/sub integration for secure whisper ASR service.
Handles logging events and system notifications via Upstash Redis.
"""

import asyncio
import json
import logging
from typing import Dict, Any, Optional, Callable, List
from datetime import datetime, timezone
import aiohttp
from upstash_redis.asyncio import Redis

from app.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


class UpstashRedisPubSub:
    """Redis pub/sub client for Upstash using REST API."""
    
    def __init__(self):
        self.redis_client: Optional[Redis] = None
        self.subscribers: Dict[str, List[Callable]] = {}
        self.is_connected = False
        self.session: Optional[aiohttp.ClientSession] = None
        
        # Upstash connection details
        self.upstash_url = "https://fair-gopher-18329.upstash.io"
        self.upstash_token = "AUeZAAIncDJjM2JkYTMwZGVhN2I0NzQ5ODJmNjU0MDE0MzdjOTU0M3AyMTgzMjk"
        
    async def initialize(self):
        """Initialize Upstash Redis connection."""
        try:
            # Initialize Upstash Redis client
            self.redis_client = Redis(
                url=self.upstash_url,
                token=self.upstash_token
            )
            
            # Test connection
            await self.redis_client.ping()
            self.is_connected = True
            
            logger.info("Upstash Redis pub/sub client initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize Upstash Redis client: {e}")
            self.is_connected = False
            raise
    
    async def close(self):
        """Close Redis connections."""
        if self.redis_client:
            # Note: Upstash Redis client doesn't need explicit closing for REST API
            pass
        
        if self.session:
            await self.session.close()
        
        self.is_connected = False
        logger.info("Redis pub/sub client closed")
    
    async def publish(self, channel: str, message: Dict[str, Any]) -> bool:
        """Publish message to Redis channel."""
        if not self.is_connected or not self.redis_client:
            logger.warning("Redis client not connected, cannot publish message")
            return False
        
        try:
            # Serialize message to JSON
            message_json = json.dumps(message, default=str)
            
            # Publish to channel
            result = await self.redis_client.publish(channel, message_json)
            
            logger.debug(f"Published message to channel '{channel}': {len(message_json)} bytes")
            return True
            
        except Exception as e:
            logger.error(f"Failed to publish message to channel '{channel}': {e}")
            return False
    
    async def publish_log_event(self, event_type: str, level: str, message: str, 
                               metadata: Optional[Dict[str, Any]] = None):
        """Publish a log event to the logging channel."""
        log_event = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "service": "whisper-asr-secure",
            "event_type": event_type,
            "level": level,
            "message": message,
            "metadata": metadata or {}
        }
        
        return await self.publish("service_logs", log_event)
    
    async def publish_system_event(self, event_type: str, data: Dict[str, Any]):
        """Publish a system event to the system events channel."""
        system_event = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "service": "whisper-asr-secure",
            "event_type": event_type,
            "data": data
        }
        
        return await self.publish("system_events", system_event)
    
    async def publish_auth_event(self, event_type: str, user_id: str, 
                                client_ip: str, metadata: Optional[Dict[str, Any]] = None):
        """Publish an authentication event to the auth events channel."""
        auth_event = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "service": "whisper-asr-secure",
            "event_type": event_type,
            "user_id": user_id,
            "client_ip": client_ip,
            "metadata": metadata or {}
        }
        
        return await self.publish("auth_events", auth_event)
    
    async def publish_websocket_event(self, event_type: str, connection_id: str, 
                                     user_id: str, metadata: Optional[Dict[str, Any]] = None):
        """Publish a WebSocket event to the WebSocket events channel."""
        ws_event = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "service": "whisper-asr-secure",
            "event_type": event_type,
            "connection_id": connection_id,
            "user_id": user_id,
            "metadata": metadata or {}
        }
        
        return await self.publish("websocket_events", ws_event)
    
    async def publish_asr_event(self, event_type: str, request_id: str, 
                               user_id: str, metadata: Optional[Dict[str, Any]] = None):
        """Publish an ASR processing event to the ASR events channel."""
        asr_event = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "service": "whisper-asr-secure",
            "event_type": event_type,
            "request_id": request_id,
            "user_id": user_id,
            "metadata": metadata or {}
        }
        
        return await self.publish("asr_events", asr_event)
    
    async def publish_health_status(self, status: Dict[str, Any]):
        """Publish health status to the health channel."""
        health_event = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "service": "whisper-asr-secure",
            "event_type": "health_status",
            "status": status
        }
        
        return await self.publish("health_status", health_event)
    
    async def publish_metrics(self, metrics: Dict[str, Any]):
        """Publish metrics data to the metrics channel."""
        metrics_event = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "service": "whisper-asr-secure",
            "event_type": "metrics_update",
            "metrics": metrics
        }
        
        return await self.publish("service_metrics", metrics_event)
    
    async def store_log_entry(self, log_entry: Dict[str, Any], retention_days: int = 7):
        """Store log entry in Redis with expiration."""
        if not self.is_connected or not self.redis_client:
            return False
        
        try:
            # Create log key with timestamp
            timestamp = datetime.now(timezone.utc)
            log_key = f"log:{timestamp.strftime('%Y%m%d')}:{timestamp.strftime('%H%M%S%f')}"
            
            # Store log entry with expiration
            await self.redis_client.setex(
                log_key,
                retention_days * 24 * 3600,  # Convert days to seconds
                json.dumps(log_entry, default=str)
            )
            
            # Also add to daily log list
            daily_key = f"logs:daily:{timestamp.strftime('%Y%m%d')}"
            await self.redis_client.lpush(daily_key, log_key)
            await self.redis_client.expire(daily_key, retention_days * 24 * 3600)
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to store log entry: {e}")
            return False
    
    async def get_recent_logs(self, hours: int = 1, limit: int = 100) -> List[Dict[str, Any]]:
        """Retrieve recent log entries."""
        if not self.is_connected or not self.redis_client:
            return []
        
        try:
            # Get logs from recent days
            logs = []
            now = datetime.now(timezone.utc)
            
            for days_back in range(2):  # Check today and yesterday
                date_key = (now - timedelta(days=days_back)).strftime('%Y%m%d')
                daily_key = f"logs:daily:{date_key}"
                
                # Get log keys from daily list
                log_keys = await self.redis_client.lrange(daily_key, 0, limit)
                
                for log_key in log_keys:
                    try:
                        log_data = await self.redis_client.get(log_key)
                        if log_data:
                            log_entry = json.loads(log_data)
                            # Filter by time
                            log_time = datetime.fromisoformat(log_entry.get('timestamp', ''))
                            if (now - log_time).total_seconds() <= hours * 3600:
                                logs.append(log_entry)
                    except Exception:
                        continue
                
                if len(logs) >= limit:
                    break
            
            # Sort by timestamp (newest first)
            logs.sort(key=lambda x: x.get('timestamp', ''), reverse=True)
            return logs[:limit]
            
        except Exception as e:
            logger.error(f"Failed to get recent logs: {e}")
            return []


# Global Redis pub/sub instance
redis_pubsub = UpstashRedisPubSub()


class LoggingHandler(logging.Handler):
    """Custom logging handler that publishes logs to Redis."""
    
    def __init__(self, pubsub_client: UpstashRedisPubSub):
        super().__init__()
        self.pubsub_client = pubsub_client
    
    def emit(self, record):
        """Emit a log record to Redis."""
        try:
            # Format the log record
            log_entry = {
                "timestamp": datetime.fromtimestamp(record.created, timezone.utc).isoformat(),
                "level": record.levelname,
                "logger": record.name,
                "message": record.getMessage(),
                "module": record.module,
                "function": record.funcName,
                "line": record.lineno,
                "thread": record.thread,
                "process": record.process
            }
            
            # Add exception info if present
            if record.exc_info:
                log_entry["exception"] = self.format(record)
            
            # Store log entry in Redis (fire and forget)
            if self.pubsub_client.is_connected:
                asyncio.create_task(self.pubsub_client.store_log_entry(log_entry))
                asyncio.create_task(self.pubsub_client.publish_log_event(
                    "log_entry",
                    record.levelname,
                    record.getMessage(),
                    {
                        "logger": record.name,
                        "module": record.module,
                        "function": record.funcName,
                        "line": record.lineno
                    }
                ))
            
        except Exception:
            # Don't let logging errors crash the application
            pass


def setup_redis_logging():
    """Set up Redis logging handler."""
    if not settings.ANALYTICS_ENABLED:
        return
    
    try:
        # Add Redis handler to root logger
        redis_handler = LoggingHandler(redis_pubsub)
        redis_handler.setLevel(logging.INFO)
        
        # Add to specific loggers
        loggers = [
            logging.getLogger('app'),
            logging.getLogger('uvicorn'),
            logging.getLogger('fastapi')
        ]
        
        for logger_instance in loggers:
            logger_instance.addHandler(redis_handler)
        
        logger.info("Redis logging handler configured")
        
    except Exception as e:
        logger.error(f"Failed to setup Redis logging: {e}")


# Startup and shutdown handlers
async def init_redis_pubsub():
    """Initialize Redis pub/sub system."""
    try:
        await redis_pubsub.initialize()
        setup_redis_logging()
        
        # Publish startup event
        await redis_pubsub.publish_system_event("service_started", {
            "version": settings.APP_VERSION,
            "configuration": {
                "tls_enabled": settings.TLS_ENABLED,
                "websocket_enabled": settings.WEBSOCKET_ENABLED,
                "analytics_enabled": settings.ANALYTICS_ENABLED,
                "asr_engine": settings.ASR_ENGINE,
                "asr_model": settings.ASR_MODEL
            }
        })
        
        logger.info("Redis pub/sub system initialized")
        
    except Exception as e:
        logger.error(f"Failed to initialize Redis pub/sub system: {e}")
        # Continue without Redis pub/sub if it fails
        pass


async def cleanup_redis_pubsub():
    """Cleanup Redis pub/sub system."""
    try:
        # Publish shutdown event
        if redis_pubsub.is_connected:
            await redis_pubsub.publish_system_event("service_stopping", {
                "reason": "normal_shutdown"
            })
        
        await redis_pubsub.close()
        logger.info("Redis pub/sub system shutdown complete")
        
    except Exception as e:
        logger.error(f"Error during Redis pub/sub cleanup: {e}")


# Import fix
from datetime import timedelta