from fastapi import Depends, Header, Security, HTTPException
from fastapi.security import APIKeyQuery, APIKeyHeader
from config import get_config

# 声明 secret
api_key_query = APIKeyQuery(name="secret", auto_error=False)


async def verify_secret(
    secret_from_query: str = Security(api_key_query),
    config=Depends(get_config),
    secret_from_header: str = Header(None, alias="X-Secret"),
):
    secret = secret_from_query or secret_from_header
    if not secret or secret != config.main.secret:
        raise HTTPException(
            status_code=403,
            detail="Secret is invalid or missing, make sure include it in URL:\"?=secret\" or Header:\"X-Secret: <secret>\"",
        )
    return True
