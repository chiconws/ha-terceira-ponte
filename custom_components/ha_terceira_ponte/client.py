"""HTTP client for the ha_terceira_ponte integration."""
from __future__ import annotations

import asyncio
import logging
import time
from dataclasses import dataclass

from aiohttp import ClientError, ClientSession

from .const import (
    AUTH_TOKEN_PATH,
    BASE_URL,
    CAMERAS,
    IMAGE_FETCH_RETRY_ATTEMPTS,
    IMAGE_FETCH_RETRY_DELAY_SECONDS,
    IMAGE_PATH_TEMPLATE,
    REGISTER_ACCESS_PATH,
    REQUEST_TIMEOUT_SECONDS,
)

_LOGGER = logging.getLogger(__name__)


class TerceiraPonteError(Exception):
    """Raised when the service cannot be reached or rejects us."""


@dataclass(slots=True)
class CachedImage:
    """Cached snapshot payload."""

    data: bytes
    fetched_at: float


class TerceiraPonteClient:
    """Client that handles auth, caching and snapshot retrieval."""

    def __init__(self, session: ClientSession, *, cache_ttl_seconds: int) -> None:
        """Initialize the client."""
        self._session = session
        self._cache_ttl_seconds = cache_ttl_seconds
        self._token: str | None = None
        self._token_lock = asyncio.Lock()
        self._camera_locks: dict[str, asyncio.Lock] = {}
        self._image_cache: dict[str, CachedImage] = {}
        self._unavailable: set[str] = set()

    async def async_validate_connection(self) -> None:
        """Validate auth and image retrieval."""
        await self.async_get_camera_image(next(iter(CAMERAS)))

    async def async_register_access(self) -> None:
        """Register public access in best-effort mode."""
        try:
            token = await self._async_get_token()
            headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
            async with asyncio.timeout(REQUEST_TIMEOUT_SECONDS):
                async with self._session.post(
                    f"{BASE_URL}{REGISTER_ACCESS_PATH}",
                    headers=headers,
                    data="{}",
                ) as response:
                    if response.status >= 400:
                        _LOGGER.debug(
                            "Access registration failed with status %s: %s",
                            response.status,
                            await response.text(),
                        )
        except (TerceiraPonteError, ClientError, TimeoutError) as err:
            _LOGGER.debug("Access registration failed: %s", err)

    async def async_get_camera_image(self, camera_id: str) -> bytes:
        """Return a cached snapshot or fetch a fresh one."""
        cache = self._image_cache.get(camera_id)
        if cache is not None and self._is_cache_valid(cache):
            return cache.data

        lock = self._camera_locks.setdefault(camera_id, asyncio.Lock())
        async with lock:
            cache = self._image_cache.get(camera_id)
            if cache is not None and self._is_cache_valid(cache):
                return cache.data

            try:
                image = await self._async_fetch_camera_image(camera_id)
            except TerceiraPonteError as err:
                if cache is None:
                    self._unavailable.add(camera_id)
                    raise
                _LOGGER.debug(
                    "Using stale cached image for camera %s after fetch failure: %s",
                    camera_id,
                    err,
                )
                return cache.data

            self._image_cache[camera_id] = CachedImage(image, self._monotonic())
            self._unavailable.discard(camera_id)
            return image

    def is_available(self, camera_id: str) -> bool:
        """Return False once a fetch failed with no cached image to fall back on."""
        return camera_id not in self._unavailable

    async def _async_fetch_camera_image(self, camera_id: str) -> bytes:
        """Fetch a camera snapshot, refreshing the token once on 401 and retrying transient errors."""
        image_url = f"{BASE_URL}{IMAGE_PATH_TEMPLATE.format(camera_id=camera_id)}"
        refreshed = False
        attempt = 0

        while True:
            token = await self._async_get_token()
            headers = {"Authorization": f"Bearer {token}"}

            try:
                async with asyncio.timeout(REQUEST_TIMEOUT_SECONDS):
                    async with self._session.get(image_url, headers=headers) as response:
                        if response.status == 401 and not refreshed:
                            self._token = None
                            refreshed = True
                            continue
                        if response.status < 400:
                            return await response.read()
                        error = TerceiraPonteError(
                            f"Image request failed with status {response.status}: "
                            f"{await response.text()}"
                        )
                        transient = response.status >= 500
            except (ClientError, TimeoutError) as err:
                error = TerceiraPonteError(f"Could not fetch image: {err}")
                transient = True

            attempt += 1
            if not transient or attempt >= IMAGE_FETCH_RETRY_ATTEMPTS:
                raise error
            _LOGGER.debug("Image request for camera %s failed, retrying: %s", camera_id, error)
            await asyncio.sleep(IMAGE_FETCH_RETRY_DELAY_SECONDS)

    async def _async_get_token(self) -> str:
        """Fetch a JWT token; it is dropped and refetched when the service answers 401."""
        async with self._token_lock:
            if self._token is not None:
                return self._token

            try:
                async with asyncio.timeout(REQUEST_TIMEOUT_SECONDS):
                    async with self._session.get(f"{BASE_URL}{AUTH_TOKEN_PATH}") as response:
                        response.raise_for_status()
                        payload = await response.json()
            except (ClientError, TimeoutError) as err:
                raise TerceiraPonteError("Could not obtain JWT token") from err

            token = payload.get("token")
            if not isinstance(token, str) or not token:
                raise TerceiraPonteError("JWT token missing from response")

            self._token = token
            return token

    def _is_cache_valid(self, cache: CachedImage) -> bool:
        """Return whether cache is still valid."""
        return (self._monotonic() - cache.fetched_at) < self._cache_ttl_seconds

    def _monotonic(self) -> float:
        """Wrapper for testability."""
        return time.monotonic()
