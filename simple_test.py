#!/usr/bin/env python3
"""
Simple test script for Whisper ASR service without Redis token management.
Tests basic functionality and WebSocket connections.
"""

import asyncio
import json
import aiohttp
import ssl
import websockets
from pathlib import Path

# SSL context for self-signed certificates
ssl_context = ssl.create_default_context()
ssl_context.check_hostname = False
ssl_context.verify_mode = ssl.CERT_NONE

BASE_URL = "https://localhost:9443"
WS_URL = "wss://localhost:9443"

async def test_health_endpoint():
    """Test the health endpoint."""
    print("🏥 Testing Health Endpoint...")
    
    try:
        connector = aiohttp.TCPConnector(ssl=ssl_context)
        async with aiohttp.ClientSession(connector=connector) as session:
            async with session.get(f"{BASE_URL}/health") as response:
                if response.status == 200:
                    data = await response.json()
                    print(f"✅ Health check passed: {data['status']}")
                    return True
                else:
                    print(f"❌ Health check failed: {response.status}")
                    return False
    except Exception as e:
        print(f"❌ Health check error: {e}")
        return False

async def test_transcription_with_auth():
    """Test transcription endpoint with various auth attempts."""
    print("\n🎙️  Testing Transcription Endpoint...")
    
    # Check if test.mp3 exists
    test_file = Path("test.mp3")
    if not test_file.exists():
        print("❌ test.mp3 file not found")
        return False
    
    connector = aiohttp.TCPConnector(ssl=ssl_context)
    async with aiohttp.ClientSession(connector=connector) as session:
        
        # Test without auth first (should fail)
        print("🔒 Testing without authentication...")
        with open("test.mp3", "rb") as f:
            form_data = aiohttp.FormData()
            form_data.add_field('audio_file', f, filename='test.mp3', content_type='audio/mp3')
            form_data.add_field('task', 'transcribe')
            form_data.add_field('language', 'en')
            
            try:
                async with session.post(f"{BASE_URL}/asr", data=form_data) as response:
                    if response.status == 401:
                        print("✅ Authentication correctly required")
                    else:
                        print(f"⚠️  Unexpected status without auth: {response.status}")
                        error_text = await response.text()
                        print(f"   Response: {error_text}")
            except Exception as e:
                print(f"❌ Error testing without auth: {e}")
    
    return True

async def test_websocket_connection():
    """Test WebSocket connection."""
    print("\n🔌 Testing WebSocket Connection...")
    
    # Test connection without auth (should fail gracefully)
    ws_url = f"{WS_URL}/ws/test-connection"
    print(f"Attempting to connect to: {ws_url}")
    
    try:
        async with websockets.connect(ws_url, ssl=ssl_context) as websocket:
            print("⚠️  WebSocket connected without authentication (unexpected)")
            
            # Try to send a test message
            test_message = {"type": "test", "message": "Hello WebSocket"}
            await websocket.send(json.dumps(test_message))
            
            # Wait for response
            try:
                response = await asyncio.wait_for(websocket.recv(), timeout=5.0)
                print(f"📥 Received: {response}")
            except asyncio.TimeoutError:
                print("⏰ No response received (timeout)")
                
    except websockets.exceptions.ConnectionClosedError as e:
        print(f"✅ WebSocket correctly closed: {e.code} - {e.reason}")
    except Exception as e:
        print(f"✅ WebSocket connection failed as expected: {type(e).__name__}: {e}")

async def test_endpoints_requiring_auth():
    """Test various endpoints that require authentication."""
    print("\n🔐 Testing Authentication-Required Endpoints...")
    
    protected_endpoints = [
        "/asr/models",
        "/metrics", 
        "/config"
    ]
    
    connector = aiohttp.TCPConnector(ssl=ssl_context)
    async with aiohttp.ClientSession(connector=connector) as session:
        for endpoint in protected_endpoints:
            try:
                async with session.get(f"{BASE_URL}{endpoint}") as response:
                    if response.status == 401:
                        print(f"✅ {endpoint} correctly requires authentication")
                    else:
                        print(f"⚠️  {endpoint} returned status: {response.status}")
                        
            except Exception as e:
                print(f"❌ Error testing {endpoint}: {e}")

async def main():
    """Run all tests."""
    print("=" * 80)
    print("🎯 SIMPLE WHISPER ASR SERVICE TESTS")
    print("=" * 80)
    
    # Run tests in sequence
    await test_health_endpoint()
    await test_endpoints_requiring_auth()
    await test_transcription_with_auth()
    await test_websocket_connection()
    
    print("\n" + "=" * 80)
    print("✅ ALL TESTS COMPLETED")
    print("=" * 80)

if __name__ == "__main__":
    asyncio.run(main())