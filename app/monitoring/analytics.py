"""
Analytics and monitoring system for secure whisper ASR service.
Tracks active sockets, ports, API calls, and system metrics.
"""

import asyncio
import json
import logging
import psutil
import time
from collections import defaultdict, deque
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional, DefaultDict
from dataclasses import dataclass, asdict
from threading import Lock

from app.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


@dataclass
class APICallMetric:
    """Represents a single API call metric."""
    timestamp: str
    endpoint: str
    method: str
    status_code: int
    response_time_ms: float
    user_id: str
    client_ip: str
    request_size: int
    response_size: int


@dataclass
class WebSocketMetric:
    """Represents WebSocket connection metrics."""
    connection_id: str
    user_id: str
    connected_at: str
    last_activity: str
    messages_sent: int
    messages_received: int
    bytes_sent: int
    bytes_received: int
    is_active: bool


@dataclass
class SystemMetric:
    """Represents system resource metrics."""
    timestamp: str
    cpu_percent: float
    memory_percent: float
    memory_used_mb: float
    memory_available_mb: float
    disk_usage_percent: float
    disk_used_gb: float
    disk_free_gb: float
    network_bytes_sent: int
    network_bytes_recv: int
    active_connections: int
    load_average: List[float]


class MetricsCollector:
    """Collects and stores various system and application metrics."""
    
    def __init__(self, retention_hours: int = 24):
        self.retention_hours = retention_hours
        self.retention_seconds = retention_hours * 3600
        
        # Metrics storage
        self.api_calls: deque = deque()
        self.websocket_metrics: Dict[str, WebSocketMetric] = {}
        self.system_metrics: deque = deque()
        
        # Aggregated statistics
        self.api_stats = defaultdict(int)
        self.endpoint_stats = defaultdict(lambda: defaultdict(int))
        self.user_stats = defaultdict(lambda: defaultdict(int))
        
        # Thread safety
        self.lock = Lock()
        
        # Background tasks
        self.cleanup_task: Optional[asyncio.Task] = None
        self.system_metrics_task: Optional[asyncio.Task] = None
        
        logger.info(f"MetricsCollector initialized with {retention_hours}h retention")
    
    async def initialize(self):
        """Initialize the metrics collector."""
        # Start background tasks
        self.cleanup_task = asyncio.create_task(self._cleanup_old_metrics())
        self.system_metrics_task = asyncio.create_task(self._collect_system_metrics())
        
        logger.info("MetricsCollector background tasks started")
    
    async def shutdown(self):
        """Shutdown the metrics collector."""
        if self.cleanup_task:
            self.cleanup_task.cancel()
        if self.system_metrics_task:
            self.system_metrics_task.cancel()
        
        # Wait for tasks to complete
        try:
            if self.cleanup_task:
                await self.cleanup_task
            if self.system_metrics_task:
                await self.system_metrics_task
        except asyncio.CancelledError:
            pass
        
        logger.info("MetricsCollector shutdown complete")
    
    def record_api_call(self, endpoint: str, method: str, status_code: int, 
                       response_time_ms: float, user_id: str = "anonymous", 
                       client_ip: str = "unknown", request_size: int = 0, 
                       response_size: int = 0):
        """Record an API call metric."""
        try:
            metric = APICallMetric(
                timestamp=datetime.now(timezone.utc).isoformat(),
                endpoint=endpoint,
                method=method,
                status_code=status_code,
                response_time_ms=response_time_ms,
                user_id=user_id,
                client_ip=client_ip,
                request_size=request_size,
                response_size=response_size
            )
            
            with self.lock:
                self.api_calls.append(metric)
                
                # Update aggregated stats
                self.api_stats['total_requests'] += 1
                self.api_stats[f'status_{status_code}'] += 1
                
                self.endpoint_stats[endpoint]['count'] += 1
                self.endpoint_stats[endpoint]['total_response_time'] += response_time_ms
                
                self.user_stats[user_id]['requests'] += 1
                self.user_stats[user_id]['total_response_time'] += response_time_ms
                
                if status_code >= 400:
                    self.api_stats['error_requests'] += 1
                    self.endpoint_stats[endpoint]['errors'] += 1
                    self.user_stats[user_id]['errors'] += 1
        
        except Exception as e:
            logger.error(f"Failed to record API call metric: {e}")
    
    def update_websocket_metric(self, connection_id: str, user_id: str, 
                               connected_at: str, last_activity: str,
                               messages_sent: int = 0, messages_received: int = 0,
                               bytes_sent: int = 0, bytes_received: int = 0,
                               is_active: bool = True):
        """Update WebSocket connection metrics."""
        try:
            with self.lock:
                self.websocket_metrics[connection_id] = WebSocketMetric(
                    connection_id=connection_id,
                    user_id=user_id,
                    connected_at=connected_at,
                    last_activity=last_activity,
                    messages_sent=messages_sent,
                    messages_received=messages_received,
                    bytes_sent=bytes_sent,
                    bytes_received=bytes_received,
                    is_active=is_active
                )
        
        except Exception as e:
            logger.error(f"Failed to update WebSocket metric: {e}")
    
    def remove_websocket_metric(self, connection_id: str):
        """Remove WebSocket connection metrics."""
        try:
            with self.lock:
                self.websocket_metrics.pop(connection_id, None)
        
        except Exception as e:
            logger.error(f"Failed to remove WebSocket metric: {e}")
    
    def get_api_statistics(self) -> Dict[str, Any]:
        """Get API call statistics."""
        try:
            with self.lock:
                # Calculate average response times
                endpoint_averages = {}
                for endpoint, stats in self.endpoint_stats.items():
                    if stats['count'] > 0:
                        endpoint_averages[endpoint] = {
                            'count': stats['count'],
                            'errors': stats.get('errors', 0),
                            'avg_response_time': stats['total_response_time'] / stats['count'],
                            'error_rate': stats.get('errors', 0) / stats['count']
                        }
                
                user_averages = {}
                for user_id, stats in self.user_stats.items():
                    if stats['requests'] > 0:
                        user_averages[user_id] = {
                            'requests': stats['requests'],
                            'errors': stats.get('errors', 0),
                            'avg_response_time': stats['total_response_time'] / stats['requests'],
                            'error_rate': stats.get('errors', 0) / stats['requests']
                        }
                
                return {
                    'total_requests': self.api_stats['total_requests'],
                    'error_requests': self.api_stats.get('error_requests', 0),
                    'error_rate': (self.api_stats.get('error_requests', 0) / 
                                 max(self.api_stats['total_requests'], 1)),
                    'status_codes': {
                        k: v for k, v in self.api_stats.items() 
                        if k.startswith('status_')
                    },
                    'endpoints': endpoint_averages,
                    'users': user_averages,
                    'recent_requests': len(self.api_calls)
                }
        
        except Exception as e:
            logger.error(f"Failed to get API statistics: {e}")
            return {}
    
    def get_websocket_statistics(self) -> Dict[str, Any]:
        """Get WebSocket connection statistics."""
        try:
            with self.lock:
                active_connections = sum(1 for ws in self.websocket_metrics.values() if ws.is_active)
                total_connections = len(self.websocket_metrics)
                
                # Calculate totals
                total_messages_sent = sum(ws.messages_sent for ws in self.websocket_metrics.values())
                total_messages_received = sum(ws.messages_received for ws in self.websocket_metrics.values())
                total_bytes_sent = sum(ws.bytes_sent for ws in self.websocket_metrics.values())
                total_bytes_received = sum(ws.bytes_received for ws in self.websocket_metrics.values())
                
                # Group by user
                users = defaultdict(lambda: {'connections': 0, 'active': 0})
                for ws in self.websocket_metrics.values():
                    users[ws.user_id]['connections'] += 1
                    if ws.is_active:
                        users[ws.user_id]['active'] += 1
                
                return {
                    'total_connections': total_connections,
                    'active_connections': active_connections,
                    'inactive_connections': total_connections - active_connections,
                    'total_messages_sent': total_messages_sent,
                    'total_messages_received': total_messages_received,
                    'total_bytes_sent': total_bytes_sent,
                    'total_bytes_received': total_bytes_received,
                    'users': dict(users)
                }
        
        except Exception as e:
            logger.error(f"Failed to get WebSocket statistics: {e}")
            return {}
    
    def get_system_statistics(self) -> Dict[str, Any]:
        """Get current system statistics."""
        try:
            if not self.system_metrics:
                return {}
            
            with self.lock:
                latest = self.system_metrics[-1] if self.system_metrics else None
                if not latest:
                    return {}
                
                # Calculate averages over recent metrics (last hour)
                recent_metrics = [
                    m for m in self.system_metrics
                    if (datetime.now(timezone.utc) - datetime.fromisoformat(m.timestamp)).total_seconds() <= 3600
                ]
                
                if recent_metrics:
                    avg_cpu = sum(m.cpu_percent for m in recent_metrics) / len(recent_metrics)
                    avg_memory = sum(m.memory_percent for m in recent_metrics) / len(recent_metrics)
                    avg_disk = sum(m.disk_usage_percent for m in recent_metrics) / len(recent_metrics)
                else:
                    avg_cpu = latest.cpu_percent
                    avg_memory = latest.memory_percent
                    avg_disk = latest.disk_usage_percent
                
                return {
                    'current': asdict(latest),
                    'averages_1h': {
                        'cpu_percent': avg_cpu,
                        'memory_percent': avg_memory,
                        'disk_usage_percent': avg_disk
                    },
                    'metrics_count': len(self.system_metrics)
                }
        
        except Exception as e:
            logger.error(f"Failed to get system statistics: {e}")
            return {}
    
    def get_port_statistics(self) -> List[Dict[str, Any]]:
        """Get active port statistics."""
        try:
            connections = psutil.net_connections(kind='inet')
            port_stats = defaultdict(lambda: {'count': 0, 'status': defaultdict(int)})
            
            for conn in connections:
                if conn.laddr:
                    port = conn.laddr.port
                    port_stats[port]['count'] += 1
                    port_stats[port]['status'][conn.status] += 1
            
            return [
                {
                    'port': port,
                    'total_connections': stats['count'],
                    'status_breakdown': dict(stats['status'])
                }
                for port, stats in port_stats.items()
            ]
        
        except Exception as e:
            logger.error(f"Failed to get port statistics: {e}")
            return []
    
    async def _cleanup_old_metrics(self):
        """Background task to clean up old metrics."""
        while True:
            try:
                await asyncio.sleep(300)  # Run every 5 minutes
                
                current_time = datetime.now(timezone.utc)
                cutoff_time = current_time.timestamp() - self.retention_seconds
                
                with self.lock:
                    # Clean up API calls
                    while (self.api_calls and 
                           datetime.fromisoformat(self.api_calls[0].timestamp).timestamp() < cutoff_time):
                        old_metric = self.api_calls.popleft()
                        
                        # Update aggregated stats (subtract the old metric)
                        self.api_stats['total_requests'] -= 1
                        self.api_stats[f'status_{old_metric.status_code}'] -= 1
                        
                        self.endpoint_stats[old_metric.endpoint]['count'] -= 1
                        self.endpoint_stats[old_metric.endpoint]['total_response_time'] -= old_metric.response_time_ms
                        
                        self.user_stats[old_metric.user_id]['requests'] -= 1
                        self.user_stats[old_metric.user_id]['total_response_time'] -= old_metric.response_time_ms
                        
                        if old_metric.status_code >= 400:
                            self.api_stats['error_requests'] -= 1
                            self.endpoint_stats[old_metric.endpoint]['errors'] -= 1
                            self.user_stats[old_metric.user_id]['errors'] -= 1
                    
                    # Clean up system metrics
                    while (self.system_metrics and 
                           datetime.fromisoformat(self.system_metrics[0].timestamp).timestamp() < cutoff_time):
                        self.system_metrics.popleft()
                
                logger.debug("Cleaned up old metrics")
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in metrics cleanup task: {e}")
    
    async def _collect_system_metrics(self):
        """Background task to collect system metrics."""
        while True:
            try:
                # Get system metrics
                cpu_percent = psutil.cpu_percent(interval=1)
                memory = psutil.virtual_memory()
                disk = psutil.disk_usage('/')
                network = psutil.net_io_counters()
                
                # Get load average (Unix only)
                load_avg = []
                try:
                    load_avg = list(psutil.getloadavg())
                except AttributeError:
                    load_avg = [0.0, 0.0, 0.0]  # Windows fallback
                
                # Count active network connections
                active_connections = len([c for c in psutil.net_connections() 
                                        if c.status == 'ESTABLISHED'])
                
                metric = SystemMetric(
                    timestamp=datetime.now(timezone.utc).isoformat(),
                    cpu_percent=cpu_percent,
                    memory_percent=memory.percent,
                    memory_used_mb=memory.used / (1024 * 1024),
                    memory_available_mb=memory.available / (1024 * 1024),
                    disk_usage_percent=disk.percent,
                    disk_used_gb=disk.used / (1024 * 1024 * 1024),
                    disk_free_gb=disk.free / (1024 * 1024 * 1024),
                    network_bytes_sent=network.bytes_sent,
                    network_bytes_recv=network.bytes_recv,
                    active_connections=active_connections,
                    load_average=load_avg
                )
                
                with self.lock:
                    self.system_metrics.append(metric)
                
                await asyncio.sleep(60)  # Collect every minute
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error collecting system metrics: {e}")
                await asyncio.sleep(60)  # Wait before retrying


