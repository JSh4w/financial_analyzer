"""JWT authentication utilities for validating Supabase tokens"""

from typing import Any, Dict, List, Optional, Union

import jwt
from app.config import Settings
from fastapi import HTTPException, Security
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jwt import PyJWKClient
from pydantic import BaseModel

settings = Settings()
security = HTTPBearer()
security_optional = HTTPBearer(
    auto_error=False
)  # For optional auth (doesn't raise error)

# Initialize JWKS client for secure RS256/ES256 verification
# Falls back to HS256 if JWKS URL is not configured (legacy support)
jwks_client = None
if hasattr(settings, "SUPABASE_JWKS_URL") and settings.SUPABASE_JWKS_URL:
    jwks_client = PyJWKClient(settings.SUPABASE_JWKS_URL, cache_keys=True)


class TokenPayload(BaseModel):
    """JWT token payload from Supabase (essential fields only)"""

    sub: str  # User ID - for DB queries
    email: str  # Email - for display/logging
    role: str  # Role - for authorization

    # Fields for validation
    iss: str  # Issuer - verify it's Supabase
    aud: Union[str, List[str]]  # Audience - verify it's "authenticated"
    exp: int  # Expiration - automatic validation
    iat: int  # Issued at - for logging

    # Nice-to-have fields
    session_id: Optional[str] = None  # Session tracking
    aal: Optional[str] = None  # Auth level (aal1, aal2)
    phone: Optional[str] = None  # Phone if available
    is_anonymous: Optional[bool] = None  # Anonymous user check

    # Advanced (only if you use custom metadata)
    app_metadata: Optional[Dict[str, Any]] = None
    user_metadata: Optional[Dict[str, Any]] = None


def decode_jwt_token(token: str) -> TokenPayload:
    """
    Decode and validate a Supabase JWT token using RS256 (recommended) or HS256 (legacy)

    Uses RS256 with JWKS endpoint if SUPABASE_JWKS_URL is configured (secure method).
    Falls back to HS256 with shared secret for legacy projects (not recommended).

    Args:
        token: The JWT token string from the Authorization header

    Returns:
        TokenPayload: Decoded token payload with user information

    Raises:
        HTTPException: If token is invalid, expired, or malformed
    """
    try:
        # Method 1: RS256 with JWKS (SECURE - Recommended by Supabase)
        if jwks_client:
            # Get the signing key from JWKS endpoint based on token's kid
            signing_key = jwks_client.get_signing_key_from_jwt(token)

            # Decode and verify using public key (RS256 or ES256)
            payload = jwt.decode(
                token,
                signing_key.key,
                algorithms=["RS256", "ES256"],  # Allow both RSA and Elliptic Curve
                audience="authenticated",
                options={"verify_aud": True, "verify_exp": True},
            )

        # Method 2: HS256 with shared secret (LEGACY - Not Recommended)
        else:
            # Fallback to legacy HS256 verification
            # WARNING: This is less secure and should be migrated to RS256
            payload = jwt.decode(
                token,
                settings.SUPABASE_JWT_SECRET,
                algorithms=["HS256"],
                audience="authenticated",
                options={"verify_aud": True, "verify_exp": True},
            )

        return TokenPayload(**payload)

    except jwt.ExpiredSignatureError as e:
        raise HTTPException(status_code=401, detail="Token has expired") from e
    except jwt.InvalidTokenError as e:
        raise HTTPException(
            status_code=401, detail="Invalid authentication token"
        ) from e
    except Exception as e:
        raise HTTPException(
            status_code=401, detail=f"Authentication failed: {str(e)}"
        ) from e


def get_current_user(
    credentials: HTTPAuthorizationCredentials = Security(security),
) -> TokenPayload:
    """
    FastAPI dependency to get the current authenticated user from JWT token

    Usage:
        @app.get("/protected")
        async def protected_route(user: TokenPayload = Depends(get_current_user)):
            return {"user_id": user.sub, "email": user.email}

    Args:
        credentials: HTTP Bearer credentials automatically extracted from header

    Returns:
        TokenPayload: Decoded token with user information

    Raises:
        HTTPException: If authentication fails
    """
    token = credentials.credentials
    return decode_jwt_token(token)


def get_current_user_id(
    credentials: HTTPAuthorizationCredentials = Security(security),
) -> str:
    """
    FastAPI dependency to get just the user ID (simpler than full token payload)

    Usage:
        @app.get("/my-data")
        async def my_data(user_id: str = Depends(get_current_user_id)):
            return {"user_id": user_id}

    Args:
        credentials: HTTP Bearer credentials automatically extracted from header

    Returns:
        str: User ID from the token
    """
    token_payload = decode_jwt_token(credentials.credentials)
    return token_payload.sub


# Optional: Dependency for optional authentication (doesn't raise error if no token)
def get_optional_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Security(security_optional),
) -> Optional[TokenPayload]:
    """
    FastAPI dependency for optional authentication
    Returns None if no token provided, otherwise validates and returns user

    Usage:
        @app.get("/public-or-private")
        async def route(user: Optional[TokenPayload] = Depends(get_optional_user)):
            if user:
                return {"message": f"Hello {user.email}"}
            return {"message": "Hello anonymous user"}
    """
    if credentials is None:
        return None
    return decode_jwt_token(credentials.credentials)
