"""Tests for the ha_terceira_ponte client."""
from __future__ import annotations

from collections import defaultdict
import json

import pytest

from custom_components.ha_terceira_ponte.client import (
    CannotConnectError,
    TerceiraPonteClient,
)


class FakeResponse:
    """Minimal async response object."""

    def __init__(
        self,
        *,
        status: int,
        json_data: dict | None = None,
        body: bytes | None = None,
        text: str = "",
        headers: dict[str, str] | None = None,
    ) -> None:
        self.status = status
        self._json_data = json_data
        self._body = body or b""
        self._text = text
        self.headers = headers or {}

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        return False

    def raise_for_status(self) -> None:
        if self.status >= 400:
            raise CannotConnectError(f"HTTP {self.status}")

    async def json(self) -> dict:
        if self._json_data is not None:
            return self._json_data
        return json.loads(self._body.decode("utf-8"))

    async def read(self) -> bytes:
        return self._body

    async def text(self) -> str:
        return self._text


class FakeSession:
    """Minimal fake aiohttp client session."""

    def __init__(self) -> None:
        self.calls: list[tuple[str, str]] = []
        self._responses: dict[tuple[str, str], list[FakeResponse]] = defaultdict(list)

    def queue(self, method: str, url: str, response: FakeResponse) -> None:
        self._responses[(method, url)].append(response)

    def get(self, url: str, **kwargs):
        self.calls.append(("GET", url))
        return self._responses[("GET", url)].pop(0)

    def post(self, url: str, **kwargs):
        self.calls.append(("POST", url))
        return self._responses[("POST", url)].pop(0)


def build_token(exp: int) -> str:
    """Build a fake JWT with an exp claim."""
    header = b'{"alg":"HS256","typ":"JWT"}'
    payload = json.dumps({"exp": exp}).encode("utf-8")

    def encode(chunk: bytes) -> str:
        import base64

        return base64.urlsafe_b64encode(chunk).decode("utf-8").rstrip("=")

    return f"{encode(header)}.{encode(payload)}.signature"


@pytest.mark.asyncio
async def test_client_caches_images_within_ttl() -> None:
    """The client should reuse cached snapshots within the TTL."""
    session = FakeSession()
    token_url = "https://terceiraponte.ceturb.es.gov.br/api/auth/token"
    image_url = "https://terceiraponte.ceturb.es.gov.br/api/imagem/Subida_Vix"

    session.queue("GET", token_url, FakeResponse(status=200, json_data={"token": build_token(4070908800)}))
    session.queue(
        "GET",
        image_url,
        FakeResponse(status=200, body=b"image-one", headers={"Content-Type": "image/jpeg"}),
    )

    client = TerceiraPonteClient(session, cache_ttl_seconds=10)
    now = [100.0]
    client._monotonic = lambda: now[0]  # type: ignore[method-assign]

    first = await client.async_get_camera_image("Subida_Vix")
    second = await client.async_get_camera_image("Subida_Vix")

    assert first == b"image-one"
    assert second == b"image-one"
    assert session.calls.count(("GET", image_url)) == 1


@pytest.mark.asyncio
async def test_client_retries_when_image_returns_401() -> None:
    """The client should refresh the token and retry once on 401."""
    session = FakeSession()
    token_url = "https://terceiraponte.ceturb.es.gov.br/api/auth/token"
    image_url = "https://terceiraponte.ceturb.es.gov.br/api/imagem/Subida_Vix"

    session.queue("GET", token_url, FakeResponse(status=200, json_data={"token": build_token(4070908800)}))
    session.queue("GET", image_url, FakeResponse(status=401, text="unauthorized"))
    session.queue("GET", token_url, FakeResponse(status=200, json_data={"token": build_token(4070909800)}))
    session.queue(
        "GET",
        image_url,
        FakeResponse(status=200, body=b"image-two", headers={"Content-Type": "image/jpeg"}),
    )

    client = TerceiraPonteClient(session, cache_ttl_seconds=10)
    image = await client.async_get_camera_image("Subida_Vix")

    assert image == b"image-two"
    assert session.calls == [
        ("GET", token_url),
        ("GET", image_url),
        ("GET", token_url),
        ("GET", image_url),
    ]


