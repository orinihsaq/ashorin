from typing import List, Optional
from fastapi import APIRouter, HTTPException, Query
from app.models.schemas import (
    RuleCreateRequest,
    RuleMatchResult,
    RuleModel,
    RuleUpdateRequest,
)
from app.repositories.profile_repository import ProfileRepository
from app.repositories.rule_repository import RuleRepository

router = APIRouter(prefix="/api/rules", tags=["Automation Rules"])


@router.get("", response_model=List[RuleModel])
async def list_rules():
    """Lists all automation rules ordered by priority and creation time."""
    rules = RuleRepository.list_rules()
    return [RuleModel(**r) for r in rules]


@router.get("/evaluate", response_model=RuleMatchResult)
async def evaluate_rules(
    url: str = Query(..., description="Target URL"),
    extractor: Optional[str] = Query(None),
    title: Optional[str] = Query(None),
    is_playlist: bool = Query(False),
):
    """
    Evaluates rules against URL metadata and returns the matching profile with explanation.
    Used for 'Why this profile?' badges in the UI.
    """
    res = RuleRepository.evaluate_rules(
        url=url,
        extractor=extractor,
        title=title,
        is_playlist=is_playlist,
    )

    prof_name = None
    if res.get("profile_id"):
        p = ProfileRepository.get_profile(res["profile_id"])
        if p:
            prof_name = p.get("name")

    return RuleMatchResult(
        matched=res["matched"],
        rule_name=res.get("rule_name"),
        profile_id=res.get("profile_id"),
        profile_name=prof_name,
        reason=res.get("reason"),
    )


@router.post("", response_model=RuleModel)
async def create_rule(req: RuleCreateRequest):
    """Creates a new automation rule."""
    # Verify target profile exists
    prof = ProfileRepository.get_profile(req.profile_id)
    if not prof:
        raise HTTPException(status_code=400, detail=f"Target profile '{req.profile_id}' does not exist.")

    rid = RuleRepository.create_rule(
        name=req.name,
        condition_type=req.condition_type,
        condition_value=req.condition_value,
        profile_id=req.profile_id,
        priority=req.priority,
        is_enabled=req.is_enabled,
    )
    created = RuleRepository.get_rule(rid)
    return RuleModel(**created)


@router.put("/{rule_id}", response_model=RuleModel)
async def update_rule(rule_id: str, req: RuleUpdateRequest):
    """Updates an automation rule."""
    if req.profile_id:
        prof = ProfileRepository.get_profile(req.profile_id)
        if not prof:
            raise HTTPException(status_code=400, detail=f"Target profile '{req.profile_id}' does not exist.")

    updates = {}
    if req.name is not None:
        updates["name"] = req.name
    if req.condition_type is not None:
        updates["condition_type"] = req.condition_type
    if req.condition_value is not None:
        updates["condition_value"] = req.condition_value
    if req.profile_id is not None:
        updates["profile_id"] = req.profile_id
    if req.priority is not None:
        updates["priority"] = req.priority
    if req.is_enabled is not None:
        updates["is_enabled"] = req.is_enabled

    success = RuleRepository.update_rule(rule_id, updates)
    if not success:
        raise HTTPException(status_code=404, detail="Rule not found")
    updated = RuleRepository.get_rule(rule_id)
    return RuleModel(**updated)


@router.delete("/{rule_id}")
async def delete_rule(rule_id: str):
    """Deletes an automation rule."""
    success = RuleRepository.delete_rule(rule_id)
    if not success:
        raise HTTPException(status_code=404, detail="Rule not found")
    return {"status": "success", "message": "Rule deleted successfully."}
