import time
import pytest
from app.db.database import get_db, init_db
from app.repositories.api_key_repository import ApiKeyRepository
from app.repositories.job_repository import JobRepository
from app.repositories.media_repository import MediaRepository
from app.repositories.profile_repository import ProfileRepository
from app.repositories.rule_repository import RuleRepository
from app.repositories.webhook_repository import WebhookRepository


@pytest.fixture(autouse=True)
def setup_test_db():
    init_db()


def test_builtin_profiles_seeded():
    profiles = ProfileRepository.list_profiles()
    assert len(profiles) >= 5
    ids = [p["id"] for p in profiles]
    assert "recommended" in ids
    assert "best_quality" in ids
    assert "audio_only" in ids

    default_prof = ProfileRepository.get_default_profile()
    assert default_prof["id"] == "recommended"


def test_custom_profile_crud():
    pid = ProfileRepository.create_profile(
        name="Custom 720p",
        description="720p MP4 profile",
        badge="720p",
        config={"quality": "720p", "output_container": "mp4"},
    )
    assert pid is not None

    prof = ProfileRepository.get_profile(pid)
    assert prof["name"] == "Custom 720p"
    assert prof["config"]["quality"] == "720p"
    assert prof["is_builtin"] is False

    # Update
    ProfileRepository.update_profile(pid, {"name": "Custom 720p Updated"})
    updated = ProfileRepository.get_profile(pid)
    assert updated["name"] == "Custom 720p Updated"

    # Set default
    ProfileRepository.set_default_profile(pid)
    d = ProfileRepository.get_default_profile()
    assert d["id"] == pid

    # Reset default back to recommended
    ProfileRepository.set_default_profile("recommended")

    # Delete
    deleted = ProfileRepository.delete_profile(pid)
    assert deleted is True
    assert ProfileRepository.get_profile(pid) is None


def test_builtin_profile_protection():
    with pytest.raises(ValueError):
        ProfileRepository.delete_profile("recommended")

    with pytest.raises(ValueError):
        ProfileRepository.update_profile("recommended", {"config": {"quality": "360p"}})


def test_rule_evaluation():
    import uuid
    dom = f"music-{uuid.uuid4().hex[:6]}.com"
    rname = f"Audio Rule {uuid.uuid4().hex[:6]}"
    rid = RuleRepository.create_rule(
        name=rname,
        condition_type="domain",
        condition_value=dom,
        profile_id="audio_only",
        priority=100,
    )

    eval_result = RuleRepository.evaluate_rules(url=f"https://{dom}/artist/track")
    assert eval_result["matched"] is True
    assert eval_result["profile_id"] == "audio_only"
    assert rname in eval_result["reason"]

    # Non-matching URL
    eval_other = RuleRepository.evaluate_rules(url="https://vimeo.com/123456")
    assert eval_other["matched"] is False
    assert eval_other["profile_id"] is None

    # Clean up
    RuleRepository.delete_rule(rid)


def test_api_key_lifecycle():
    raw_key, record = ApiKeyRepository.create_key("Automation Test Key")
    assert raw_key.startswith("ash_live_")
    assert record["name"] == "Automation Test Key"
    assert record["key_prefix"].startswith("ash_live_")

    # Verify key
    verified = ApiKeyRepository.verify_key(raw_key)
    assert verified is not None
    assert verified["id"] == record["id"]

    # Invalid key
    assert ApiKeyRepository.verify_key("ash_live_invalidkey1234567890") is None

    # Revoke key
    ApiKeyRepository.revoke_key(record["id"])
    assert ApiKeyRepository.verify_key(raw_key) is None

    # Delete key
    ApiKeyRepository.delete_key(record["id"])


def test_media_repository_crud_and_protection():
    media_id = MediaRepository.add_media({
        "title": "Sample Coding Video",
        "filename": "sample_coding.mp4",
        "relative_path": "sample_coding.mp4",
        "source_url": "https://example.com/coding",
        "container": "mp4",
        "filesize": 1024 * 1024 * 15,  # 15MB
        "is_favorite": False,
        "is_protected": True,
    })

    item = MediaRepository.get_media(media_id)
    assert item is not None
    assert item["title"] == "Sample Coding Video"
    assert item["is_protected"] is True

    # Attempt delete while protected must raise ValueError
    with pytest.raises(ValueError):
        MediaRepository.delete_media(media_id)

    # Toggle protected off
    new_prot = MediaRepository.toggle_protected(media_id)
    assert new_prot is False

    # Toggle favorite on
    new_fav = MediaRepository.toggle_favorite(media_id)
    assert new_fav is True

    # Delete allowed now
    deleted = MediaRepository.delete_media(media_id, delete_file=False)
    assert deleted is True
    assert MediaRepository.get_media(media_id) is None


def test_webhook_repository_and_delivery_logs():
    wid = WebhookRepository.create_webhook(
        url="https://webhook.site/test",
        events=["job.completed", "batch.completed"],
        signing_secret="secret123",
    )
    assert wid is not None

    wh = WebhookRepository.get_webhook(wid)
    assert wh["url"] == "https://webhook.site/test"
    assert "job.completed" in wh["events"]

    # Log delivery
    del_id = WebhookRepository.log_delivery(
        webhook_id=wid,
        event="job.completed",
        payload_summary="Job 123 completed",
        status_code=200,
        success=True,
    )
    assert del_id is not None

    logs = WebhookRepository.list_deliveries(webhook_id=wid)
    assert len(logs) >= 1
    assert logs[0]["event"] == "job.completed"
    assert logs[0]["success"] is True

    WebhookRepository.delete_webhook(wid)
    assert WebhookRepository.get_webhook(wid) is None
