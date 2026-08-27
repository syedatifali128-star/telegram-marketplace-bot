from __future__ import annotations

import pytest

from app.models import Category, Group
from app.repositories import campaign_repository, group_repository
from app.services import campaign_service


def _make_category(db, name="SMM") -> Category:
    cat = Category(name=name)
    db.add(cat)
    db.commit()
    return cat


def _make_group(db, chat_id: int, name: str, category_ids: list[int]) -> Group:
    return group_repository.create_group(db, telegram_chat_id=chat_id, name=name, username_or_link=None, category_ids=category_ids)


def test_campaign_creation_success(db):
    cat = _make_category(db)
    campaign = campaign_service.create_campaign(
        db, name="Test Campaign", category_id=cat.id, message_text="Hello {category}", interval_seconds=600
    )
    db.commit()
    assert campaign.id is not None
    assert campaign.status.value == "PAUSED"  # created paused by design


def test_campaign_interval_too_short_rejected(db):
    cat = _make_category(db)
    with pytest.raises(campaign_service.CampaignValidationError):
        campaign_service.create_campaign(db, "X", cat.id, "hi", interval_seconds=10)


def test_invalid_template_variable_rejected(db):
    cat = _make_category(db)
    with pytest.raises(campaign_service.CampaignValidationError):
        campaign_service.create_campaign(db, "X", cat.id, "Hello {unknown_var}", interval_seconds=600)


def test_valid_template_variables_accepted(db):
    cat = _make_category(db)
    campaign = campaign_service.create_campaign(
        db, "X", cat.id, "{campaign_name} in {category} on {date} {time}", interval_seconds=600
    )
    db.commit()
    rendered = campaign_service.render_message(campaign, category_name="SMM")
    assert "X in SMM on" in rendered


def test_campaign_group_isolation(db):
    """Campaign A assigned to Group 1 must never resolve Group 2 as a target."""
    cat_a = _make_category(db, "Instagram")
    cat_b = _make_category(db, "YouTube")
    group_a = _make_group(db, 111, "IG Marketplace", [cat_a.id])
    group_b = _make_group(db, 222, "YT Marketplace", [cat_b.id])
    db.commit()

    campaign_a = campaign_service.create_campaign(db, "Campaign A", cat_a.id, "hi", 600)
    db.commit()
    campaign_a, warnings = campaign_service.assign_groups(db, campaign_a, [group_a.id])
    db.commit()

    targets = campaign_repository.get_assigned_groups(db, campaign_a.id)
    target_ids = {g.id for g in targets}

    assert group_a.id in target_ids
    assert group_b.id not in target_ids  # never implicitly included


def test_resume_without_groups_rejected(db):
    cat = _make_category(db)
    campaign = campaign_service.create_campaign(db, "X", cat.id, "hi", 600)
    db.commit()
    with pytest.raises(campaign_service.CampaignValidationError):
        campaign_service.resume_campaign(db, campaign)


def test_resume_with_groups_succeeds(db):
    cat = _make_category(db)
    group = _make_group(db, 333, "G1", [cat.id])
    db.commit()
    campaign = campaign_service.create_campaign(db, "X", cat.id, "hi", 600)
    db.commit()
    campaign_service.assign_groups(db, campaign, [group.id])
    db.commit()
    campaign_service.resume_campaign(db, campaign)
    assert campaign.status.value == "ACTIVE"


def test_pause_campaign(db):
    cat = _make_category(db)
    group = _make_group(db, 444, "G1", [cat.id])
    db.commit()
    campaign = campaign_service.create_campaign(db, "X", cat.id, "hi", 600)
    campaign_service.assign_groups(db, campaign, [group.id])
    db.commit()
    campaign_service.resume_campaign(db, campaign)
    campaign_service.pause_campaign(db, campaign)
    assert campaign.status.value == "PAUSED"
