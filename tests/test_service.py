"""Integration-level tests against a mocked CETURB service."""

import logging

import pytest
from homeassistant.config_entries import ConfigEntryState
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from pytest_homeassistant_custom_component.common import MockConfigEntry
from pytest_homeassistant_custom_component.test_util.aiohttp import AiohttpClientMocker

from custom_components.terceira_ponte import client as client_module
from custom_components.terceira_ponte.const import (
    AUTH_TOKEN_PATH,
    BASE_URL,
    CAMERAS,
    DOMAIN,
    IMAGE_PATH_TEMPLATE,
    REGISTER_ACCESS_PATH,
)
from custom_components.terceira_ponte.diagnostics import async_get_config_entry_diagnostics

JPEG = b"\xff\xd8jpeg"


@pytest.fixture(autouse=True)
def no_retry_delay(monkeypatch):
    monkeypatch.setattr(client_module, "IMAGE_FETCH_RETRY_DELAY_SECONDS", 0)


def mock_service(aioclient_mock: AiohttpClientMocker, *, register_status: int = 200) -> None:
    aioclient_mock.get(f"{BASE_URL}{AUTH_TOKEN_PATH}", json={"token": "jwt"})
    aioclient_mock.post(f"{BASE_URL}{REGISTER_ACCESS_PATH}", status=register_status, text="no")
    for camera_id in CAMERAS:
        aioclient_mock.get(f"{BASE_URL}{IMAGE_PATH_TEMPLATE.format(camera_id=camera_id)}", content=JPEG)


@pytest.fixture
def entry(hass: HomeAssistant) -> MockConfigEntry:
    entry = MockConfigEntry(domain=DOMAIN, data={}, title="Terceira Ponte")
    entry.add_to_hass(hass)
    return entry


@pytest.mark.parametrize("register_status", [200, 500])
async def test_setup_unload_and_diagnostics(
    hass: HomeAssistant, aioclient_mock, entry, register_status
) -> None:
    mock_service(aioclient_mock, register_status=register_status)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    assert entry.state is ConfigEntryState.LOADED
    assert len(hass.states.async_entity_ids("camera")) == 4

    diag = await async_get_config_entry_diagnostics(hass, entry)
    assert diag["cameras"]["Subida_Vix"] is True

    assert await hass.config_entries.async_unload(entry.entry_id)
    assert entry.state is ConfigEntryState.NOT_LOADED


async def test_service_down_retries_setup(hass: HomeAssistant, aioclient_mock, entry) -> None:
    aioclient_mock.get(f"{BASE_URL}{AUTH_TOKEN_PATH}", status=503)
    await hass.config_entries.async_setup(entry.entry_id)
    assert entry.state is ConfigEntryState.SETUP_RETRY


async def test_user_flow_errors(hass: HomeAssistant, aioclient_mock) -> None:
    aioclient_mock.get(f"{BASE_URL}{AUTH_TOKEN_PATH}", status=503)
    result = await hass.config_entries.flow.async_init(DOMAIN, context={"source": "user"})
    result = await hass.config_entries.flow.async_configure(result["flow_id"], {})
    assert result["errors"] == {"base": "cannot_connect"}


async def test_user_flow_unexpected_error(hass: HomeAssistant, aioclient_mock) -> None:
    aioclient_mock.get(f"{BASE_URL}{AUTH_TOKEN_PATH}", exc=ValueError("boom"))
    result = await hass.config_entries.flow.async_init(DOMAIN, context={"source": "user"})
    result = await hass.config_entries.flow.async_configure(result["flow_id"], {})
    assert result["errors"] == {"base": "unknown"}


async def test_unavailable_is_logged_once(
    hass: HomeAssistant, aioclient_mock, caplog: pytest.LogCaptureFixture
) -> None:
    client = client_module.TerceiraPonteClient(
        async_get_clientsession(hass),
        cache_ttl_seconds=0,
    )
    url = f"{BASE_URL}{IMAGE_PATH_TEMPLATE.format(camera_id='Subida_Vix')}"
    aioclient_mock.get(f"{BASE_URL}{AUTH_TOKEN_PATH}", json={"token": "jwt"})
    aioclient_mock.get(url, status=404)
    caplog.set_level(logging.INFO)
    for _ in range(2):
        with pytest.raises(client_module.TerceiraPonteError):
            await client.async_get_camera_image("Subida_Vix")
    assert caplog.text.count("is unavailable") == 1
    assert not client.is_available("Subida_Vix")

    aioclient_mock.clear_requests()
    aioclient_mock.get(f"{BASE_URL}{AUTH_TOKEN_PATH}", json={"token": "jwt"})
    aioclient_mock.get(url, content=JPEG)
    assert await client.async_get_camera_image("Subida_Vix") == JPEG
    assert "available again" in caplog.text
