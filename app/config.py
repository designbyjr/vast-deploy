"""
Configuration management for secure whisper ASR service.
Handles environment variables, settings validation, and configuration loading.
"""

import os
from functools import lru_cache
from typing import Optional, List, Dict, Any
from pydantic import BaseSettings, validator, Field


class Settings(BaseSettings):
    """Application settings with validation."""
    
    # === Application Info ===
    APP_NAME: str = "Secure Whisper ASR Service"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = False
    
    # === Server Configuration ===
    HOST: str = "0.0.0.0"
    PORT: int = 9443
    WORKERS: int = 1
    
    # === Security Configuration ===
    TLS_ENABLED: bool = True
    TLS_CERT_PATH: str = "/app/certs/cert.pem"
    TLS_KEY_PATH: str = "/app/certs/key.pem"
    TLS_AUTO_GENERATE: bool = True
    TLS_CERT_DAYS: int = 365
    
    # === Redis Configuration (Upstash) ===
    REDIS_AUTH_ENABLED: bool = True
    REDIS_URL: str = "redis://localhost:6379"
    REDIS_PASSWORD: str = ""
    REDIS_TOKEN_DB: int = 0
    REDIS_PUBSUB_DB: int = 1
    REDIS_MAX_CONNECTIONS: int = 10
    REDIS_TIMEOUT: int = 5
    TOKEN_TTL: int = 3600  # Token time to live in seconds
    
    # === WebSocket Configuration ===
    WEBSOCKET_ENABLED: bool = True
    WEBSOCKET_MAX_CONNECTIONS: int = 100
    WEBSOCKET_TIMEOUT: int = 300
    DEFAULT_WEBSOCKETS: bool = True
    WEBSOCKET_PING_INTERVAL: int = 20
    WEBSOCKET_PING_TIMEOUT: int = 10
    
    # === ASR Model Configuration ===
    ASR_ENGINE: str = "faster_whisper"
    ASR_MODEL: str = "base"
    ASR_DEVICE: str = "cpu"
    ASR_QUANTIZATION: str = "int8"
    SAMPLE_RATE: int = 16000
    MODEL_IDLE_TIMEOUT: int = 0
    
    # === Monitoring & Analytics ===
    ANALYTICS_ENABLED: bool = True
    LOGGING_LEVEL: str = "INFO"
    METRICS_ENABLED: bool = True
    HEALTH_CHECK_INTERVAL: int = 30
    LOG_RETENTION_DAYS: int = 7
    METRICS_RETENTION_HOURS: int = 24
    
    # === File Upload Configuration ===
    MAX_FILE_SIZE: str = "25MB"
    UPLOAD_MAX_SIZE: str = "25MB"
    UPLOAD_ALLOWED_TYPES: str = "audio/wav,audio/mp3,audio/m4a,audio/flac,audio/ogg"
    
    # === API Configuration ===
    CORS_ORIGINS: str = "*"
    REQUEST_TIMEOUT: int = 300
    MAX_REQUEST_SIZE: str = "100MB"
    
    # === Security Headers ===
    SECURE_HEADERS: bool = True
    HSTS_MAX_AGE: int = 31536000
    CONTENT_SECURITY_POLICY: str = "default-src 'self'"
    
    # === Rate Limiting ===
    RATE_LIMIT_ENABLED: bool = True
    RATE_LIMIT_REQUESTS: int = 100
    RATE_LIMIT_WINDOW: int = 3600
    
    # === Development Configuration ===
    DEV_REDIS_PASSWORD: str = "securepassword"
    LOG_SQL: bool = False
    
    class Config:
        env_file = ".env"
        case_sensitive = True
    
    @validator("LOGGING_LEVEL")
    def validate_logging_level(cls, v):
        valid_levels = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
        if v.upper() not in valid_levels:
            raise ValueError(f"LOGGING_LEVEL must be one of {valid_levels}")
        return v.upper()
    
    @validator("ASR_ENGINE")
    def validate_asr_engine(cls, v):
        valid_engines = ["faster_whisper", "openai_whisper", "whisperx"]
        if v not in valid_engines:
            raise ValueError(f"ASR_ENGINE must be one of {valid_engines}")
        return v
    
    @validator("ASR_DEVICE")
    def validate_asr_device(cls, v):
        valid_devices = ["cpu", "cuda", "auto"]
        if v not in valid_devices:
            raise ValueError(f"ASR_DEVICE must be one of {valid_devices}")
        return v
    
    @validator("ASR_QUANTIZATION")
    def validate_asr_quantization(cls, v):
        valid_quantizations = ["float32", "float16", "int8"]
        if v not in valid_quantizations:
            raise ValueError(f"ASR_QUANTIZATION must be one of {valid_quantizations}")
        return v
    
    def get_file_size_bytes(self, size_str: str) -> int:
        """Convert size string (e.g., '25MB') to bytes."""
        size_str = size_str.upper().strip()
        
        if size_str.endswith('KB'):
            return int(size_str[:-2]) * 1024
        elif size_str.endswith('MB'):
            return int(size_str[:-2]) * 1024 * 1024
        elif size_str.endswith('GB'):
            return int(size_str[:-2]) * 1024 * 1024 * 1024
        else:
            return int(size_str)
    
    def get_cors_origins(self) -> List[str]:
        """Get CORS origins as a list."""
        if self.CORS_ORIGINS == "*":
            return ["*"]
        return [origin.strip() for origin in self.CORS_ORIGINS.split(",")]
    
    def get_upload_allowed_types(self) -> List[str]:
        """Get allowed upload types as a list."""
        return [mime_type.strip() for mime_type in self.UPLOAD_ALLOWED_TYPES.split(",")]
    
    def is_development(self) -> bool:
        """Check if running in development mode."""
        return self.DEBUG or self.REDIS_URL.startswith("redis://localhost")
    
    def get_redis_config(self) -> Dict[str, Any]:
        """Get Redis configuration dictionary."""
        return {
            "url": self.REDIS_URL,
            "password": self.REDIS_PASSWORD,
            "token_db": self.REDIS_TOKEN_DB,
            "pubsub_db": self.REDIS_PUBSUB_DB,
            "max_connections": self.REDIS_MAX_CONNECTIONS,
            "timeout": self.REDIS_TIMEOUT,
            "enabled": self.REDIS_AUTH_ENABLED
        }
    
    def get_websocket_config(self) -> Dict[str, Any]:
        """Get WebSocket configuration dictionary."""
        return {
            "enabled": self.WEBSOCKET_ENABLED,
            "max_connections": self.WEBSOCKET_MAX_CONNECTIONS,
            "timeout": self.WEBSOCKET_TIMEOUT,
            "default_connections": self.DEFAULT_WEBSOCKETS,
            "ping_interval": self.WEBSOCKET_PING_INTERVAL,
            "ping_timeout": self.WEBSOCKET_PING_TIMEOUT
        }
    
    def get_asr_config(self) -> Dict[str, Any]:
        """Get ASR configuration dictionary."""
        return {
            "engine": self.ASR_ENGINE,
            "model": self.ASR_MODEL,
            "device": self.ASR_DEVICE,
            "quantization": self.ASR_QUANTIZATION,
            "sample_rate": self.SAMPLE_RATE,
            "idle_timeout": self.MODEL_IDLE_TIMEOUT
        }
    
    def get_monitoring_config(self) -> Dict[str, Any]:
        """Get monitoring configuration dictionary."""
        return {
            "analytics_enabled": self.ANALYTICS_ENABLED,
            "metrics_enabled": self.METRICS_ENABLED,
            "health_check_interval": self.HEALTH_CHECK_INTERVAL,
            "log_retention_days": self.LOG_RETENTION_DAYS,
            "metrics_retention_hours": self.METRICS_RETENTION_HOURS
        }
    
    def get_security_config(self) -> Dict[str, Any]:
        """Get security configuration dictionary."""
        return {
            "tls_enabled": self.TLS_ENABLED,
            "cert_path": self.TLS_CERT_PATH,
            "key_path": self.TLS_KEY_PATH,
            "auto_generate": self.TLS_AUTO_GENERATE,
            "cert_days": self.TLS_CERT_DAYS,
            "secure_headers": self.SECURE_HEADERS,
            "hsts_max_age": self.HSTS_MAX_AGE,
            "csp": self.CONTENT_SECURITY_POLICY
        }
    
    def validate_upstash_config(self) -> bool:
        """Validate Upstash Redis configuration."""
        if not self.REDIS_AUTH_ENABLED:
            return True  # Skip validation if auth is disabled
        
        # Check if using Upstash URL format
        if not self.REDIS_URL.startswith("redis://"):
            return False
        
        # Check if password is set
        if not self.REDIS_PASSWORD:
            return False
        
        return True


