#!/usr/bin/env python3
"""
Comprehensive Authentication and WebSocket Tests for Whisper ASR Service
Tests Redis bearer token authentication, WebSocket connections, and TLS functionality.
"""

import asyncio
import json
import os
import sys
import websockets
import ssl
import aiohttp
import uuid
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, Optional

# Add project root to Python path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from tests.redis_token_manager import RedisTokenManager


class WhisperASRTester:
    """Comprehensive tester for Whisper ASR service authentication and WebSocket functionality."""
    
    def __init__(self, base_url: str, redis_url: str, redis_password: str, use_tls: bool = False):
        self.base_url = base_url
        self.redis_url = redis_url
        self.redis_password = redis_password
        self.use_tls = use_tls
        self.token_manager = RedisTokenManager(redis_url, redis_password)
        self.test_token = None
        
        # Configure SSL context for self-signed certificates
        self.ssl_context = ssl.create_default_context()
        self.ssl_context.check_hostname = False
        self.ssl_context.verify_mode = ssl.CERT_NONE
        
    async def setup(self):
        """Initialize the tester and create test tokens."""
        print("🚀 Setting up Whisper ASR Service Tester...")
        print(f"📊 Base URL: {self.base_url}")
        print(f"🔐 TLS Enabled: {self.use_tls}")
        print(f"🔑 Redis URL: {self.redis_url}")
        
        # Connect to Redis
        if not await self.token_manager.connect():
            print("❌ Failed to connect to Redis")
            return False
        
        # Create a test token
        print("\n📝 Creating test authentication token...")
        self.test_token = await self.token_manager.create_token(
            user_id="test-user-speech",
            permissions=["read", "write", "transcribe", "websocket"],
            expires_in_hours=2
        )
        
        return True
    
    async def cleanup(self):
        """Clean up resources."""
        print("\n🧹 Cleaning up...")
        if self.test_token:
            await self.token_manager.revoke_token(self.test_token)
        await self.token_manager.close()
    
    async def test_health_endpoint(self):
        """Test the health endpoint (no auth required)."""
        print("\n🏥 Testing Health Endpoint...")
        
        try:
            connector = aiohttp.TCPConnector(ssl=self.ssl_context if self.use_tls else False)
            async with aiohttp.ClientSession(connector=connector) as session:
                async with session.get(f"{self.base_url}/health") as response:
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
    
    async def test_authentication_required_endpoints(self):
        """Test that protected endpoints require authentication."""
        print("\n🔐 Testing Authentication Requirements...")
        
        protected_endpoints = [
            "/asr/models",
            "/metrics", 
            "/config"
        ]
        
        connector = aiohttp.TCPConnector(ssl=self.ssl_context if self.use_tls else False)
        async with aiohttp.ClientSession(connector=connector) as session:
            for endpoint in protected_endpoints:
                try:
                    # Test without token
                    async with session.get(f"{self.base_url}{endpoint}") as response:
                        if response.status == 401:
                            print(f"✅ {endpoint} correctly requires authentication")
                        else:
                            print(f"❌ {endpoint} should require authentication (got {response.status})")
                            
                except Exception as e:
                    print(f"❌ Error testing {endpoint}: {e}")
    
    async def test_bearer_token_authentication(self):
        """Test API endpoints with bearer token authentication."""
        print("\n🎫 Testing Bearer Token Authentication...")
        
        headers = {"Authorization": f"Bearer {self.test_token}"}
        connector = aiohttp.TCPConnector(ssl=self.ssl_context if self.use_tls else False)
        
        async with aiohttp.ClientSession(connector=connector) as session:
            # Test /asr/models endpoint
            try:
                async with session.get(f"{self.base_url}/asr/models", headers=headers) as response:
                    if response.status == 200:
                        data = await response.json()
                        print(f"✅ /asr/models authenticated successfully")
                        print(f"   Current model: {data.get('current_model')}")
                        print(f"   Available models: {len(data.get('available_models', []))}")
                        
                        # Verify v3 models are included
                        available_models = data.get('available_models', [])
                        v3_models = [m for m in available_models if 'v3' in m or 'turbo' in m]
                        if v3_models:
                            print(f"   V3 models found: {v3_models}")
                        else:
                            print("   ⚠️  No V3 models found in available models")
                    else:
                        print(f"❌ /asr/models authentication failed: {response.status}")
                        error_text = await response.text()
                        print(f"   Error: {error_text}")
                        
            except Exception as e:
                print(f"❌ Error testing /asr/models: {e}")
            
            # Test /config endpoint
            try:
                async with session.get(f"{self.base_url}/config", headers=headers) as response:
                    if response.status == 200:
                        data = await response.json()
                        print(f"✅ /config authenticated successfully")
                        print(f"   Configuration valid: {data.get('valid', False)}")
                    else:
                        print(f"❌ /config authentication failed: {response.status}")
            except Exception as e:
                print(f"❌ Error testing /config: {e}")
    
    async def test_invalid_token(self):
        """Test API with invalid bearer token."""
        print("\n🚫 Testing Invalid Token Rejection...")
        
        invalid_headers = {"Authorization": "Bearer invalid-token-12345"}
        connector = aiohttp.TCPConnector(ssl=self.ssl_context if self.use_tls else False)
        
        async with aiohttp.ClientSession(connector=connector) as session:
            try:
                async with session.get(f"{self.base_url}/asr/models", headers=invalid_headers) as response:
                    if response.status == 401:
                        print("✅ Invalid token correctly rejected")
                    else:
                        print(f"❌ Invalid token should be rejected (got {response.status})")
            except Exception as e:
                print(f"❌ Error testing invalid token: {e}")
    
    async def test_websocket_connection_without_auth(self):
        """Test WebSocket connection without authentication (should fail)."""
        print("\n🔌 Testing WebSocket Without Authentication...")
        
        ws_url = self.base_url.replace("http", "ws") + "/ws/test-connection"
        
        try:
            if self.use_tls:
                async with websockets.connect(ws_url, ssl=self.ssl_context) as websocket:
                    # This should not work without auth
                    print("❌ WebSocket connected without authentication (should fail)")
            else:
                async with websockets.connect(ws_url) as websocket:
                    print("❌ WebSocket connected without authentication (should fail)")
        except websockets.exceptions.ConnectionClosedError as e:
            if e.code in [1008, 4001]:  # Policy Violation or custom auth error
                print("✅ WebSocket correctly rejected without authentication")
            else:
                print(f"⚠️  WebSocket closed with unexpected code: {e.code}")
        except Exception as e:
            print(f"✅ WebSocket connection failed as expected: {type(e).__name__}")
    
    async def test_websocket_with_authentication(self):
        """Test WebSocket connection with bearer token authentication."""
        print("\n🔐 Testing Authenticated WebSocket Connection...")
        
        ws_url = self.base_url.replace("http", "ws") + "/ws/test-speech-connection"
        headers = {"Authorization": f"Bearer {self.test_token}"}
        
        try:
            # Connect with authentication
            if self.use_tls:
                async with websockets.connect(ws_url, extra_headers=headers, ssl=self.ssl_context) as websocket:
                    await self._test_websocket_functionality(websocket)
            else:
                async with websockets.connect(ws_url, extra_headers=headers) as websocket:
                    await self._test_websocket_functionality(websocket)
                    
        except websockets.exceptions.ConnectionClosedError as e:
            print(f"⚠️  WebSocket closed: {e.code} - {e.reason}")
        except Exception as e:
            print(f"❌ WebSocket error: {type(e).__name__}: {e}")
    
    async def _test_websocket_functionality(self, websocket):
        """Test basic WebSocket functionality."""
        print("✅ WebSocket connected with authentication")
        
        # Send test message
        test_message = {
            "type": "test",
            "message": "Hello from authenticated client",
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        
        await websocket.send(json.dumps(test_message))
        print("📤 Sent test message to WebSocket")
        
        # Wait for response
        try:
            response = await asyncio.wait_for(websocket.recv(), timeout=5.0)
            response_data = json.loads(response)
            print(f"📥 Received WebSocket response: {response_data.get('type', 'unknown')}")
            
            # Send ping
            ping_message = {"type": "ping", "timestamp": datetime.now(timezone.utc).isoformat()}
            await websocket.send(json.dumps(ping_message))
            
            # Wait for pong
            pong_response = await asyncio.wait_for(websocket.recv(), timeout=5.0)
            pong_data = json.loads(pong_response)
            if pong_data.get("type") == "pong":
                print("✅ WebSocket ping/pong successful")
            
        except asyncio.TimeoutError:
            print("⚠️  WebSocket response timeout (may be normal)")
        except json.JSONDecodeError:
            print("⚠️  Received non-JSON WebSocket message")
    
    async def test_speech_audio_upload(self):
        """Test audio file upload with speech-specific validation."""
        print("\n🎙️  Testing Speech Audio Upload...")
        
        headers = {"Authorization": f"Bearer {self.test_token}"}
        
        # Create a mock speech audio file (WAV header)
        speech_audio_data = self._create_mock_speech_wav()
        
        connector = aiohttp.TCPConnector(ssl=self.ssl_context if self.use_tls else False)
        async with aiohttp.ClientSession(connector=connector) as session:
            # Test speech audio upload
            form_data = aiohttp.FormData()
            form_data.add_field('audio_file', speech_audio_data, 
                              filename='test_speech.wav', 
                              content_type='audio/wav')
            form_data.add_field('task', 'transcribe')
            form_data.add_field('language', 'en')
            
            try:
                async with session.post(f"{self.base_url}/asr", 
                                      headers=headers, 
                                      data=form_data) as response:
                    if response.status == 200:
                        data = await response.json()
                        print("✅ Speech audio upload successful")
                        print(f"   Model used: {data.get('model')}")
                        print(f"   Language detected: {data.get('language')}")
                        print(f"   Processing time: {data.get('processing_time', 0):.3f}s")
                        
                        # Check if response indicates speech processing
                        transcription = data.get('transcription', '')
                        if 'speech' in transcription.lower() or 'whisper' in transcription.lower():
                            print("✅ Response indicates speech processing")
                        
                    else:
                        error_text = await response.text()
                        print(f"❌ Speech audio upload failed: {response.status}")
                        print(f"   Error: {error_text}")
                        
            except Exception as e:
                print(f"❌ Error testing speech upload: {e}")
    
    def _create_mock_speech_wav(self) -> bytes:
        """Create a minimal valid WAV file header for testing."""
        # This creates a minimal WAV file with proper headers
        # In real use, you'd upload actual speech audio files
        wav_header = (
            b'RIFF'         # ChunkID
            b'\x24\x00\x00\x00'  # ChunkSize (36 bytes)
            b'WAVE'         # Format
            b'fmt '         # Subchunk1ID
            b'\x10\x00\x00\x00'  # Subchunk1Size (16 bytes)
            b'\x01\x00'     # AudioFormat (PCM)
            b'\x01\x00'     # NumChannels (mono)
            b'\x40\x1f\x00\x00'  # SampleRate (8000 Hz)
            b'\x40\x1f\x00\x00'  # ByteRate
            b'\x01\x00'     # BlockAlign
            b'\x08\x00'     # BitsPerSample (8-bit)
            b'data'         # Subchunk2ID
            b'\x00\x00\x00\x00'  # Subchunk2Size (0 - no actual audio data)
        )
        return wav_header
    
    async def run_all_tests(self):
        """Run all tests in sequence."""
        print("=" * 80)
        print("🎯 WHISPER ASR SERVICE COMPREHENSIVE TESTS")
        print("=" * 80)
        
        if not await self.setup():
            return False
        
        try:
            # Test sequence
            await self.test_health_endpoint()
            await self.test_authentication_required_endpoints()
            await self.test_bearer_token_authentication()
            await self.test_invalid_token()
            await self.test_websocket_connection_without_auth()
            await self.test_websocket_with_authentication()
            await self.test_speech_audio_upload()
            
            print("\n" + "=" * 80)
            print("✅ ALL TESTS COMPLETED")
            print("=" * 80)
            
            return True
            
        finally:
            await self.cleanup()


async def main():
    """Main test runner."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Whisper ASR Service Authentication & WebSocket Tests")
    parser.add_argument("--base-url", default="http://localhost:9443", 
                       help="Base URL of the Whisper ASR service")
    parser.add_argument("--redis-url", required=True, 
                       help="Redis URL for authentication")
    parser.add_argument("--redis-password", required=True, 
                       help="Redis password")
    parser.add_argument("--tls", action="store_true", 
                       help="Use TLS/HTTPS for connections")
    
    args = parser.parse_args()
    
    # Update base URL protocol based on TLS setting
    if args.tls and args.base_url.startswith("http://"):
        args.base_url = args.base_url.replace("http://", "https://")
    
    # Run tests
    tester = WhisperASRTester(args.base_url, args.redis_url, args.redis_password, args.tls)
    success = await tester.run_all_tests()
    
    return 0 if success else 1


if __name__ == "__main__":
    import sys
    sys.exit(asyncio.run(main()))