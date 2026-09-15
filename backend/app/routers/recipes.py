from typing import Any, Dict, List, Optional
from fastapi import APIRouter, HTTPException, Query
from app.models.schemas import (
    RecipeCreateRequest,
    RecipeModel,
    RecipeUpdateRequest,
)
from app.repositories.profile_repository import ProfileRepository
from app.repositories.recipe_repository import RecipeRepository

router = APIRouter(prefix="/api/recipes", tags=["Download Recipes"])


@router.get("", response_model=List[RecipeModel])
async def list_recipes():
    """Lists all available download recipes (built-in and custom)."""
    recipes = RecipeRepository.list_recipes()
    return [RecipeModel(**r) for r in recipes]


@router.post("", response_model=RecipeModel)
async def create_recipe(req: RecipeCreateRequest):
    """Creates a new custom download recipe."""
    profile = ProfileRepository.get_profile(req.profile_id)
    if not profile:
        raise HTTPException(status_code=400, detail=f"Referenced profile '{req.profile_id}' does not exist.")

    created = RecipeRepository.create_recipe(req.model_dump())
    return RecipeModel(**created)


@router.get("/{recipe_id}", response_model=RecipeModel)
async def get_recipe(recipe_id: str):
    """Retrieves full recipe details."""
    recipe = RecipeRepository.get_recipe(recipe_id)
    if not recipe:
        raise HTTPException(status_code=404, detail="Recipe not found")
    return RecipeModel(**recipe)


@router.patch("/{recipe_id}", response_model=RecipeModel)
async def update_recipe(recipe_id: str, req: RecipeUpdateRequest):
    """Updates custom recipe settings."""
    existing = RecipeRepository.get_recipe(recipe_id)
    if not existing:
        raise HTTPException(status_code=404, detail="Recipe not found")
    if existing.get("is_builtin"):
        raise HTTPException(status_code=400, detail="Standard built-in recipes cannot be modified.")

    if req.profile_id:
        profile = ProfileRepository.get_profile(req.profile_id)
        if not profile:
            raise HTTPException(status_code=400, detail=f"Profile '{req.profile_id}' does not exist.")

    updated = RecipeRepository.update_recipe(recipe_id, req.model_dump(exclude_unset=True))
    return RecipeModel(**updated)


@router.delete("/{recipe_id}")
async def delete_recipe(recipe_id: str):
    """Permanently deletes a custom recipe. Built-in recipes cannot be deleted."""
    existing = RecipeRepository.get_recipe(recipe_id)
    if not existing:
        raise HTTPException(status_code=404, detail="Recipe not found")
    if existing.get("is_builtin"):
        raise HTTPException(status_code=400, detail="Cannot delete protected built-in recipes.")

    success = RecipeRepository.delete_recipe(recipe_id)
    return {"status": "success", "message": "Recipe deleted"}


@router.post("/{recipe_id}/clone", response_model=RecipeModel)
async def clone_recipe(recipe_id: str, name: str = Query(..., description="Name for the cloned recipe")):
    """Clones an existing recipe into a customizable duplicate."""
    cloned = RecipeRepository.clone_recipe(recipe_id, name)
    if not cloned:
        raise HTTPException(status_code=404, detail="Source recipe not found")
    return RecipeModel(**cloned)


@router.post("/{recipe_id}/default")
async def set_default_recipe(recipe_id: str):
    """Sets the designated recipe as the system default."""
    success = RecipeRepository.set_default_recipe(recipe_id)
    if not success:
        raise HTTPException(status_code=404, detail="Recipe not found")
    return {"status": "success", "default_recipe": recipe_id}
