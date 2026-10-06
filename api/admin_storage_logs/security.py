from fastapi import Security, HTTPException, status
from fastapi.security.api_key import APIKeyHeader

# In a real app, load this from environment variables
API_KEY = "super_secret_admin_key"
API_KEY_NAME = "X-Admin-API-Key"

api_key_header = APIKeyHeader(name=API_KEY_NAME, auto_error=False)

async def get_api_key(api_key_header: str = Security(api_key_header)):
    if api_key_header == API_KEY:
        return api_key_header
    else:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Could not validate credentials"
        )