"""Diagnostics: cache settings and which cameras answer. Nothing secret is stored."""

from __future__ import annotations

from typing import Any

from homeassistant.core import HomeAssistant

from . import TerceiraPonteConfigEntry
from .const import CAMERAS


async def async_get_config_entry_diagnostics(
    hass: HomeAssistant, entry: TerceiraPonteConfigEntry
) -> dict[str, Any]:
    """Return options and camera availability."""
    client = entry.runtime_data
    return {
        "options": dict(entry.options),
        "cameras": {camera_id: client.is_available(camera_id) for camera_id in CAMERAS},
    }
