from typing import List
from fastapi import APIRouter, HTTPException
from app.models.schemas import (
    ProfileCreateRequest,
    ProfileModel,
    ProfileUpdateRequest,
)
from app.repositories.profile_repository import ProfileRepository

router = APIRouter(prefix="/api/profiles", tags=["Profiles"])


@router.get("", response_model=List[ProfileModel])
async def list_profiles():
    """Lists all available download profiles (built-in and custom)."""
    raw_profiles = ProfileRepository.list_profiles()
    return [ProfileModel(**p) for p in raw_profiles]


@router.get("/default", response_model=ProfileModel)
async def get_default_profile():
    """Returns the current default profile."""
    p = ProfileRepository.get_default_profile()
    return ProfileModel(**p)


@router.get("/{profile_id}", response_model=ProfileModel)
async def get_profile(profile_id: str):
    """Retrieves a specific profile."""
    p = ProfileRepository.get_profile(profile_id)
    if not p:
        raise HTTPException(status_code=404, detail="Profile not found")
    return ProfileModel(**p)


@router.post("", response_model=ProfileModel)
async def create_profile(req: ProfileCreateRequest):
    """Creates a new custom download profile."""
    try:
        pid = ProfileRepository.create_profile(
            name=req.name,
            config=req.config.model_dump(),
            description=req.description,
            badge=req.badge,
            profile_id=req.id,
        )
        created = ProfileRepository.get_profile(pid)
        return ProfileModel(**created)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.put("/{profile_id}", response_model=ProfileModel)
async def update_profile(profile_id: str, req: ProfileUpdateRequest):
    """Updates an existing profile. Built-in profiles cannot have core config edited."""
    updates = {}
    if req.name is not None:
        updates["name"] = req.name
    if req.description is not None:
        updates["description"] = req.description
    if req.badge is not None:
        updates["badge"] = req.badge
    if req.config is not None:
        updates["config"] = req.config.model_dump()
    if req.is_default is not None:
        updates["is_default"] = req.is_default

    try:
        success = ProfileRepository.update_profile(profile_id, updates)
        if not success:
            raise HTTPException(status_code=404, detail="Profile not found")
        updated = ProfileRepository.get_profile(profile_id)
        return ProfileModel(**updated)
    except ValueError as ve:
        raise HTTPException(status_code=400, detail=str(ve))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/{profile_id}")
async def delete_profile(profile_id: str):
    """Deletes a custom profile. Built-ins cannot be deleted."""
    try:
        success = ProfileRepository.delete_profile(profile_id)
        if not success:
            raise HTTPException(status_code=404, detail="Profile not found")
        return {"status": "success", "message": "Profile deleted successfully."}
    except ValueError as ve:
        raise HTTPException(status_code=400, detail=str(ve))


@router.post("/{profile_id}/set-default")
async def set_default_profile(profile_id: str):
    """Sets a profile as the system default."""
    success = ProfileRepository.set_default_profile(profile_id)
    if not success:
        raise HTTPException(status_code=404, detail="Profile not found")
    return {"status": "success", "default_profile_id": profile_id}
