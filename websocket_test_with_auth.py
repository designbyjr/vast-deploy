#!/usr/bin/env python3
"""
WebSocket Test with Authentication and MP3 File Transcription
Tests WebSocket functionality with Bearer token authentication
"""

import asyncio
import websockets
import json
import ssl
import base64
import sys
from datetime import datetime

# Configuration
BEARER_TOKEN = "68c8e154-8f25-43bf-90ef-0b0dbdf1a75e"
WEBSOCKET_URL = "wss://localhost:9443"
MP3_FILE = "test.mp3"

class AuthenticatedWebSocketTester:
    def __init__(self):
        self.ssl_context = ssl.create_default_context()
        self.ssl_context.check_hostname = False
        self.ssl_context.verify_mode = ssl.CERT_NONE
        
    def log(self, message, status="INFO"):
        timestamp = datetime.now().strftime("%H:%M:%S.%f")[:-3]
        status_emoji = {"INFO": "ℹ️", "SUCCESS": "✅", "ERROR": "❌", "WARN": "⚠️"}
        print(f"[{timestamp}] {status_emoji.get(status, 'ℹ️')} {message}")
    
    async def test_authenticated_websocket_connection(self):
        """Test WebSocket connection with Bearer token authentication"""
        self.log("Testing authenticated WebSocket connection...")
        
        try:
            # Pass token as query parameter instead of header
            uri = f"{WEBSOCKET_URL}/ws/test-auth-connection?token={BEARER_TOKEN}"
            
            self.log(f"Connecting to: {uri}")
            self.log(f"Using token: {BEARER_TOKEN[:20]}...")
            
            async with websockets.connect(uri, ssl=self.ssl_context) as websocket:
                self.log("WebSocket connection established with authentication", "SUCCESS")
                
                # Wait for welcome message
                try:
                    welcome_message = await asyncio.wait_for(websocket.recv(), timeout=10)
                    welcome_data = json.loads(welcome_message)
                    
                    self.log(f"Welcome message received: {welcome_data.get('type')}", "SUCCESS")
                    if 'connection_id' in welcome_data:
                        self.log(f"Connection ID: {welcome_data['connection_id']}")
                    
                except asyncio.TimeoutError:
                    self.log("No welcome message received within timeout", "WARN")
                except json.JSONDecodeError as e:
                    self.log(f"Invalid JSON in welcome message: {e}", "ERROR")
                
                return websocket
                
        except websockets.exceptions.ConnectionClosedError as e:
            self.log(f"WebSocket connection closed: {e.code} - {e.reason}", "ERROR")
            return None
        except Exception as e:
            self.log(f"WebSocket connection failed: {e}", "ERROR")
            return None
    
    async def test_ping_pong_with_auth(self, websocket):
        """Test ping/pong messages with authenticated connection"""
        self.log("Testing ping/pong with authenticated connection...")
        
        try:
            # Send ping message
            ping_msg = {
                "type": "ping",
                "timestamp": datetime.now().isoformat(),
                "data": "test-ping-with-auth"
            }
            
            await websocket.send(json.dumps(ping_msg))
            self.log("Sent authenticated ping message")
            
            # Wait for pong response
            try:
                response = await asyncio.wait_for(websocket.recv(), timeout=10)
                response_data = json.loads(response)
                
                if response_data.get("type") == "pong":
                    self.log("Received pong response", "SUCCESS")
                    return True
                else:
                    self.log(f"Unexpected response to ping: {response_data}", "WARN")
                    return False
                    
            except asyncio.TimeoutError:
                self.log("No pong response received", "ERROR")
                return False
            except json.JSONDecodeError:
                self.log("Invalid JSON in pong response", "ERROR")
                return False
                
        except Exception as e:
            self.log(f"Ping/pong test failed: {e}", "ERROR")
            return False
    
    async def test_mp3_transcription_via_websocket(self, websocket):
        """Test MP3 file transcription via WebSocket"""
        self.log(f"Testing MP3 transcription via WebSocket: {MP3_FILE}")
        
        try:
            # Read the MP3 file
            with open(MP3_FILE, 'rb') as f:
                audio_data = f.read()
                audio_b64 = base64.b64encode(audio_data).decode()
            
            self.log(f"Loaded MP3 file: {len(audio_data)} bytes")
            
            # Prepare ASR request
            asr_request = {
                "type": "asr_request",
                "request_id": f"test-mp3-{int(datetime.now().timestamp())}",
                "audio_data": audio_b64,
                "audio_format": "mp3",
                "task": "transcribe",
                "language": "en",
                "model": "large-v2",
                "timestamp": datetime.now().isoformat()
            }
            
            # Send ASR request
            await websocket.send(json.dumps(asr_request))
            self.log("Sent MP3 transcription request via WebSocket")
            
            # Wait for ASR response
            try:
                response = await asyncio.wait_for(websocket.recv(), timeout=60)
                response_data = json.loads(response)
                
                if response_data.get("type") == "asr_response":
                    self.log("Received ASR response", "SUCCESS")
                    self.log(f"Request ID: {response_data.get('request_id')}")
                    self.log(f"Transcription: {response_data.get('transcription', 'N/A')}")
                    self.log(f"Language: {response_data.get('language', 'N/A')}")
                    self.log(f"Processing time: {response_data.get('processing_time', 'N/A')}s")
                    return True
                elif response_data.get("type") == "error":
                    self.log(f"ASR error response: {response_data.get('message')}", "ERROR")
                    return False
                else:
                    self.log(f"Unexpected ASR response: {response_data}", "WARN")
                    return False
                    
            except asyncio.TimeoutError:
                self.log("No ASR response received within timeout", "ERROR")
                return False
            except json.JSONDecodeError:
                self.log("Invalid JSON in ASR response", "ERROR")
                return False
                
        except FileNotFoundError:
            self.log(f"MP3 file not found: {MP3_FILE}", "ERROR")
            return False
        except Exception as e:
            self.log(f"MP3 transcription test failed: {e}", "ERROR")
            return False
    
    async def test_status_request(self, websocket):
        """Test connection status request"""
        self.log("Testing status request...")
        
        try:
            status_request = {
                "type": "status_request",
                "timestamp": datetime.now().isoformat()
            }
            
            await websocket.send(json.dumps(status_request))
            self.log("Sent status request")
            
            try:
                response = await asyncio.wait_for(websocket.recv(), timeout=10)
                response_data = json.loads(response)
                
                if response_data.get("type") == "status_response":
                    self.log("Received status response", "SUCCESS")
                    self.log(f"Connection status: {response_data.get('status')}")
                    return True
                else:
                    self.log(f"Unexpected status response: {response_data}", "WARN")
                    return False
                    
            except asyncio.TimeoutError:
                self.log("No status response received", "ERROR")
                return False
                
        except Exception as e:
            self.log(f"Status request test failed: {e}", "ERROR")
            return False

