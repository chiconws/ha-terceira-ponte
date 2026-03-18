"""HTTP client for the ha_terceira_ponte integration."""
from __future__ import annotations

import asyncio
import base64
import binascii
import json
import logging
import time
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

from aiohttp import ClientError, ClientResponseError, ClientSession
import async_timeout

from .const import (
    AUTH_TOKEN_PATH,
    BASE_URL,
    DEFAULT_TEST_CAMERA_ID,
    IMAGE_FETCH_RETRY_ATTEMPTS,
    IMAGE_FETCH_RETRY_DELAY_SECONDS,
    IMAGE_PATH_TEMPLATE,
    REGISTER_ACCESS_PATH,
    REQUEST_TIMEOUT_SECONDS,
    TOKEN_REFRESH_SKEW_SECONDS,
)

_LOGGER = logging.getLogger(__name__)


class TerceiraPonteError(Exception):
    """Base integration error."""


class CannotConnectError(TerceiraPonteError):
    """Raised when the service cannot be reached."""


class AuthenticationError(TerceiraPonteError):
    """Raised when authentication fails."""


@dataclass(slots=True)
class CameraState:
    """Current state for a camera feed."""

    available: bool = True
    last_success_at: datetime | None = None
    bytes_size: int | None = None
    content_type: str | None = None
    last_error: str | None = None


@dataclass(slots=True)
class CachedImage:
    """Cached snapshot payload."""

    data: bytes
    fetched_at: float
    content_type: str


