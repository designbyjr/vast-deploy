"""
Secure WebSocket handler for whisper ASR service.
Provides multi-threaded, TLS-encrypted WebSocket connections with authentication.
"""

import asyncio
import json
import logging
import threading
from typing import Dict, Set, Optional, Any, List
from datetime import datetime, timezone
from concurrent.futures import ThreadPoolExecutor
from urllib.parse import parse_qs

from fastapi import WebSocket, WebSocketDisconnect
from starlette.websockets import WebSocketState

from app.middleware.auth import verify_websocket_auth
from app.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


class WebSocketConnection:
    """Represents a single WebSocket connection with metadata."""
    
    def __init__(self, websocket: WebSocket, user_data: Dict[str, Any], connection_id: str):
        self.websocket = websocket
        self.user_data = user_data
        self.connection_id = connection_id
        self.connected_at = datetime.now(timezone.utc)
        self.last_activity = self.connected_at
        self.message_count = 0
        self.is_active = True
        self.lock = asyncio.Lock()
        
    async def send_message(self, message: Dict[str, Any]) -> bool:
        """Send message to WebSocket with error handling."""
        try:
            async with self.lock:
                if self.websocket.client_state == WebSocketState.CONNECTED:
                    await self.websocket.send_json(message)
                    self.last_activity = datetime.now(timezone.utc)
                    self.message_count += 1
                    return True
                else:
                    self.is_active = False
                    return False
        except Exception as e:
            logger.error(f"Failed to send message to WebSocket {self.connection_id}: {e}")
            self.is_active = False
            return False
    
    async def close(self, code: int = 1000, reason: str = ""):
        """Close WebSocket connection gracefully."""
        try:
            async with self.lock:
                if self.websocket.client_state == WebSocketState.CONNECTED:
                    await self.websocket.close(code=code, reason=reason)
                self.is_active = False
        except Exception as e:
            logger.error(f"Error closing WebSocket {self.connection_id}: {e}")


