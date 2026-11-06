"""Tests for terceira_ponte camera entities."""

from collections.abc import Iterable

import pytest
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.terceira_ponte import camera as camera_platform
from custom_components.terceira_ponte.const import CAMERAS, DOMAIN
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import Entity


class FakeClient:
    """Fake client for camera tests."""

    async def async_get_camera_image(self, camera_id: str) -> bytes:
        """Return the camera id as image bytes."""
        return camera_id.encode("utf-8")

    def is_available(self, camera_id: str) -> bool:
        """Report every camera as available."""
        return True


@pytest.mark.asyncio
async def test_camera_setup_creates_four_entities(hass: HomeAssistant) -> None:
    """Camera setup should create the expected camera entities."""
    entry = MockConfigEntry(domain=DOMAIN, data={}, title="Terceira Ponte")
    entry.runtime_data = FakeClient()

    added_entities: list = []

    def add_entities(
        new_entities: Iterable[Entity], update_before_add: bool = False
    ) -> None:
        added_entities.extend(new_entities)

    await camera_platform.async_setup_entry(hass, entry, add_entities)

    assert len(added_entities) == 4
    assert [entity.unique_id for entity in added_entities] == list(CAMERAS)

    first_image = await added_entities[0].async_camera_image()
    assert first_image == next(iter(CAMERAS)).encode("utf-8")


async def test_camera_writes_recovery_after_overlapping_fetch(
    hass: HomeAssistant,
) -> None:
    """A success after another fetch marked the camera unavailable is written."""
    client = FakeClient()
    entity = camera_platform.TerceiraPonteCamera(client, next(iter(CAMERAS)), "Cam")  # type: ignore[arg-type] # fake client
    entity.hass = hass
    writes: list[bool] = []
    entity.async_write_ha_state = lambda: writes.append(entity.available)  # type: ignore[method-assign] # record writes
    # The overlapping fetch already published "unavailable"; this one succeeds.
    entity._published_available = False  # noqa: SLF001
    await entity.async_camera_image()
    assert writes == [True]
    await entity.async_camera_image()
    assert writes == [True]
