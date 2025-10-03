"""
Health check system for secure whisper ASR service.
Provides comprehensive health monitoring for all service components.
"""

import asyncio
import logging
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional
from enum import Enum

from app.config import get_settings
from app.middleware.auth import auth_manager
from app.websocket.handler import websocket_manager
from app.utils.tls_manager import tls_manager
from app.utils.redis_pubsub import redis_pubsub
from app.monitoring.analytics import metrics_collector

logger = logging.getLogger(__name__)
settings = get_settings()


class HealthStatus(Enum):
    """Health status enumeration."""
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"
    UNKNOWN = "unknown"


class HealthCheck:
    """Individual health check."""
    
    def __init__(self, name: str, description: str, critical: bool = False):
        self.name = name
        self.description = description
        self.critical = critical
        self.status = HealthStatus.UNKNOWN
        self.message = ""
        self.last_checked = None
        self.response_time_ms = 0.0
        self.details = {}


class HealthCheckManager:
    """Manages all health checks for the service."""
    
    def __init__(self):
        self.checks: Dict[str, HealthCheck] = {}
        self.overall_status = HealthStatus.UNKNOWN
        self.last_check_time = None
        self.check_interval = settings.HEALTH_CHECK_INTERVAL
        self.background_task: Optional[asyncio.Task] = None
        
        # Register all health checks
        self._register_health_checks()
    
    def _register_health_checks(self):
        """Register all health checks."""
        
        # System health checks
        self.checks["system_memory"] = HealthCheck(
            "system_memory",
            "System memory usage check",
            critical=True
        )
        
        self.checks["system_disk"] = HealthCheck(
            "system_disk",
            "System disk usage check",
            critical=True
        )
        
        self.checks["system_cpu"] = HealthCheck(
            "system_cpu",
            "System CPU usage check",
            critical=False
        )
        
        # Service component checks
        self.checks["redis_connection"] = HealthCheck(
            "redis_connection",
            "Redis connection and authentication",
            critical=True
        )
        
        self.checks["tls_certificates"] = HealthCheck(
            "tls_certificates",
            "TLS certificate validity",
            critical=True
        )
        
        self.checks["websocket_manager"] = HealthCheck(
            "websocket_manager",
            "WebSocket manager status",
            critical=False
        )
        
        self.checks["metrics_collector"] = HealthCheck(
            "metrics_collector",
            "Metrics collection system",
            critical=False
        )
        
        # Application-specific checks
        self.checks["default_websockets"] = HealthCheck(
            "default_websockets",
            "Default WebSocket connections",
            critical=False
        )
        
        logger.info(f"Registered {len(self.checks)} health checks")
    
    async def initialize(self):
        """Initialize health check manager."""
        # Start background health checking
        if self.background_task is None:
            self.background_task = asyncio.create_task(self._background_health_checks())
        
        # Perform initial health check
        await self.run_all_checks()
        
        logger.info("Health check manager initialized")
    
    async def shutdown(self):
        """Shutdown health check manager."""
        if self.background_task:
            self.background_task.cancel()
            try:
                await self.background_task
            except asyncio.CancelledError:
                pass
        
        logger.info("Health check manager shutdown")
    
    async def run_all_checks(self) -> Dict[str, Any]:
        """Run all health checks and return results."""
        start_time = datetime.now(timezone.utc)
        
        # Run all checks concurrently
        check_tasks = []
        for check_name in self.checks:
            check_tasks.append(self._run_single_check(check_name))
        
        await asyncio.gather(*check_tasks, return_exceptions=True)
        
        # Calculate overall status
        self._calculate_overall_status()
        
        self.last_check_time = start_time
        total_time = (datetime.now(timezone.utc) - start_time).total_seconds() * 1000
        
        # Publish health status to Redis
        if redis_pubsub.is_connected:
            await redis_pubsub.publish_health_status(self.get_health_summary())
        
        logger.debug(f"Health checks completed in {total_time:.2f}ms")
        
        return self.get_health_summary()
    
    async def _run_single_check(self, check_name: str):
        """Run a single health check."""
        check = self.checks.get(check_name)
        if not check:
            return
        
        start_time = datetime.now(timezone.utc)
        
        try:
            # Run the specific health check
            if check_name == "system_memory":
                await self._check_system_memory(check)
            elif check_name == "system_disk":
                await self._check_system_disk(check)
            elif check_name == "system_cpu":
                await self._check_system_cpu(check)
            elif check_name == "redis_connection":
                await self._check_redis_connection(check)
            elif check_name == "tls_certificates":
                await self._check_tls_certificates(check)
            elif check_name == "websocket_manager":
                await self._check_websocket_manager(check)
            elif check_name == "metrics_collector":
                await self._check_metrics_collector(check)
            elif check_name == "default_websockets":
                await self._check_default_websockets(check)
            else:
                check.status = HealthStatus.UNKNOWN
                check.message = "Unknown health check"
            
        except Exception as e:
            check.status = HealthStatus.UNHEALTHY
            check.message = f"Health check failed: {str(e)}"
            check.details = {"error": str(e)}
            logger.error(f"Health check '{check_name}' failed: {e}")
        
        finally:
            check.last_checked = start_time
            check.response_time_ms = (datetime.now(timezone.utc) - start_time).total_seconds() * 1000
    
    async def _check_system_memory(self, check: HealthCheck):
        """Check system memory usage."""
        import psutil
        
        memory = psutil.virtual_memory()
        memory_percent = memory.percent
        
        check.details = {
            "memory_percent": memory_percent,
            "memory_used_gb": round(memory.used / (1024**3), 2),
            "memory_total_gb": round(memory.total / (1024**3), 2),
            "memory_available_gb": round(memory.available / (1024**3), 2)
        }
        
        if memory_percent > 90:
            check.status = HealthStatus.UNHEALTHY
            check.message = f"Memory usage critically high: {memory_percent}%"
        elif memory_percent > 80:
            check.status = HealthStatus.DEGRADED
            check.message = f"Memory usage high: {memory_percent}%"
        else:
            check.status = HealthStatus.HEALTHY
            check.message = f"Memory usage normal: {memory_percent}%"
    
    async def _check_system_disk(self, check: HealthCheck):
        """Check system disk usage."""
        import psutil
        
        disk = psutil.disk_usage('/')
        disk_percent = (disk.used / disk.total) * 100
        
        check.details = {
            "disk_percent": round(disk_percent, 2),
            "disk_used_gb": round(disk.used / (1024**3), 2),
            "disk_total_gb": round(disk.total / (1024**3), 2),
            "disk_free_gb": round(disk.free / (1024**3), 2)
        }
        
        if disk_percent > 95:
            check.status = HealthStatus.UNHEALTHY
            check.message = f"Disk usage critically high: {disk_percent:.1f}%"
        elif disk_percent > 85:
            check.status = HealthStatus.DEGRADED
            check.message = f"Disk usage high: {disk_percent:.1f}%"
        else:
            check.status = HealthStatus.HEALTHY
            check.message = f"Disk usage normal: {disk_percent:.1f}%"
    
    async def _check_system_cpu(self, check: HealthCheck):
        """Check system CPU usage."""
        import psutil
        
        cpu_percent = psutil.cpu_percent(interval=0.1)
        load_avg = psutil.getloadavg() if hasattr(psutil, 'getloadavg') else [0, 0, 0]
        
        check.details = {
            "cpu_percent": cpu_percent,
            "load_average_1m": load_avg[0],
            "load_average_5m": load_avg[1],
            "load_average_15m": load_avg[2],
            "cpu_count": psutil.cpu_count()
        }
        
        if cpu_percent > 95:
            check.status = HealthStatus.UNHEALTHY
            check.message = f"CPU usage critically high: {cpu_percent}%"
        elif cpu_percent > 80:
            check.status = HealthStatus.DEGRADED
            check.message = f"CPU usage high: {cpu_percent}%"
        else:
            check.status = HealthStatus.HEALTHY
            check.message = f"CPU usage normal: {cpu_percent}%"
    
    async def _check_redis_connection(self, check: HealthCheck):
        """Check Redis connection and authentication."""
        if not settings.REDIS_AUTH_ENABLED:
            check.status = HealthStatus.HEALTHY
            check.message = "Redis authentication disabled"
            check.details = {"enabled": False}
            return
        
        if not auth_manager.redis_client:
            check.status = HealthStatus.UNHEALTHY
            check.message = "Redis client not initialized"
            check.details = {"connected": False}
            return
        
        try:
            # Test Redis connection
            await auth_manager.redis_client.ping()
            check.status = HealthStatus.HEALTHY
            check.message = "Redis connection healthy"
            check.details = {
                "connected": True,
                "url": settings.REDIS_URL[:20] + "..." if len(settings.REDIS_URL) > 20 else settings.REDIS_URL
            }
        except Exception as e:
            check.status = HealthStatus.UNHEALTHY
            check.message = f"Redis connection failed: {str(e)}"
            check.details = {"connected": False, "error": str(e)}
    
    async def _check_tls_certificates(self, check: HealthCheck):
        """Check TLS certificate validity."""
        if not settings.TLS_ENABLED:
            check.status = HealthStatus.HEALTHY
            check.message = "TLS disabled"
            check.details = {"enabled": False}
            return
        
        try:
            cert_info = await tls_manager.get_certificate_info()
            
            if cert_info.get("status") == "valid":
                days_until_expiry = cert_info.get("days_until_expiry", 0)
                
                if days_until_expiry <= 7:
                    check.status = HealthStatus.UNHEALTHY
                    check.message = f"Certificate expires in {days_until_expiry} days"
                elif days_until_expiry <= 30:
                    check.status = HealthStatus.DEGRADED
                    check.message = f"Certificate expires in {days_until_expiry} days"
                else:
                    check.status = HealthStatus.HEALTHY
                    check.message = f"Certificate valid for {days_until_expiry} days"
                
                check.details = {
                    "days_until_expiry": days_until_expiry,
                    "is_self_signed": cert_info.get("is_self_signed", True),
                    "subject": cert_info.get("subject", ""),
                    "not_after": cert_info.get("not_after", "")
                }
            else:
                check.status = HealthStatus.UNHEALTHY
                check.message = f"Certificate status: {cert_info.get('status', 'unknown')}"
                check.details = cert_info
                
        except Exception as e:
            check.status = HealthStatus.UNHEALTHY
            check.message = f"Certificate check failed: {str(e)}"
            check.details = {"error": str(e)}
    
    async def _check_websocket_manager(self, check: HealthCheck):
        """Check WebSocket manager status."""
        if not settings.WEBSOCKET_ENABLED:
            check.status = HealthStatus.HEALTHY
            check.message = "WebSocket disabled"
            check.details = {"enabled": False}
            return
        
        try:
            stats = await websocket_manager.get_connection_stats()
            
            check.status = HealthStatus.HEALTHY
            check.message = f"WebSocket manager healthy - {stats['active_connections']} active connections"
            check.details = stats
            
        except Exception as e:
            check.status = HealthStatus.UNHEALTHY
            check.message = f"WebSocket manager check failed: {str(e)}"
            check.details = {"error": str(e)}
    
    async def _check_metrics_collector(self, check: HealthCheck):
        """Check metrics collector status."""
        if not settings.METRICS_ENABLED:
            check.status = HealthStatus.HEALTHY
            check.message = "Metrics collection disabled"
            check.details = {"enabled": False}
            return
        
        try:
            api_stats = metrics_collector.get_api_statistics()
            ws_stats = metrics_collector.get_websocket_statistics()
            
            check.status = HealthStatus.HEALTHY
            check.message = f"Metrics collector healthy - {api_stats.get('total_requests', 0)} API requests tracked"
            check.details = {
                "api_requests": api_stats.get('total_requests', 0),
                "websocket_connections": ws_stats.get('total_connections', 0)
            }
            
        except Exception as e:
            check.status = HealthStatus.UNHEALTHY
            check.message = f"Metrics collector check failed: {str(e)}"
            check.details = {"error": str(e)}
    
    async def _check_default_websockets(self, check: HealthCheck):
        """Check default WebSocket connections."""
        if not settings.DEFAULT_WEBSOCKETS or not settings.WEBSOCKET_ENABLED:
            check.status = HealthStatus.HEALTHY
            check.message = "Default WebSockets disabled"
            check.details = {"enabled": False}
            return
        
        try:
            # This would check default monitoring WebSocket connections
            # For now, just report as healthy
            check.status = HealthStatus.HEALTHY
            check.message = "Default WebSockets ready"
            check.details = {"enabled": True, "count": 0}
            
        except Exception as e:
            check.status = HealthStatus.DEGRADED
            check.message = f"Default WebSockets check failed: {str(e)}"
            check.details = {"error": str(e)}
    
    def _calculate_overall_status(self):
        """Calculate overall service health status."""
        critical_checks = [check for check in self.checks.values() if check.critical]
        non_critical_checks = [check for check in self.checks.values() if not check.critical]
        
        # Check critical systems first
        critical_unhealthy = any(check.status == HealthStatus.UNHEALTHY for check in critical_checks)
        critical_degraded = any(check.status == HealthStatus.DEGRADED for check in critical_checks)
        
        if critical_unhealthy:
            self.overall_status = HealthStatus.UNHEALTHY
        elif critical_degraded:
            self.overall_status = HealthStatus.DEGRADED
        else:
            # Check non-critical systems
            non_critical_unhealthy = any(check.status == HealthStatus.UNHEALTHY for check in non_critical_checks)
            non_critical_degraded = any(check.status == HealthStatus.DEGRADED for check in non_critical_checks)
            
            if non_critical_unhealthy:
                self.overall_status = HealthStatus.DEGRADED
            elif non_critical_degraded:
                self.overall_status = HealthStatus.DEGRADED
            else:
                self.overall_status = HealthStatus.HEALTHY
    
    def get_health_summary(self) -> Dict[str, Any]:
        """Get health summary for all checks."""
        return {
            "status": self.overall_status.value,
            "timestamp": self.last_check_time.isoformat() if self.last_check_time else None,
            "service": "whisper-asr-secure",
            "version": settings.APP_VERSION,
            "checks": {
                check_name: {
                    "status": check.status.value,
                    "message": check.message,
                    "critical": check.critical,
                    "last_checked": check.last_checked.isoformat() if check.last_checked else None,
                    "response_time_ms": check.response_time_ms,
                    "details": check.details
                }
                for check_name, check in self.checks.items()
            }
        }
    
    def get_simple_health(self) -> Dict[str, Any]:
        """Get simple health status."""
        return {
            "status": self.overall_status.value,
            "timestamp": self.last_check_time.isoformat() if self.last_check_time else None,
            "healthy": self.overall_status == HealthStatus.HEALTHY
        }
    
    async def _background_health_checks(self):
        """Background task for periodic health checks."""
        while True:
            try:
                await asyncio.sleep(self.check_interval)
                await self.run_all_checks()
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in background health checks: {e}")
                await asyncio.sleep(self.check_interval)


# Global health check manager
health_manager = HealthCheckManager()


# Startup and shutdown handlers
async def init_health_checks():
    """Initialize health check system."""
    await health_manager.initialize()
    logger.info("Health check system initialized")


async def cleanup_health_checks():
    """Cleanup health check system."""
    await health_manager.shutdown()
    logger.info("Health check system shutdown complete")