class WebSocketManager:
    """Manages WebSocket connections with multi-threading support."""
    
    def __init__(self):
        self.connections: Dict[str, WebSocketConnection] = {}
        self.user_connections: Dict[str, Set[str]] = {}  # user_id -> connection_ids
        self.default_connections: Dict[str, WebSocketConnection] = {}
        self.executor = ThreadPoolExecutor(max_workers=settings.WEBSOCKET_MAX_CONNECTIONS // 10 or 1)
        self.cleanup_task: Optional[asyncio.Task] = None
        self.stats_lock = asyncio.Lock()
        
    async def initialize(self):
        """Initialize WebSocket manager and create default connections."""
        logger.info("Initializing WebSocket manager")
        
        # Start cleanup task
        self.cleanup_task = asyncio.create_task(self._cleanup_inactive_connections())
        
        # Create default health check WebSocket connections if enabled
        if settings.DEFAULT_WEBSOCKETS:
            await self._create_default_connections()
        
        logger.info(f"WebSocket manager initialized with {len(self.default_connections)} default connections")
    
    async def shutdown(self):
        """Shutdown WebSocket manager and close all connections."""
        logger.info("Shutting down WebSocket manager")
        
        # Cancel cleanup task
        if self.cleanup_task:
            self.cleanup_task.cancel()
            try:
                await self.cleanup_task
            except asyncio.CancelledError:
                pass
        
        # Close all connections
        close_tasks = []
        for connection in list(self.connections.values()):
            close_tasks.append(connection.close(code=1001, reason="Server shutdown"))
        
        if close_tasks:
            await asyncio.gather(*close_tasks, return_exceptions=True)
        
        # Shutdown thread pool
        self.executor.shutdown(wait=True)
        
        logger.info("WebSocket manager shutdown complete")
    
    async def connect(self, websocket: WebSocket, connection_id: str, 
                     user_data: Dict[str, Any]) -> WebSocketConnection:
        """Add a new WebSocket connection."""
        connection = WebSocketConnection(websocket, user_data, connection_id)
        
        async with self.stats_lock:
            self.connections[connection_id] = connection
            
            # Track user connections
            user_id = user_data.get("user_id", "anonymous")
            if user_id not in self.user_connections:
                self.user_connections[user_id] = set()
            self.user_connections[user_id].add(connection_id)
        
        logger.info(f"WebSocket connected: {connection_id} for user: {user_id}")
        
        # Send welcome message
        await connection.send_message({
            "type": "connection_established",
            "connection_id": connection_id,
            "timestamp": connection.connected_at.isoformat(),
            "server_info": {
                "version": "1.0.0",
                "features": ["asr", "authentication", "monitoring"]
            }
        })
        
        return connection
    
    async def disconnect(self, connection_id: str):
        """Remove a WebSocket connection."""
        async with self.stats_lock:
            connection = self.connections.pop(connection_id, None)
            if connection:
                user_id = connection.user_data.get("user_id", "anonymous")
                if user_id in self.user_connections:
                    self.user_connections[user_id].discard(connection_id)
                    if not self.user_connections[user_id]:
                        del self.user_connections[user_id]
                
                logger.info(f"WebSocket disconnected: {connection_id} for user: {user_id}")
                return connection
        return None
    
    async def broadcast_to_user(self, user_id: str, message: Dict[str, Any]) -> int:
        """Broadcast message to all connections for a specific user."""
        sent_count = 0
        user_connection_ids = self.user_connections.get(user_id, set()).copy()
        
        for connection_id in user_connection_ids:
            connection = self.connections.get(connection_id)
            if connection and connection.is_active:
                success = await connection.send_message(message)
                if success:
                    sent_count += 1
                else:
                    # Connection is no longer active, schedule for cleanup
                    await self.disconnect(connection_id)
        
        return sent_count
    
    async def broadcast_to_all(self, message: Dict[str, Any]) -> int:
        """Broadcast message to all active connections."""
        sent_count = 0
        connection_ids = list(self.connections.keys())
        
        for connection_id in connection_ids:
            connection = self.connections.get(connection_id)
            if connection and connection.is_active:
                success = await connection.send_message(message)
                if success:
                    sent_count += 1
                else:
                    # Connection is no longer active, schedule for cleanup
                    await self.disconnect(connection_id)
        
        return sent_count
    
    async def get_connection_stats(self) -> Dict[str, Any]:
        """Get current WebSocket connection statistics."""
        async with self.stats_lock:
            active_connections = sum(1 for conn in self.connections.values() if conn.is_active)
            
            return {
                "total_connections": len(self.connections),
                "active_connections": active_connections,
                "inactive_connections": len(self.connections) - active_connections,
                "unique_users": len(self.user_connections),
                "default_connections": len(self.default_connections),
                "connections_by_user": {
                    user_id: len(conn_ids) 
                    for user_id, conn_ids in self.user_connections.items()
                }
            }
    
    async def _cleanup_inactive_connections(self):
        """Background task to clean up inactive connections."""
        while True:
            try:
                await asyncio.sleep(60)  # Check every minute
                
                inactive_connections = []
                current_time = datetime.now(timezone.utc)
                
                async with self.stats_lock:
                    for connection_id, connection in self.connections.items():
                        # Check if connection is inactive
                        if not connection.is_active:
                            inactive_connections.append(connection_id)
                        # Check for timeout
                        elif (current_time - connection.last_activity).total_seconds() > settings.WEBSOCKET_TIMEOUT:
                            logger.warning(f"WebSocket {connection_id} timed out")
                            inactive_connections.append(connection_id)
                
                # Clean up inactive connections
                for connection_id in inactive_connections:
                    await self.disconnect(connection_id)
                
                if inactive_connections:
                    logger.info(f"Cleaned up {len(inactive_connections)} inactive WebSocket connections")
                    
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in WebSocket cleanup task: {e}")
    
    async def _create_default_connections(self):
        """Create default health check WebSocket connections."""
        # This would be implemented to create monitoring WebSocket connections
        # For now, we'll just log that this feature is available
        logger.info("Default WebSocket connections feature is ready")


# Global WebSocket manager instance
websocket_manager = WebSocketManager()


class SecureWebSocketHandler:
    """Handler for secure WebSocket connections with authentication."""
    
    @staticmethod
    async def authenticate_websocket(websocket: WebSocket, token: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """Authenticate WebSocket connection."""
        if not token:
            # Try to get token from query parameters
            query_params = parse_qs(str(websocket.url.query))
            token_list = query_params.get('token', [])
            if token_list:
                token = token_list[0]
        
        if not token:
            # Try to get token from headers
            auth_header = websocket.headers.get("Authorization", "")
            if auth_header.startswith("Bearer "):
                token = auth_header.split(" ", 1)[1]
        
        if not token:
            await websocket.close(code=4001, reason="Authentication required")
            return None
        
        # Verify token
        is_valid, user_data = await verify_websocket_auth(token)
        if not is_valid:
            await websocket.close(code=4001, reason="Invalid authentication token")
            return None
        
        return user_data
    
    @staticmethod
    async def handle_websocket_connection(websocket: WebSocket, connection_id: str):
        """Handle a new WebSocket connection with authentication."""
        try:
            # Accept connection first
            await websocket.accept()
            
            # Authenticate
            user_data = await SecureWebSocketHandler.authenticate_websocket(websocket)
            if not user_data:
                return  # Connection already closed due to auth failure
            
            # Add to manager
            connection = await websocket_manager.connect(websocket, connection_id, user_data)
            
            try:
                # Handle messages
                while True:
                    try:
                        # Wait for message with timeout
                        message = await asyncio.wait_for(
                            websocket.receive_json(),
                            timeout=settings.WEBSOCKET_PING_TIMEOUT
                        )
                        
                        # Process message in thread pool to avoid blocking
                        await asyncio.get_event_loop().run_in_executor(
                            websocket_manager.executor,
                            SecureWebSocketHandler._process_message,
                            connection, message
                        )
                        
                    except asyncio.TimeoutError:
                        # Send ping to keep connection alive
                        await connection.send_message({
                            "type": "ping",
                            "timestamp": datetime.now(timezone.utc).isoformat()
                        })
                    
            except WebSocketDisconnect:
                logger.info(f"WebSocket {connection_id} disconnected normally")
            except Exception as e:
                logger.error(f"Error handling WebSocket {connection_id}: {e}")
                await connection.close(code=1011, reason="Server error")
            
        finally:
            # Clean up connection
            await websocket_manager.disconnect(connection_id)
    
    @staticmethod
    def _process_message(connection: WebSocketConnection, message: Dict[str, Any]):
        """Process WebSocket message in thread pool (blocking operations)."""
        try:
            message_type = message.get("type", "unknown")
            
            # Handle different message types
            if message_type == "ping":
                # Respond to ping
                asyncio.create_task(connection.send_message({
                    "type": "pong",
                    "timestamp": datetime.now(timezone.utc).isoformat()
                }))
            
            elif message_type == "asr_request":
                # Handle ASR request (would integrate with whisper models)
                asyncio.create_task(SecureWebSocketHandler._handle_asr_request(connection, message))
            
            elif message_type == "status_request":
                # Handle status request
                asyncio.create_task(SecureWebSocketHandler._handle_status_request(connection))
            
            else:
                logger.warning(f"Unknown message type: {message_type} from {connection.connection_id}")
                asyncio.create_task(connection.send_message({
                    "type": "error",
                    "error": "Unknown message type",
                    "timestamp": datetime.now(timezone.utc).isoformat()
                }))
                
        except Exception as e:
            logger.error(f"Error processing message from {connection.connection_id}: {e}")
            asyncio.create_task(connection.send_message({
                "type": "error",
                "error": "Message processing error",
                "timestamp": datetime.now(timezone.utc).isoformat()
            }))
    
    @staticmethod
    async def _handle_asr_request(connection: WebSocketConnection, message: Dict[str, Any]):
        """Handle ASR request via WebSocket."""
        # This would integrate with the whisper ASR models
        # For now, send a placeholder response
        await connection.send_message({
            "type": "asr_response",
            "request_id": message.get("request_id"),
            "status": "processing",
            "message": "ASR processing not yet implemented",
            "timestamp": datetime.now(timezone.utc).isoformat()
        })
    
    @staticmethod
    async def _handle_status_request(connection: WebSocketConnection):
        """Handle status request via WebSocket."""
        stats = await websocket_manager.get_connection_stats()
        await connection.send_message({
            "type": "status_response",
            "connection_stats": stats,
            "connection_info": {
                "id": connection.connection_id,
                "user_id": connection.user_data.get("user_id"),
                "connected_at": connection.connected_at.isoformat(),
                "message_count": connection.message_count,
                "last_activity": connection.last_activity.isoformat()
            },
            "timestamp": datetime.now(timezone.utc).isoformat()
        })


# Startup and shutdown handlers for WebSocket manager
async def init_websocket_manager():
    """Initialize WebSocket manager."""
    await websocket_manager.initialize()


async def cleanup_websocket_manager():
    """Cleanup WebSocket manager."""
    await websocket_manager.shutdown()
