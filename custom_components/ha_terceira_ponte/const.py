"""Constants for the ha_terceira_ponte integration."""
from __future__ import annotations

from dataclasses import dataclass

DOMAIN = "ha_terceira_ponte"
NAME = "Terceira Ponte"

BASE_URL = "https://terceiraponte.ceturb.es.gov.br"
AUTH_TOKEN_PATH = "/api/auth/token"
REGISTER_ACCESS_PATH = "/api/acesso/registrar"
IMAGE_PATH_TEMPLATE = "/api/imagem/{camera_id}"

CONF_CACHE_TTL_SECONDS = "cache_ttl_seconds"
DEFAULT_CACHE_TTL_SECONDS = 10
MIN_CACHE_TTL_SECONDS = 5
MAX_CACHE_TTL_SECONDS = 60

REQUEST_TIMEOUT_SECONDS = 10
TOKEN_REFRESH_SKEW_SECONDS = 300

DEVICE_ID = "ha_terceira_ponte_cameras"
DEVICE_NAME = "CETURB Terceira Ponte"
MANUFACTURER = "CETURB-ES"
MODEL = "Terceira Ponte Cameras"

PLATFORMS: tuple[str, ...] = ("camera",)


@dataclass(frozen=True, slots=True)
class CameraDefinition:
    """Static definition for a CETURB camera."""

    camera_id: str
    name: str


CAMERAS: tuple[CameraDefinition, ...] = (
    CameraDefinition(camera_id="Subida_Vix", name="Subida Vitória"),
    CameraDefinition(camera_id="Descida_Vix", name="Descida Vitória"),
    CameraDefinition(camera_id="Subida_VilaVelha", name="Subida Vila Velha"),
    CameraDefinition(camera_id="Descida_VilaVelha", name="Descida Vila Velha"),
)

DEFAULT_TEST_CAMERA_ID = CAMERAS[0].camera_id
