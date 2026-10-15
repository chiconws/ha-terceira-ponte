"""Camera platform for the ha_terceira_ponte integration."""
from __future__ import annotations

from typing import TYPE_CHECKING

from homeassistant.components.camera import Camera
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceEntryType, DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .client import TerceiraPonteClient
from .const import CAMERAS, DOMAIN

if TYPE_CHECKING:
    from . import TerceiraPonteConfigEntry


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
        identifiers={(DOMAIN, "ha_terceira_ponte_cameras")},
        name="CETURB Terceira Ponte",
        manufacturer="CETURB-ES",
        model="Terceira Ponte Cameras",
        entry_type=DeviceEntryType.SERVICE,
    )

    def __init__(self, client: TerceiraPonteClient, camera_id: str, name: str) -> None:
        """Initialize the camera entity."""
        super().__init__()
        self._client = client
        self._camera_id = camera_id
        self._attr_unique_id = camera_id
        self._attr_name = name
        self._attr_content_type = "image/jpeg"

    @property
    def available(self) -> bool:
        """Return whether the camera is available."""
        return self._client.get_camera_state(self._camera_id).available

    @property
    def extra_state_attributes(self) -> dict[str, str | int | None]:
        """Return extra state attributes."""
        state = self._client.get_camera_state(self._camera_id)
        return {
            "camera_id": self._camera_id,
            "last_success_at": (
                state.last_success_at.isoformat() if state.last_success_at else None
            ),
            "bytes": state.bytes_size,
            "content_type": state.content_type,
        }

    async def async_camera_image(
        self,
        width: int | None = None,
        height: int | None = None,
    ) -> bytes | None:
        """Return a camera image."""
        try:
            return await self._client.async_get_camera_image(self._camera_id)
        finally:
            if self.hass is not None:
                self.async_write_ha_state()
