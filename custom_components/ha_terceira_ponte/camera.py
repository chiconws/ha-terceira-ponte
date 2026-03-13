"""Camera platform for the ha_terceira_ponte integration."""
from __future__ import annotations

from homeassistant.components.camera import Camera
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceEntryType
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .client import TerceiraPonteClient
from .const import (
    CAMERAS,
    DEVICE_ID,
    DEVICE_NAME,
    DOMAIN,
    MANUFACTURER,
    MODEL,
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up camera entities from a config entry."""
    client: TerceiraPonteClient = hass.data[DOMAIN][entry.entry_id]
    async_add_entities(
        TerceiraPonteCamera(client, definition) for definition in CAMERAS
    )


class TerceiraPonteCamera(Camera):
    """Representation of a Terceira Ponte snapshot camera."""

    _attr_has_entity_name = True
    _attr_should_poll = False

    def __init__(self, client: TerceiraPonteClient, definition) -> None:
        """Initialize the camera entity."""
        super().__init__()
        self._client = client
        self._definition = definition
        self._attr_unique_id = definition.camera_id
        self._attr_name = definition.name
        self._attr_content_type = "image/jpeg"

    @property
    def available(self) -> bool:
        """Return whether the camera is available."""
        return self._client.get_camera_state(self._definition.camera_id).available

    @property
    def device_info(self) -> dict:
        """Return device information for the shared service device."""
        return {
            "identifiers": {(DOMAIN, DEVICE_ID)},
            "name": DEVICE_NAME,
            "manufacturer": MANUFACTURER,
            "model": MODEL,
            "entry_type": DeviceEntryType.SERVICE,
        }

    @property
    def extra_state_attributes(self) -> dict[str, str | int | None]:
        """Return extra state attributes."""
        state = self._client.get_camera_state(self._definition.camera_id)
        return {
            "camera_id": self._definition.camera_id,
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
            return await self._client.async_get_camera_image(self._definition.camera_id)
        finally:
            if self.hass is not None:
                self.async_write_ha_state()
