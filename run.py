#!/usr/bin/env python3
"""
Startup script for Secure Whisper ASR Service
"""

import os
import sys
import asyncio
import logging
from pathlib import Path

# Add app directory to Python path
app_dir = Path(__file__).parent
sys.path.insert(0, str(app_dir))

from app.config import get_settings

def main():
    """Main startup function."""
    print("🎤 Starting Secure Whisper ASR Service...")
    print("=" * 60)
    
    # Load settings
    settings = get_settings()
    
    # Print configuration
    print(f"📊 Service: {settings.APP_NAME} v{settings.APP_VERSION}")
    print(f"🌐 Host: {settings.HOST}:{settings.PORT}")
    print(f"🔐 TLS: {'Enabled' if settings.TLS_ENABLED else 'Disabled'}")
    print(f"🔌 WebSocket: {'Enabled' if settings.WEBSOCKET_ENABLED else 'Disabled'}")
    print(f"🔑 Authentication: {'Enabled' if settings.REDIS_AUTH_ENABLED else 'Disabled'}")
    print(f"📈 Monitoring: {'Enabled' if settings.METRICS_ENABLED else 'Disabled'}")
    print(f"🐛 Debug: {'Enabled' if settings.DEBUG else 'Disabled'}")
    print("=" * 60)
    
    # Import and run the app
    try:
        import uvicorn
        from app.main import app
        
        # SSL configuration
        ssl_keyfile = settings.TLS_KEY_PATH if settings.TLS_ENABLED else None
        ssl_certfile = settings.TLS_CERT_PATH if settings.TLS_ENABLED else None
        
        # Check if certs directory exists
        if settings.TLS_ENABLED:
            cert_dir = Path(settings.TLS_CERT_PATH).parent
            cert_dir.mkdir(parents=True, exist_ok=True)
            print(f"📜 TLS certificates will be stored in: {cert_dir}")
        
        print(f"🚀 Starting server on {'https' if settings.TLS_ENABLED else 'http'}://{settings.HOST}:{settings.PORT}")
        print(f"📚 API Documentation: {'https' if settings.TLS_ENABLED else 'http'}://{settings.HOST}:{settings.PORT}/docs")
        print("=" * 60)
        
        # Run the server
        uvicorn.run(
            app,
            host=settings.HOST,
            port=settings.PORT,
            ssl_keyfile=ssl_keyfile,
            ssl_certfile=ssl_certfile,
            log_level=settings.LOGGING_LEVEL.lower(),
            reload=settings.DEBUG,
            workers=1,
            access_log=True,
            use_colors=True,
        )
        
    except KeyboardInterrupt:
        print("\n⛔ Server stopped by user")
    except Exception as e:
        print(f"❌ Error starting server: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()