class TerceiraPonteClient:
    """Client that handles auth, caching and snapshot retrieval."""

    def __init__(
        self,
        session: ClientSession,
        *,
        cache_ttl_seconds: int,
        base_url: str = BASE_URL,
    ) -> None:
        """Initialize the client."""
        self._session = session
        self._cache_ttl_seconds = cache_ttl_seconds
        self._base_url = base_url.rstrip("/")
        self._token: str | None = None
        self._token_expires_at: datetime | None = None
        self._token_lock = asyncio.Lock()
        self._camera_locks: dict[str, asyncio.Lock] = {}
        self._image_cache: dict[str, CachedImage] = {}
        self._camera_states: dict[str, CameraState] = {}

    async def async_validate_connection(self) -> None:
        """Validate auth and image retrieval."""
        await self.async_get_camera_image(DEFAULT_TEST_CAMERA_ID)

    async def async_register_access(self) -> None:
        """Register public access in best-effort mode."""
        try:
            token = await self._async_get_token()
            headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
            async with async_timeout.timeout(REQUEST_TIMEOUT_SECONDS):
                async with self._session.post(
                    f"{self._base_url}{REGISTER_ACCESS_PATH}",
                    headers=headers,
                    data="{}",
                ) as response:
                    if response.status >= 400:
                        body = await response.text()
                        _LOGGER.debug(
                            "Access registration failed with status %s: %s",
                            response.status,
                            body,
                        )
        except TerceiraPonteError as err:
            _LOGGER.debug("Access registration failed: %s", err)
        except (ClientError, TimeoutError) as err:
            _LOGGER.debug("Access registration request failed: %s", err)

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
                image, content_type = await self._async_fetch_camera_image(camera_id)
            except TerceiraPonteError as err:
                state = self._camera_states.setdefault(camera_id, CameraState())
                state.last_error = str(err)

                if cache is not None:
                    state.available = True
                    state.bytes_size = len(cache.data)
                    state.content_type = cache.content_type
                    _LOGGER.debug(
                        "Using stale cached image for camera %s after fetch failure: %s",
                        camera_id,
                        err,
                    )
                    return cache.data

                state.available = False
                raise

            cached = CachedImage(
                data=image,
                fetched_at=self._monotonic(),
                content_type=content_type,
            )
            self._image_cache[camera_id] = cached

            state = self._camera_states.setdefault(camera_id, CameraState())
            state.available = True
            state.last_success_at = self._utcnow()
            state.bytes_size = len(image)
            state.content_type = content_type
            state.last_error = None

            return image

    def get_camera_state(self, camera_id: str) -> CameraState:
        """Return camera state metadata."""
        return self._camera_states.setdefault(camera_id, CameraState())

    def set_cache_ttl(self, cache_ttl_seconds: int) -> None:
        """Update cache TTL at runtime."""
        self._cache_ttl_seconds = cache_ttl_seconds

    async def _async_fetch_camera_image(self, camera_id: str) -> tuple[bytes, str]:
        """Fetch a camera snapshot with auth and transient error retries."""
        image_path = IMAGE_PATH_TEMPLATE.format(camera_id=camera_id)
        image_url = f"{self._base_url}{image_path}"

        for attempt in range(IMAGE_FETCH_RETRY_ATTEMPTS):
            force_refresh = False

            while True:
                token = await self._async_get_token(force_refresh=force_refresh)
                headers = {"Authorization": f"Bearer {token}"}

                try:
                    async with async_timeout.timeout(REQUEST_TIMEOUT_SECONDS):
                        async with self._session.get(image_url, headers=headers) as response:
                            if response.status == 401:
                                if not force_refresh:
                                    self._token = None
                                    self._token_expires_at = None
                                    force_refresh = True
                                    continue
                                raise AuthenticationError(
                                    "Authentication failed while fetching image"
                                )

                            if response.status >= 500:
                                body = await response.text()
                                if attempt < IMAGE_FETCH_RETRY_ATTEMPTS - 1:
                                    _LOGGER.debug(
                                        "Image request for camera %s failed with status %s, retrying: %s",
                                        camera_id,
                                        response.status,
                                        body,
                                    )
                                    await asyncio.sleep(IMAGE_FETCH_RETRY_DELAY_SECONDS)
                                    break
                                raise CannotConnectError(
                                    f"Image request failed with status {response.status}: {body}"
                                )

                            if response.status >= 400:
                                body = await response.text()
                                raise CannotConnectError(
                                    f"Image request failed with status {response.status}: {body}"
                                )

                            return await response.read(), response.headers.get(
                                "Content-Type",
                                "image/jpeg",
                            )
                except (ClientError, TimeoutError) as err:
                    if attempt < IMAGE_FETCH_RETRY_ATTEMPTS - 1:
                        _LOGGER.debug(
                            "Image request for camera %s failed, retrying: %s",
                            camera_id,
                            err,
                        )
                        await asyncio.sleep(IMAGE_FETCH_RETRY_DELAY_SECONDS)
                        break
                    raise CannotConnectError("Could not fetch image") from err

        raise CannotConnectError("Image retry exhausted")

    async def _async_get_token(self, *, force_refresh: bool = False) -> str:
        """Return a valid JWT token."""
        async with self._token_lock:
            if not force_refresh and self._token is not None and not self._should_refresh_token():
                return self._token

            try:
                async with async_timeout.timeout(REQUEST_TIMEOUT_SECONDS):
                    async with self._session.get(
                        f"{self._base_url}{AUTH_TOKEN_PATH}",
                    ) as response:
                        response.raise_for_status()
                        payload = await response.json()
            except ClientResponseError as err:
                raise AuthenticationError("Failed to obtain JWT token") from err
            except (ClientError, TimeoutError) as err:
                raise CannotConnectError("Could not obtain JWT token") from err

            token = payload.get("token")
            if not isinstance(token, str) or not token:
                raise AuthenticationError("JWT token missing from response")

            self._token = token
            self._token_expires_at = self._decode_token_exp(token)
            return token

    def _should_refresh_token(self) -> bool:
        """Return whether the current JWT is close to expiring."""
        if self._token is None or self._token_expires_at is None:
            return True

        refresh_at = self._token_expires_at - timedelta(seconds=TOKEN_REFRESH_SKEW_SECONDS)
        return self._utcnow() >= refresh_at

    def _decode_token_exp(self, token: str) -> datetime:
        """Decode the JWT exp claim without verifying signature."""
        try:
            payload_segment = token.split(".")[1]
            padding = "=" * (-len(payload_segment) % 4)
            decoded = base64.urlsafe_b64decode(payload_segment + padding)
            payload = json.loads(decoded.decode("utf-8"))
            exp = int(payload["exp"])
        except (IndexError, KeyError, ValueError, TypeError, json.JSONDecodeError, binascii.Error) as err:
            raise AuthenticationError("Could not decode JWT expiration") from err

        return datetime.fromtimestamp(exp, tz=UTC)

    def _is_cache_valid(self, cache: CachedImage) -> bool:
        """Return whether cache is still valid."""
        return (self._monotonic() - cache.fetched_at) < self._cache_ttl_seconds

    def _utcnow(self) -> datetime:
        """Wrapper for testability."""
        return datetime.now(tz=UTC)

    def _monotonic(self) -> float:
        """Wrapper for testability."""
        return time.monotonic()
