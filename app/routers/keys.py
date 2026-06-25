from fastapi import APIRouter, HTTPException

from app.schemas.key import CreateKeyRequest, CreateKeyResponse, KeyInfoResponse
from app.services import key_service

router = APIRouter(prefix="/keys", tags=["API Keys"])


@router.post("", response_model=CreateKeyResponse, status_code=201)
def create_new_key(body: CreateKeyRequest) -> CreateKeyResponse:
    return key_service.create_key(name=body.name)


@router.get("", response_model=list[KeyInfoResponse])
def get_all_keys() -> list[KeyInfoResponse]:
    return key_service.list_keys()


@router.delete("/{key_id}", status_code=204)
def delete_key(key_id: int) -> None:
    revoked = key_service.revoke_key(key_id=key_id)
    if not revoked:
        raise HTTPException(status_code=404, detail="API key not found")
