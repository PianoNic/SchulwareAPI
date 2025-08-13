from fastapi import Depends, HTTPException
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

security = HTTPBearer()

def get_current_token(credentials: HTTPAuthorizationCredentials = Depends(security)):
    if credentials:
        return credentials.credentials
    raise HTTPException(status_code=403, detail="Invalid or missing token")
