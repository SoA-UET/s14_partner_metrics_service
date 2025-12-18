"""
JWT Authentication utilities for verifying JWTs from Identity Service.
Implements JWKS-based verification according to VERIFY.md specification.
"""

import os
import time
import threading
import requests
import jwt
from typing import Optional, Dict, Any
from functools import wraps
from flask import request, jsonify


class JWKSManager:
    """
    Manages JWKS (JSON Web Key Set) fetching and caching.
    """
    
    def __init__(self):
        self.identity_service_url = os.getenv("IDENTITY_SERVICE_URL", "http://localhost:5001")
        self.jwks_ttl_minutes = int(os.getenv("JWKS_TTL_IN_MINUTES", "10"))
        self.jwks_cache: Dict[str, Any] = {}  # kid -> public_key mapping
        self.last_fetch_time = 0
        self.lock = threading.Lock()
        
        # Fetch JWKS at initialization
        self.refresh_jwks()
        
        # Start background refresh thread
        self._start_refresh_thread()
    
    def _start_refresh_thread(self):
        """Start background thread to refresh JWKS periodically."""
        def refresh_loop():
            while True:
                time.sleep(self.jwks_ttl_minutes * 60)
                self.refresh_jwks()
        
        thread = threading.Thread(target=refresh_loop, daemon=True)
        thread.start()
    
    def refresh_jwks(self):
        """Fetch JWKS from Identity Service."""
        try:
            jwks_url = f"{self.identity_service_url}/.well-known/jwks.json"
            print(f"[JWKSManager] Fetching JWKS from {jwks_url}")
            
            response = requests.get(jwks_url, timeout=5)
            response.raise_for_status()
            
            jwks_data = response.json()
            
            with self.lock:
                # Clear old cache
                self.jwks_cache = {}
                
                # Handle both single key and array of keys
                if isinstance(jwks_data, dict):
                    jwks_list = [jwks_data]
                elif isinstance(jwks_data, list):
                    jwks_list = jwks_data
                else:
                    print(f"[JWKSManager] Invalid JWKS format")
                    return
                
                # Store keys by kid
                for key_data in jwks_list:
                    kid = key_data.get("kid")
                    public_key = key_data.get("public_key")
                    if kid and public_key:
                        self.jwks_cache[kid] = public_key
                
                self.last_fetch_time = time.time()
                print(f"[JWKSManager] JWKS refreshed, {len(self.jwks_cache)} keys loaded")
        
        except Exception as e:
            print(f"[JWKSManager] Error fetching JWKS: {e}")
            # Continue using cached keys (graceful degradation)
    
    def get_public_key(self, kid: str) -> Optional[str]:
        """
        Get public key for the given kid.
        Does NOT refresh JWKS on cache miss (as per spec).
        """
        with self.lock:
            return self.jwks_cache.get(kid)


# Global JWKS manager instance
_jwks_manager: Optional[JWKSManager] = None


def get_jwks_manager() -> JWKSManager:
    """Get or create the global JWKS manager instance."""
    global _jwks_manager
    if _jwks_manager is None:
        _jwks_manager = JWKSManager()
    return _jwks_manager


def verify_jwt(token: str) -> Optional[Dict[str, Any]]:
    """
    Verify a JWT token according to VERIFY.md specification.
    
    Args:
        token: The JWT token string
        
    Returns:
        The decoded JWT payload if valid, None otherwise
    """
    try:
        # Step 1: Parse JWT header
        unverified_header = jwt.get_unverified_header(token)
        
        alg = unverified_header.get("alg")
        kid = unverified_header.get("kid")
        
        # Validate algorithm and kid
        if alg != "RS256":
            print(f"[JWT] Invalid algorithm: {alg}")
            return None
        
        if not kid:
            print(f"[JWT] Missing kid in header")
            return None
        
        # Step 2: Resolve public key
        jwks_manager = get_jwks_manager()
        public_key = jwks_manager.get_public_key(kid)
        
        if not public_key:
            print(f"[JWT] No public key found for kid: {kid}")
            return None
        
        # Step 3: Verify signature
        try:
            payload = jwt.decode(
                token,
                public_key,
                algorithms=["RS256"],
                options={
                    "verify_signature": True,
                    "verify_exp": True,
                    "verify_iat": True,
                    "require": ["exp", "iat", "sub"]
                }
            )
        except jwt.ExpiredSignatureError:
            print(f"[JWT] Token expired")
            return None
        except jwt.InvalidTokenError as e:
            print(f"[JWT] Invalid token: {e}")
            return None
        
        # Step 4: Validate claims
        if not payload.get("sub"):
            print(f"[JWT] Missing sub claim")
            return None
        
        # Ensure permissions is always present (default to empty array)
        if "permissions" not in payload:
            payload["permissions"] = []
        
        return payload
    
    except Exception as e:
        print(f"[JWT] Error verifying token: {e}")
        return None


def require_auth(required_permissions: list = None):
    """
    Decorator for Flask routes that require JWT authentication.
    
    Args:
        required_permissions: Optional list of required permissions
        
    Usage:
        @app.route('/api/protected')
        @require_auth(['employee.read'])
        def protected_route():
            # Access user info via request.user
            pass
    """
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            # Extract token from Authorization header
            auth_header = request.headers.get("Authorization")
            
            if not auth_header:
                return jsonify({
                    "status": "error",
                    "error_code": "UNAUTHORIZED",
                    "message": "Authorization header missing"
                }), 401
            
            # Parse Bearer token
            parts = auth_header.split()
            if len(parts) != 2 or parts[0].lower() != "bearer":
                return jsonify({
                    "status": "error",
                    "error_code": "UNAUTHORIZED",
                    "message": "Invalid Authorization header format"
                }), 401
            
            token = parts[1]
            
            # Verify token
            payload = verify_jwt(token)
            
            if not payload:
                return jsonify({
                    "status": "error",
                    "error_code": "UNAUTHORIZED",
                    "message": "Authentication token is invalid or expired"
                }), 401
            
            # Check permissions if required
            if required_permissions:
                user_permissions = payload.get("permissions", [])
                has_permission = any(perm in user_permissions for perm in required_permissions)
                
                if not has_permission:
                    return jsonify({
                        "status": "error",
                        "error_code": "FORBIDDEN",
                        "message": "User does not have permission to access this resource"
                    }), 403
            
            # Attach user info to request
            request.user = payload
            
            return f(*args, **kwargs)
        
        return decorated_function
    
    return decorator