@lru_cache()
def get_settings() -> Settings:
    """Get application settings (cached)."""
    return Settings()


# Configuration validation function
def validate_configuration() -> Dict[str, Any]:
    """Validate entire configuration and return status."""
    settings = get_settings()
    validation_results = {
        "valid": True,
        "errors": [],
        "warnings": [],
        "config": {
            "app": {
                "name": settings.APP_NAME,
                "version": settings.APP_VERSION,
                "debug": settings.DEBUG,
                "development": settings.is_development()
            }
        }
    }
    
    # Validate Redis configuration
    if settings.REDIS_AUTH_ENABLED and not settings.validate_upstash_config():
        validation_results["errors"].append(
            "Invalid Upstash Redis configuration. Please check REDIS_URL and REDIS_PASSWORD."
        )
        validation_results["valid"] = False
    
    # Validate TLS configuration
    if settings.TLS_ENABLED:
        if not settings.TLS_AUTO_GENERATE:
            if not os.path.exists(settings.TLS_CERT_PATH):
                validation_results["errors"].append(f"TLS certificate not found: {settings.TLS_CERT_PATH}")
                validation_results["valid"] = False
            if not os.path.exists(settings.TLS_KEY_PATH):
                validation_results["errors"].append(f"TLS private key not found: {settings.TLS_KEY_PATH}")
                validation_results["valid"] = False
    
    # Add warnings for development mode
    if settings.is_development():
        validation_results["warnings"].append("Running in development mode")
    
    if settings.CORS_ORIGINS == "*":
        validation_results["warnings"].append("CORS allows all origins (*)")
    
    # Add configuration details
    validation_results["config"].update({
        "redis": settings.get_redis_config(),
        "websocket": settings.get_websocket_config(),
        "asr": settings.get_asr_config(),
        "monitoring": settings.get_monitoring_config(),
        "security": settings.get_security_config()
    })
    
    return validation_results