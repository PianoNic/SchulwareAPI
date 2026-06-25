from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials

from src.api.auth.bearer import security


def get_current_token(credentials: HTTPAuthorizationCredentials = Depends(security)):
    """
    Extract the bearer token from the request headers.

    The token is the caller's upstream Schulnetz mobile token, replayed downstream
    (SchulwareAPI is a stateless proxy and issues no tokens of its own).
    """
    if credentials:
        return credentials.credentials
    raise HTTPException(status_code=403, detail="Invalid or missing token")
