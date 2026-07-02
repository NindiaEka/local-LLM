from fastapi import Depends, HTTPException, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.services.key_service import validate_key

_bearer_scheme = HTTPBearer(auto_error=False)


def verify_api_key(
    request: Request,
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer_scheme),
) -> None:
    if credentials is None:
        raise HTTPException(status_code=401, detail="Authorization header missing")

    validated = validate_key(credentials.credentials)
    request.state.api_key_id = str(validated.id)
