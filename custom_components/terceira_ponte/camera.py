"""Camera platform for the terceira_ponte integration."""
from __future__ import annotations

from typing import TYPE_CHECKING

from homeassistant.components.camera import Camera
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceEntryType, DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .client import TerceiraPonteClient
from .const import BASE_URL, CAMERAS, DOMAIN

if TYPE_CHECKING:
    from . import TerceiraPonteConfigEntry


PARALLEL_UPDATES = 0


async def async_setup_entry(
    hass: HomeAssistant,
    entry: TerceiraPonteConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up camera entities from a config entry."""
    async_add_entities(
        TerceiraPonteCamera(entry.runtime_data, camera_id, name)
        for camera_id, name in CAMERAS.items()
    )


class TerceiraPonteCamera(Camera):
    """Representation of a Terceira Ponte snapshot camera."""

    _attr_has_entity_name = True
    _attr_should_poll = False
    _attr_device_info = DeviceInfo(
        identifiers={(DOMAIN, "terceira_ponte_cameras")},
        name="CETURB Terceira Ponte",
        manufacturer="CETURB-ES",
        model="Terceira Ponte Cameras",
        entry_type=DeviceEntryType.SERVICE,
        configuration_url=BASE_URL,
    )

    def __init__(self, client: TerceiraPonteClient, camera_id: str, name: str) -> None:
        """Initialize the camera entity."""
        super().__init__()
        self._client = client
        self._camera_id = camera_id
        self._attr_unique_id = camera_id
        self._attr_name = name
        self._attr_content_type = "image/jpeg"
        self._attr_extra_state_attributes = {"camera_id": camera_id}

    @property
    def available(self) -> bool:
        """Return whether the camera is available."""
        return self._client.is_available(self._camera_id)

    async def async_camera_image(
        self,
        width: int | None = None,
        height: int | None = None,
    ) -> bytes | None:
        """Return a camera image, writing state only when availability flips."""
        was_available = self.available
        try:
            return await self._client.async_get_camera_image(self._camera_id)
        finally:
            if self.hass is not None and self.available != was_available:
                self.async_write_ha_state()