@pytest.mark.asyncio
async def test_client_retries_when_image_returns_500() -> None:
    """The client should retry transient server errors before succeeding."""
    session = FakeSession()
    token_url = "https://terceiraponte.ceturb.es.gov.br/api/auth/token"
    image_url = "https://terceiraponte.ceturb.es.gov.br/api/imagem/Subida_Vix"

    session.queue("GET", token_url, FakeResponse(status=200, json_data={"token": build_token(4070908800)}))
    session.queue("GET", image_url, FakeResponse(status=500, text="server error"))
    session.queue("GET", image_url, FakeResponse(status=500, text="server error"))
    session.queue(
        "GET",
        image_url,
        FakeResponse(status=200, body=b"image-three", headers={"Content-Type": "image/jpeg"}),
    )

    client = TerceiraPonteClient(session, cache_ttl_seconds=10)
    image = await client.async_get_camera_image("Subida_Vix")

    assert image == b"image-three"
    assert session.calls == [
        ("GET", token_url),
        ("GET", image_url),
        ("GET", image_url),
        ("GET", image_url),
    ]


@pytest.mark.asyncio
async def test_client_returns_stale_cache_when_refresh_fails() -> None:
    """The client should keep serving the last image when refresh fails."""
    session = FakeSession()
    token_url = "https://terceiraponte.ceturb.es.gov.br/api/auth/token"
    image_url = "https://terceiraponte.ceturb.es.gov.br/api/imagem/Subida_Vix"

    session.queue("GET", token_url, FakeResponse(status=200, json_data={"token": build_token(4070908800)}))
    session.queue(
        "GET",
        image_url,
        FakeResponse(status=200, body=b"image-one", headers={"Content-Type": "image/jpeg"}),
    )
    session.queue("GET", image_url, FakeResponse(status=500, text="server error"))
    session.queue("GET", image_url, FakeResponse(status=500, text="server error"))
    session.queue("GET", image_url, FakeResponse(status=500, text="server error"))

    client = TerceiraPonteClient(session, cache_ttl_seconds=10)
    now = [100.0]
    client._monotonic = lambda: now[0]  # type: ignore[method-assign]

    first = await client.async_get_camera_image("Subida_Vix")
    now[0] = 111.0
    second = await client.async_get_camera_image("Subida_Vix")
    state = client.get_camera_state("Subida_Vix")

    assert first == b"image-one"
    assert second == b"image-one"
    assert state.available is True
    assert state.bytes_size == len(b"image-one")
    assert state.content_type == "image/jpeg"
    assert state.last_error == "Image request failed with status 500: server error"


@pytest.mark.asyncio
async def test_client_marks_camera_unavailable_after_failed_fetch() -> None:
    """The camera should be marked unavailable when a fetch fails without cache."""
    session = FakeSession()
    token_url = "https://terceiraponte.ceturb.es.gov.br/api/auth/token"
    image_url = "https://terceiraponte.ceturb.es.gov.br/api/imagem/Subida_Vix"

    session.queue("GET", token_url, FakeResponse(status=200, json_data={"token": build_token(4070908800)}))
    session.queue("GET", image_url, FakeResponse(status=500, text="server error"))
    session.queue("GET", image_url, FakeResponse(status=500, text="server error"))
    session.queue("GET", image_url, FakeResponse(status=500, text="server error"))

    client = TerceiraPonteClient(session, cache_ttl_seconds=10)

    with pytest.raises(CannotConnectError, match="Image request failed with status 500: server error"):
        await client.async_get_camera_image("Subida_Vix")

    assert client.get_camera_state("Subida_Vix").available is False
