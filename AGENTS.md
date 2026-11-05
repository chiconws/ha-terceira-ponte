# Agent Notes: Terceira Ponte

Language: README in **pt-BR**; code, logs and `strings.json` in English; translations en + pt-BR.

## Overview

Cloud integration (`cloud_polling`, `integration_type: service`) that exposes the four public
CETURB-ES cameras of the Terceira Ponte bridge as `camera` entities. No account; one entry.

## Code structure

All code in `custom_components/terceira_ponte/`.

- `client.py`: `TerceiraPonteClient`, no HA imports. Public JWT from `/api/auth/token`, snapshots from `/api/imagem/<id>`, per-camera cache and lock, retries on 5xx/timeouts, logs once when a camera goes down and once when it is back.
- `__init__.py`: validates one snapshot before setup (`ConfigEntryNotReady`), stores the client in `entry.runtime_data`, registers the access (best effort, like the website).
- `camera.py`: one `TerceiraPonteCamera` per entry in `const.CAMERAS`, all on a single service device.
- `config_flow.py`: confirm-only user step; options set the cache TTL (`OptionsFlowWithReload`).
- `diagnostics.py`: options and per-camera availability.

## Key concepts

- No polling: HA asks for an image when a dashboard shows it; the cache TTL absorbs bursts.
- A camera is unavailable only after a failed fetch with no cached image to fall back on.

## Local validation (before push)

`.venv/bin/prek install` once per clone; the git hook then runs ruff (lint + format), codespell, yamllint, prettier, zizmor, markdownlint, mypy and Pyright. By hand:

```bash
SKIP=no-commit-to-branch .venv/bin/prek run --all-files --hook-stage manual
.venv/bin/coverage run -m pytest -q && .venv/bin/coverage report
```

Contributor setup: `CONTRIBUTING.md`.

## Deviations from standard

- No `coordinator.py`: nothing is polled; images are fetched on demand with a cache.
- No `entity.py`: a single entity class.
