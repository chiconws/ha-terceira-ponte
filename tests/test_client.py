"""Tests for the terceira_ponte client."""

from collections import defaultdict
import json
from typing import Any, Self, cast

from aiohttp import ClientSession
import pytest

from custom_components.terceira_ponte.client import (
    TerceiraPonteClient,
    TerceiraPonteError,
)
from custom_components.terceira_ponte.const import (
    AUTH_TOKEN_PATH,
    BASE_URL,
    IMAGE_PATH_TEMPLATE,
)

CAMERA = "Subida_Vix"
TOKEN_URL = f"{BASE_URL}{AUTH_TOKEN_PATH}"
IMAGE_URL = f"{BASE_URL}{IMAGE_PATH_TEMPLATE.format(camera_id=CAMERA)}"


class FakeResponse:
    """Minimal async response object."""

    def __init__(
        self,
        *,
        status: int,
        json_data: dict[str, Any] | None = None,
        body: bytes | None = None,
        text: str = "",
        headers: dict[str, str] | None = None,
    ) -> None:
        """Store the canned response."""
        self.status = status
        self._json_data = json_data
        self._body = body or b""
        self._text = text
        self.headers = headers or {}

    async def __aenter__(self) -> Self:
        """Enter the response context."""
        return self

    async def __aexit__(self, *_: object) -> bool:
        """Exit the response context."""
        return False

    def raise_for_status(self) -> None:
        """Raise for HTTP error statuses."""
        if self.status >= 400:
            raise TerceiraPonteError(f"HTTP {self.status}")

    async def json(self) -> dict[str, Any]:
        """Return the JSON body."""
        if self._json_data is not None:
            return self._json_data
        return cast(dict[str, Any], json.loads(self._body.decode("utf-8")))

    async def read(self) -> bytes:
        """Return the raw body."""
        return self._body

    async def text(self) -> str:
        """Return the text body."""
        return self._text


class FakeSession:
    """Minimal fake aiohttp client session."""

    def __init__(self) -> None:
        """Start with no calls and no queued responses."""
        self.calls: list[tuple[str, str]] = []
        self._responses: dict[tuple[str, str], list[FakeResponse]] = defaultdict(list)

    def queue(self, method: str, url: str, response: FakeResponse) -> None:
        """Queue a response for a method and URL."""
        self._responses[(method, url)].append(response)

    def get(self, url: str, **_: object) -> FakeResponse:
        """Return the next queued GET response."""
        self.calls.append(("GET", url))
        return self._responses[("GET", url)].pop(0)

    def post(self, url: str, **_: object) -> FakeResponse:
        """Return the next queued POST response."""
        self.calls.append(("POST", url))
        return self._responses[("POST", url)].pop(0)


def make_client(session: FakeSession) -> TerceiraPonteClient:
    """Build a client on top of the fake session."""
    return TerceiraPonteClient(cast(ClientSession, session), cache_ttl_seconds=10)


@pytest.mark.asyncio
async def test_client_caches_images_within_ttl() -> None:
    """The client should reuse cached snapshots within the TTL."""
    session = FakeSession()
    session.queue(
        "GET", TOKEN_URL, FakeResponse(status=200, json_data={"token": "token-one"})
    )
    session.queue(
        "GET",
        IMAGE_URL,
        FakeResponse(
            status=200, body=b"image-one", headers={"Content-Type": "image/jpeg"}
        ),
    )

    client = make_client(session)
    now = [100.0]
    client._monotonic = lambda: now[0]  # type: ignore[method-assign]  # noqa: SLF001

    first = await client.async_get_camera_image(CAMERA)
    second = await client.async_get_camera_image(CAMERA)

    assert first == b"image-one"
    assert second == b"image-one"
    assert session.calls.count(("GET", IMAGE_URL)) == 1


@pytest.mark.asyncio
async def test_client_retries_when_image_returns_401() -> None:
    """The client should refresh the token and retry once on 401."""
    session = FakeSession()
    session.queue(
        "GET", TOKEN_URL, FakeResponse(status=200, json_data={"token": "token-one"})
    )
    session.queue("GET", IMAGE_URL, FakeResponse(status=401, text="unauthorized"))
    session.queue(
        "GET", TOKEN_URL, FakeResponse(status=200, json_data={"token": "token-two"})
    )
    session.queue(
        "GET",
        IMAGE_URL,
        FakeResponse(
            status=200, body=b"image-two", headers={"Content-Type": "image/jpeg"}
        ),
    )

    client = make_client(session)
    image = await client.async_get_camera_image(CAMERA)

    assert image == b"image-two"
    assert session.calls == [
        ("GET", TOKEN_URL),
        ("GET", IMAGE_URL),
        ("GET", TOKEN_URL),
        ("GET", IMAGE_URL),
    ]


@pytest.mark.asyncio
async def test_client_retries_when_image_returns_500() -> None:
    """The client should retry transient server errors before succeeding."""
    session = FakeSession()
    session.queue(
        "GET", TOKEN_URL, FakeResponse(status=200, json_data={"token": "token-one"})
    )
    session.queue("GET", IMAGE_URL, FakeResponse(status=500, text="server error"))
    session.queue("GET", IMAGE_URL, FakeResponse(status=500, text="server error"))
    session.queue(
        "GET",
        IMAGE_URL,
        FakeResponse(
            status=200, body=b"image-three", headers={"Content-Type": "image/jpeg"}
        ),
    )

    client = make_client(session)
    image = await client.async_get_camera_image(CAMERA)

    assert image == b"image-three"
    assert session.calls == [
        ("GET", TOKEN_URL),
        ("GET", IMAGE_URL),
        ("GET", IMAGE_URL),
        ("GET", IMAGE_URL),
    ]


@pytest.mark.asyncio
async def test_client_returns_stale_cache_when_refresh_fails() -> None:
    """The client should keep serving the last image when refresh fails."""
    session = FakeSession()
    session.queue(
        "GET", TOKEN_URL, FakeResponse(status=200, json_data={"token": "token-one"})
    )
    session.queue(
        "GET",
        IMAGE_URL,
        FakeResponse(
            status=200, body=b"image-one", headers={"Content-Type": "image/jpeg"}
        ),
    )
    session.queue("GET", IMAGE_URL, FakeResponse(status=500, text="server error"))
    session.queue("GET", IMAGE_URL, FakeResponse(status=500, text="server error"))
    session.queue("GET", IMAGE_URL, FakeResponse(status=500, text="server error"))

    client = make_client(session)
    now = [100.0]
    client._monotonic = lambda: now[0]  # type: ignore[method-assign]  # noqa: SLF001

    first = await client.async_get_camera_image(CAMERA)
    now[0] = 111.0
    second = await client.async_get_camera_image(CAMERA)

    assert first == b"image-one"
    assert second == b"image-one"
    assert client.is_available(CAMERA) is True


@pytest.mark.asyncio
async def test_client_marks_camera_unavailable_after_failed_fetch() -> None:
    """The camera should be marked unavailable when a fetch fails without cache."""
    session = FakeSession()
    session.queue(
        "GET", TOKEN_URL, FakeResponse(status=200, json_data={"token": "token-one"})
    )
    session.queue("GET", IMAGE_URL, FakeResponse(status=500, text="server error"))
    session.queue("GET", IMAGE_URL, FakeResponse(status=500, text="server error"))
    session.queue("GET", IMAGE_URL, FakeResponse(status=500, text="server error"))

    client = make_client(session)

    with pytest.raises(
        TerceiraPonteError, match="Image request failed with status 500: server error"
    ):
        await client.async_get_camera_image(CAMERA)

    assert client.is_available(CAMERA) is False
