# Astrocartography Backend (Rust)

Rust/Axum port of the Python FastAPI backend in `../backend`.

## Run

```bat
run.bat
```

Or:

```sh
cargo run
```

Listens on `http://0.0.0.0:8000` by default (override with `PORT`).

## Implemented endpoints

- `GET /healthz`
- `POST /api/astrocartography`
- `POST /api/transit-acg`
- `POST /api/progressed-acg`
- `POST /api/geodetic`
- `POST /api/fixed-stars`
- `POST /api/midpoints`
- `POST /api/crossings`
- `POST /api/location-analysis`

Ephemeris uses the bundled files at `../backend/ephe` (Swiss mode) and falls back to Moshier if absent. Outputs are validated against the Python implementation (matching line/point/paran counts and coordinates).

## Remaining work

- `top-cities`, `travel-timing`, `trip-plan`, `births` CRUD, `solar/lunar-return`, `electional`.
- Full frontend build integration (serve `../frontend/dist`).
- Golden-file accuracy tests against Python.
