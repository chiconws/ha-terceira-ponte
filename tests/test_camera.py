"""Tests for ha_terceira_ponte camera entities."""
from __future__ import annotations

from datetime import UTC, datetime

import pytest

from custom_components.ha_terceira_ponte import camera as camera_platform
from custom_components.ha_terceira_ponte.client import CameraState
from custom_components.ha_terceira_ponte.const import CAMERAS, DOMAIN
from pytest_homeassistant_custom_component.common import MockConfigEntry


class FakeClient:
    """Fake client for camera tests."""

    def __init__(self) -> None:
        self.images: dict[str, bytes] = {
            definition.camera_id: definition.camera_id.encode("utf-8")
            for definition in CAMERAS
        }
        self.states: dict[str, CameraState] = {
            definition.camera_id: CameraState(
                available=True,
                last_success_at=datetime(2026, 3, 12, tzinfo=UTC),
                bytes_size=len(definition.camera_id),
                content_type="image/jpeg",
            )
            for definition in CAMERAS
        }

    async def async_get_camera_image(self, camera_id: str) -> bytes:
        return self.images[camera_id]

    def get_camera_state(self, camera_id: str) -> CameraState:
        return self.states[camera_id]


@pytest.mark.asyncio
async def test_camera_setup_creates_four_entities(hass) -> None:
    """Camera setup should create the expected camera entities."""
    entry = MockConfigEntry(domain=DOMAIN, data={}, title="Terceira Ponte")
    fake_client = FakeClient()
    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = fake_client

    added_entities = []

    def add_entities(entities):
        added_entities.extend(list(entities))

    await camera_platform.async_setup_entry(hass, entry, add_entities)

    assert len(added_entities) == 4
    assert [entity.unique_id for entity in added_entities] == [
        definition.camera_id for definition in CAMERAS
    ]

    first_image = await added_entities[0].async_camera_image()
    assert first_image == CAMERAS[0].camera_id.encode("utf-8")
