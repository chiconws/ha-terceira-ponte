"""Constants for the ha_terceira_ponte integration."""
from __future__ import annotations

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
IMAGE_FETCH_RETRY_ATTEMPTS = 3
IMAGE_FETCH_RETRY_DELAY_SECONDS = 0.75

# camera_id -> entity name
CAMERAS: dict[str, str] = {
    "Subida_Vix": "Subida Vitória",
    "Descida_Vix": "Descida Vitória",
    "Subida_VilaVelha": "Subida Vila Velha",
    "Descida_VilaVelha": "Descida Vila Velha",
}
