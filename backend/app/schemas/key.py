from pydantic import BaseModel


class CreateKeyRequest(BaseModel):
    name: str


class CreateKeyResponse(BaseModel):
    id: int
    name: str
    key: str


class KeyInfoResponse(BaseModel):
    id: int
    name: str
    is_active: bool
    created_at: str
