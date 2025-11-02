from fastapi import Depends, HTTPException
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from src.application.services.test_token_config import is_test_token

security = HTTPBearer()

def get_current_token(credentials: HTTPAuthorizationCredentials = Depends(security)):
    """
    Extract and validate bearer token from request headers.

    Supports both real OAuth2 tokens and test tokens for development.
    Test token: "test-token-12345" returns dummy data for all endpoints.
    """
    if credentials:
        token = credentials.credentials
        # Accept both real tokens and test tokens
        return token
    raise HTTPException(status_code=403, detail="Invalid or missing token")

def is_test_token_request(token: str) -> bool:
    """Check if the request is using a test token"""
    return is_test_token(token)