async def main():
    """Main test execution"""
    print("=" * 80)
    print("🎯 AUTHENTICATED WEBSOCKET TEST WITH MP3 TRANSCRIPTION")
    print("=" * 80)
    
    tester = AuthenticatedWebSocketTester()
    
    # Test authenticated connection
    websocket = await tester.test_authenticated_websocket_connection()
    
    if websocket is None:
        print("\n❌ Failed to establish authenticated WebSocket connection")
        return False
    
    try:
        # Run tests with the authenticated connection
        tests_results = []
        
        # Test 1: Ping/Pong
        result1 = await tester.test_ping_pong_with_auth(websocket)
        tests_results.append(("Ping/Pong", result1))
        
        # Test 2: Status Request
        result2 = await tester.test_status_request(websocket)
        tests_results.append(("Status Request", result2))
        
        # Test 3: MP3 Transcription
        result3 = await tester.test_mp3_transcription_via_websocket(websocket)
        tests_results.append(("MP3 Transcription", result3))
        
        # Summary
        print("\n" + "=" * 80)
        print("📊 TEST RESULTS SUMMARY")
        print("=" * 80)
        
        passed = 0
        for test_name, result in tests_results:
            status = "✅ PASSED" if result else "❌ FAILED"
            print(f"{test_name}: {status}")
            if result:
                passed += 1
        
        print(f"\nOverall: {passed}/{len(tests_results)} tests passed")
        
        if passed == len(tests_results):
            print("🎉 All tests passed!")
            return True
        else:
            print("⚠️  Some tests failed")
            return False
        
    finally:
        await websocket.close()
        print("WebSocket connection closed")

if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)