# Global metrics collector instance
metrics_collector = MetricsCollector(
    retention_hours=getattr(settings, 'METRICS_RETENTION_HOURS', 24)
)


class MonitoringMiddleware:
    """Middleware to collect API call metrics."""
    
    def __init__(self, app):
        self.app = app
    
    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return
        
        # Extract request information
        path = scope.get("path", "unknown")
        method = scope.get("method", "unknown")
        client = scope.get("client", ["unknown", 0])
        client_ip = client[0] if client else "unknown"
        
        start_time = time.time()
        request_size = 0
        response_size = 0
        status_code = 200
        user_id = "anonymous"
        
        # Extract user ID from scope if available
        if hasattr(scope, "user"):
            user_id = getattr(scope["user"], "user_id", "anonymous")
        
        # Wrap send to capture response information
        async def send_wrapper(message):
            nonlocal status_code, response_size
            
            if message["type"] == "http.response.start":
                status_code = message.get("status", 200)
            elif message["type"] == "http.response.body":
                body = message.get("body", b"")
                response_size += len(body)
            
            await send(message)
        
        # Wrap receive to capture request size
        async def receive_wrapper():
            message = await receive()
            nonlocal request_size
            
            if message["type"] == "http.request" and "body" in message:
                request_size += len(message["body"])
            
            return message
        
        try:
            await self.app(scope, receive_wrapper, send_wrapper)
        finally:
            # Calculate response time and record metric
            response_time_ms = (time.time() - start_time) * 1000
            
            metrics_collector.record_api_call(
                endpoint=path,
                method=method,
                status_code=status_code,
                response_time_ms=response_time_ms,
                user_id=user_id,
                client_ip=client_ip,
                request_size=request_size,
                response_size=response_size
            )


# Startup and shutdown handlers
async def init_monitoring():
    """Initialize monitoring system."""
    await metrics_collector.initialize()
    logger.info("Monitoring system initialized")


async def cleanup_monitoring():
    """Cleanup monitoring system."""
    await metrics_collector.shutdown()
    logger.info("Monitoring system shutdown complete")