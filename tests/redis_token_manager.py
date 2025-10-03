#!/usr/bin/env python3
"""
Redis Token Manager for Whisper ASR Service
Manages bearer tokens stored in Upstash Redis for authentication testing.
"""

import json
import asyncio
import uuid
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, List, Optional
import redis.asyncio as aioredis
import os
import sys

# Add project root to Python path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.config import get_settings

class RedisTokenManager:
    """Manages authentication tokens in Upstash Redis."""
    
    def __init__(self, redis_url: str, password: str):
        self.redis_url = redis_url
        self.password = password
        self.client = None
        
    async def connect(self):
        """Connect to Redis."""
        try:
            self.client = aioredis.from_url(
                self.redis_url,
                password=self.password,
                decode_responses=True,
                db=0  # Use token database
            )
            await self.client.ping()
            print(f"✅ Connected to Redis at {self.redis_url.split('@')[-1] if '@' in self.redis_url else self.redis_url}")
            return True
        except Exception as e:
            print(f"❌ Failed to connect to Redis: {e}")
            return False
    
    async def close(self):
        """Close Redis connection."""
        if self.client:
            await self.client.close()
    
    async def create_token(
        self, 
        user_id: str = "test-user", 
        permissions: List[str] = None,
        expires_in_hours: int = 24
    ) -> str:
        """Create a new authentication token."""
        if permissions is None:
            permissions = ["read", "write", "transcribe"]
            
        # Generate unique token
        token = str(uuid.uuid4())
        
        # Create token data
        expires_at = datetime.now(timezone.utc) + timedelta(hours=expires_in_hours)
        token_data = {
            "user_id": user_id,
            "permissions": permissions,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "expires_at": expires_at.isoformat(),
            "last_used": datetime.now(timezone.utc).isoformat()
        }
        
        # Store in Redis with expiration
        key = f"auth:token:{token}"
        await self.client.setex(
            key, 
            int(expires_in_hours * 3600),  # TTL in seconds
            json.dumps(token_data)
        )
        
        print(f"✅ Created token for user '{user_id}': {token}")
        print(f"   Permissions: {permissions}")
        print(f"   Expires: {expires_at.strftime('%Y-%m-%d %H:%M:%S UTC')}")
        
        return token
    
    async def validate_token(self, token: str) -> tuple[bool, Optional[Dict[str, Any]]]:
        """Validate a token and return user data."""
        try:
            key = f"auth:token:{token}"
            token_data = await self.client.get(key)
            
            if not token_data:
                return False, None
            
            user_data = json.loads(token_data)
            
            # Check expiration
            expires_at = datetime.fromisoformat(user_data["expires_at"])
            if expires_at < datetime.now(timezone.utc):
                await self.client.delete(key)
                return False, None
                
            return True, user_data
            
        except Exception as e:
            print(f"❌ Token validation error: {e}")
            return False, None
    
    async def list_tokens(self) -> List[Dict[str, Any]]:
        """List all active tokens."""
        try:
            keys = await self.client.keys("auth:token:*")
            tokens = []
            
            for key in keys:
                token_data = await self.client.get(key)
                if token_data:
                    data = json.loads(token_data)
                    tokens.append({
                        "token": key.split(":")[-1],
                        "user_id": data.get("user_id"),
                        "permissions": data.get("permissions"),
                        "created_at": data.get("created_at"),
                        "expires_at": data.get("expires_at"),
                        "last_used": data.get("last_used")
                    })
            
            return tokens
        except Exception as e:
            print(f"❌ Error listing tokens: {e}")
            return []
    
    async def revoke_token(self, token: str) -> bool:
        """Revoke a token."""
        try:
            key = f"auth:token:{token}"
            result = await self.client.delete(key)
            if result:
                print(f"✅ Revoked token: {token}")
                return True
            else:
                print(f"⚠️  Token not found: {token}")
                return False
        except Exception as e:
            print(f"❌ Error revoking token: {e}")
            return False
    
    async def cleanup_expired_tokens(self) -> int:
        """Remove expired tokens and return count removed."""
        try:
            keys = await self.client.keys("auth:token:*")
            removed_count = 0
            
            for key in keys:
                token_data = await self.client.get(key)
                if token_data:
                    data = json.loads(token_data)
                    expires_at = datetime.fromisoformat(data["expires_at"])
                    
                    if expires_at < datetime.now(timezone.utc):
                        await self.client.delete(key)
                        removed_count += 1
            
            print(f"✅ Cleaned up {removed_count} expired tokens")
            return removed_count
        except Exception as e:
            print(f"❌ Error cleaning up tokens: {e}")
            return 0


async def main():
    """Main CLI interface for token management."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Redis Token Manager for Whisper ASR")
    parser.add_argument("--redis-url", required=True, help="Redis URL (e.g., redis://user:pass@host:port)")
    parser.add_argument("--redis-password", help="Redis password (if not in URL)")
    
    subparsers = parser.add_subparsers(dest="command", help="Available commands")
    
    # Create token command
    create_parser = subparsers.add_parser("create", help="Create a new token")
    create_parser.add_argument("--user-id", default="test-user", help="User ID for the token")
    create_parser.add_argument("--permissions", nargs="+", default=["read", "write", "transcribe"], 
                             help="Permissions for the token")
    create_parser.add_argument("--expires-hours", type=int, default=24, help="Token expiration in hours")
    
    # List tokens command
    subparsers.add_parser("list", help="List all active tokens")
    
    # Validate token command
    validate_parser = subparsers.add_parser("validate", help="Validate a token")
    validate_parser.add_argument("token", help="Token to validate")
    
    # Revoke token command
    revoke_parser = subparsers.add_parser("revoke", help="Revoke a token")
    revoke_parser.add_argument("token", help="Token to revoke")
    
    # Cleanup command
    subparsers.add_parser("cleanup", help="Remove expired tokens")
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return
    
    # Initialize token manager
    manager = RedisTokenManager(args.redis_url, args.redis_password or "")
    
    if not await manager.connect():
        return
    
    try:
        if args.command == "create":
            token = await manager.create_token(
                user_id=args.user_id,
                permissions=args.permissions,
                expires_in_hours=args.expires_hours
            )
            print(f"\n🔑 Bearer Token: {token}")
            print(f"📋 Use in API calls: -H 'Authorization: Bearer {token}'")
            
        elif args.command == "list":
            tokens = await manager.list_tokens()
            if tokens:
                print(f"\n📋 Active Tokens ({len(tokens)}):")
                print("-" * 80)
                for token_info in tokens:
                    print(f"Token: {token_info['token'][:20]}...")
                    print(f"User: {token_info['user_id']}")
                    print(f"Permissions: {token_info['permissions']}")
                    print(f"Expires: {token_info['expires_at']}")
                    print("-" * 80)
            else:
                print("No active tokens found.")
                
        elif args.command == "validate":
            is_valid, user_data = await manager.validate_token(args.token)
            if is_valid:
                print(f"✅ Token is valid")
                print(f"User: {user_data['user_id']}")
                print(f"Permissions: {user_data['permissions']}")
            else:
                print("❌ Token is invalid or expired")
                
        elif args.command == "revoke":
            await manager.revoke_token(args.token)
            
        elif args.command == "cleanup":
            await manager.cleanup_expired_tokens()
            
    finally:
        await manager.close()


if __name__ == "__main__":
    asyncio.run(main())