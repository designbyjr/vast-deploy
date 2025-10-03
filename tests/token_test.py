#!/usr/bin/env python3
"""
Production-safe token test using environment variables.
"""

import os
import requests
import json
import uuid
from datetime import datetime, timezone, timedelta

def create_token_with_rest():
    """Create a test token using Upstash REST API with environment credentials."""
    
    # Get credentials from environment
    redis_url = os.getenv('REDIS_URL', '')
    upstash_token = os.getenv('REDIS_PASSWORD', '')
    
    # Parse Upstash URL from Redis URL
    upstash_url = None
    if redis_url and '@' in redis_url:
        try:
            hostname = redis_url.split('@')[-1].split(':')[0]
            upstash_url = f"https://{hostname}"
        except Exception as e:
            print(f"❌ Failed to parse REDIS_URL: {e}")
            return None
    
    if not upstash_url or not upstash_token:
        print("❌ REDIS_URL and REDIS_PASSWORD environment variables must be set")
        return None
    
    # Generate token
    token = str(uuid.uuid4())
    
    # Create token data
    expires_at = datetime.now(timezone.utc) + timedelta(hours=2)
    token_data = {
        "user_id": "test-speech-user",
        "permissions": ["read", "write", "transcribe", "websocket"],
        "created_at": datetime.now(timezone.utc).isoformat(),
        "expires_at": expires_at.isoformat(),
        "last_used": datetime.now(timezone.utc).isoformat()
    }
    
    # Store in Upstash Redis using REST API
    headers = {
        "Authorization": f"Bearer {upstash_token}",
        "Content-Type": "application/json"
    }
    
    key = f"auth:token:{token}"
    ttl_seconds = int(2 * 3600)  # 2 hours
    
    # Use SETEX command via REST API
    response = requests.post(
        f"{upstash_url}/setex/{key}/{ttl_seconds}",
        headers=headers,
        data=json.dumps(token_data)
    )
    
    if response.status_code == 200:
        print(f"✅ Token created successfully: {token}")
        print(f"   User: {token_data['user_id']}")
        print(f"   Permissions: {token_data['permissions']}")
        print(f"   Expires: {expires_at.strftime('%Y-%m-%d %H:%M:%S UTC')}")
        print(f"\n🔑 Use this token: {token}")
        return token
    else:
        print(f"❌ Failed to create token: {response.status_code} - {response.text}")
        return None

def test_api_with_token(token):
    """Test the API with the created token."""
    service_url = os.getenv('SERVICE_URL', 'https://localhost:9443')
    
    # Test the health endpoint first (no auth)
    print(f"\n🏥 Testing health endpoint at {service_url}...")
    try:
        response = requests.get(f"{service_url}/health", verify=False)
        if response.status_code == 200:
            print(f"✅ Health check passed: {response.json().get('status')}")
        else:
            print(f"❌ Health check failed: {response.status_code}")
    except Exception as e:
        print(f"❌ Health check error: {e}")
    
    # Test authenticated endpoint
    print("\n🔐 Testing authenticated endpoint...")
    headers = {"Authorization": f"Bearer {token}"}
    try:
        response = requests.get(f"{service_url}/asr/models", headers=headers, verify=False)
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Authentication successful!")
            print(f"   Current model: {data.get('current_model')}")
            print(f"   Engine: {data.get('current_engine')}")
            print(f"   Device: {data.get('device')}")
        else:
            print(f"❌ Authentication failed: {response.status_code} - {response.text}")
    except Exception as e:
        print(f"❌ Authentication test error: {e}")

if __name__ == "__main__":
    print("🎯 Production-Safe Token Test for Whisper ASR Service")
    print("=" * 60)
    print("📋 Required environment variables:")
    print("   - REDIS_URL: Redis connection URL with credentials")
    print("   - REDIS_PASSWORD: Redis authentication token")
    print("   - SERVICE_URL: ASR service URL (default: https://localhost:9443)")
    print("=" * 60)
    
    # Create token
    token = create_token_with_rest()
    
    if token:
        # Test API
        test_api_with_token(token)
        
        print("\n" + "=" * 60)
        print("✅ Tests completed!")
        print(f"📋 Bearer Token for manual testing: {token}")
    else:
        print("❌ Failed to create token")