from typing import List
from fastapi import APIRouter, HTTPException
from app.models.schemas import (
    ApiKeyCreateRequest,
    ApiKeyCreateResponse,
    ApiKeyModel,
)
from app.repositories.api_key_repository import ApiKeyRepository

router = APIRouter(prefix="/api/keys", tags=["API Keys"])


@router.get("", response_model=List[ApiKeyModel])
async def list_keys():
    """Lists registered API keys with creation and last usage timestamps."""
    keys = ApiKeyRepository.list_keys()
    return [ApiKeyModel(**k) for k in keys]


@router.post("", response_model=ApiKeyCreateResponse)
async def create_key(req: ApiKeyCreateRequest):
    """
    Generates a new API key for automation integrations.
    Returns the plaintext API key exactly once.
    """
    if not req.name.strip():
        raise HTTPException(status_code=400, detail="Key name is required.")

    raw_key, record = ApiKeyRepository.create_key(req.name.strip())
    return ApiKeyCreateResponse(
        id=record["id"],
        name=record["name"],
        api_key=raw_key,
        key_prefix=record["key_prefix"],
    )


@router.post("/{key_id}/revoke")
async def revoke_key(key_id: str):
    """Revokes an API key, preventing any further authentication with it."""
    success = ApiKeyRepository.revoke_key(key_id)
    if not success:
        raise HTTPException(status_code=404, detail="API key not found")
    return {"status": "success", "message": "API key revoked successfully."}


@router.delete("/{key_id}")
async def delete_key(key_id: str):
    """Permanently deletes an API key."""
    success = ApiKeyRepository.delete_key(key_id)
    if not success:
        raise HTTPException(status_code=404, detail="API key not found")
    return {"status": "success", "message": "API key deleted permanently."}
