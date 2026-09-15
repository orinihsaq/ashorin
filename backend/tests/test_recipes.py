import pytest
from httpx import ASGITransport, AsyncClient
from app.main import app
from app.repositories.recipe_repository import RecipeRepository


@pytest.mark.asyncio
async def test_recipes_lifecycle():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        # 1. List recipes (should contain 4 built-in)
        res = await ac.get("/api/recipes")
        assert res.status_code == 200
        recipes = res.json()
        assert len(recipes) >= 4
        builtin_ids = {r["id"] for r in recipes if r["is_builtin"]}
        assert "video_archive" in builtin_ids
        assert "music" in builtin_ids
        assert "mobile_video" in builtin_ids
        assert "podcast" in builtin_ids

        # 2. Cannot delete built-in recipe
        res = await ac.delete("/api/recipes/video_archive")
        assert res.status_code == 400
        assert "Cannot delete protected" in res.json()["detail"]

        # 3. Create custom recipe
        custom_payload = {
            "name": "4K Archival Workflow",
            "description": "High resolution preservation workflow",
            "profile_id": "best_quality",
            "storage_folder": "Archival/4K/{creator}/{title}",
            "duplicate_policy": "skip",
            "target_quality": "4k",
            "minimum_quality": "1080p",
            "upgrade_policy": "automatic",
            "retention_days": 0,
            "notify_events": ["job.completed", "job.failed"],
        }
        res = await ac.post("/api/recipes", json=custom_payload)
        assert res.status_code == 200
        created = res.json()
        assert created["name"] == "4K Archival Workflow"
        recipe_id = created["id"]
        assert created["is_builtin"] is False

        # 4. Clone recipe
        res = await ac.post(f"/api/recipes/{recipe_id}/clone?name=Cloned_4K_Workflow")
        assert res.status_code == 200
        cloned = res.json()
        assert cloned["name"] == "Cloned_4K_Workflow"
        assert cloned["id"] != recipe_id

        # 5. Set default recipe
        res = await ac.post(f"/api/recipes/{recipe_id}/default")
        assert res.status_code == 200
        assert res.json()["default_recipe"] == recipe_id

        # 6. Delete custom recipe
        res = await ac.delete(f"/api/recipes/{recipe_id}")
        assert res.status_code == 200
        res = await ac.delete(f"/api/recipes/{cloned['id']}")
        assert res.status_code == 200
