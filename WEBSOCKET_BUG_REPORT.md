# WebSocket Authentication Bug Report

## Issue Summary
WebSocket authentication is failing with a `'Query' object is not subscriptable` error, preventing authenticated WebSocket connections from working properly.

## Environment
- Container: whisper-asr-secure running on HTTPS port 9443
- Redis Authentication: Upstash Redis (working correctly for HTTP APIs)
- WebSocket URL: `wss://localhost:9443/ws/{connection_id}`

## Problem Description

### Symptoms
- WebSocket connections can be established but are immediately closed with code `4001 - Invalid authentication token`
- Container logs show: `'Query' object is not subscriptable` error in `app.middleware.auth`
- HTTP API authentication works perfectly with the same Bearer tokens
- WebSocket welcome messages are sent before authentication failure

### Error Logs
```
2025-10-03 22:32:14,163 - app.middleware.auth - ERROR - Redis token validation error: 'Query' object is not subscriptable
2025-10-03 22:32:14,163 - app.middleware.auth - ERROR - Failed to log authentication event: 'Query' object is not subscriptable
INFO:     connection closed
```

### Working vs Broken
✅ **Working**: HTTP API with Bearer token authentication
```bash
curl -k -H "Authorization: Bearer 68c8e154-8f25-43bf-90ef-0b0dbdf1a75e" https://localhost:9443/asr/models
# Returns: 200 OK with model information
```

❌ **Broken**: WebSocket with same Bearer token
```python
# Both query parameter and header methods fail
websockets.connect("wss://localhost:9443/ws/test?token=68c8e154-8f25-43bf-90ef-0b0dbdf1a75e")
# Results in: 4001 - Invalid authentication token
```

## Root Cause Analysis

The issue appears to be in the WebSocket authentication handler at `app/websocket/handler.py:285`:

```python
async def handle_websocket_connection(websocket: WebSocket, connection_id: str, 
                                    token: Optional[str] = Query(None)):
```

The `Query(None)` parameter declaration is causing issues when the authentication middleware tries to process the token parameter.

### Code Locations
1. **WebSocket Handler**: `app/websocket/handler.py` lines 284-295
2. **Authentication Middleware**: `app/middleware/auth.py` - token validation functions
3. **Error occurs in**: `verify_websocket_auth()` or `validate_token()` methods

## Test Cases

### Test 1: Query Parameter Authentication
```python
# URI: wss://localhost:9443/ws/test-auth-connection?token={BEARER_TOKEN}
# Expected: Successful connection
# Actual: 4001 - Invalid authentication token
```

### Test 2: Header Authentication  
```python
# Headers: {"Authorization": f"Bearer {BEARER_TOKEN}"}
# URI: wss://localhost:9443/ws/test-auth-connection
# Expected: Successful connection  
# Actual: 4001 - Invalid authentication token
```

### Test 3: HTTP API (Control Test)
```bash
curl -k -H "Authorization: Bearer 68c8e154-8f25-43bf-90ef-0b0dbdf1a75e" https://localhost:9443/asr/models
# Result: ✅ SUCCESS - Returns model information
```

## Expected Behavior
1. WebSocket should authenticate using Bearer token from query parameter or Authorization header
2. Valid tokens should allow WebSocket connection to remain open
3. Connection should receive welcome message and respond to ping/pong
4. ASR requests should be processed via WebSocket

## Impact
- **High**: WebSocket functionality is completely broken for authenticated users
- Prevents real-time ASR processing via WebSocket
- Blocks integration testing of MP3 file transcription via WebSocket
- Users cannot use WebSocket features with authentication enabled

## Suggested Fix
1. Fix the `Query()` parameter handling in `handle_websocket_connection()`
2. Ensure token extraction works for both query parameters and headers
3. Verify token validation uses the same Redis authentication as HTTP APIs
4. Add proper error handling for authentication failures

## Test Files Available
- `websocket_test_with_auth.py` - Comprehensive WebSocket authentication test
- `simple_test.py` - Basic container health validation
- `tests/token_test.py` - Redis token creation and validation
- Valid Bearer token for testing: `68c8e154-8f25-43bf-90ef-0b0dbdf1a75e`

## Priority
**High** - WebSocket authentication is a core feature that needs to work for production deployment.