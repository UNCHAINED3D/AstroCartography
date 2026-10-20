"""
FastAPI application: astrocartography endpoint.

Single endpoint for the basic version:
    POST /api/astrocartography  -> ACG lines + subplanetary points (GeoJSON-ish)
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Optional

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from acg import generate_acg
from acg import (
    generate_transit_acg,
    generate_progressed_acg,
    generate_geodetic,
    generate_fixed_star_lines,
    generate_midpoint_lines,
    generate_crossings,
)
from analysis import generate_analysis
from analysis import generate_analysis
from electional import rate_travel_window
from returns import generate_solar_return_acg, generate_lunar_return_acg

from cache import cached, payload_key
from cities import rank_cities_for_birth, rank_cities_for_couple
from births import (
    create_entry,
    list_entries,
    get_entry,
    update_entry,
    delete_entry,
)

app = FastAPI(title="Astrocartography API", version="0.1.0")

# Compress API responses + HTML/JS/CSS. Compresses any response larger than 500
# bytes, which covers the large three.js/globe.gl bundle the frontend serves.
app.add_middleware(GZipMiddleware, minimum_size=500)


# Hashed build assets are content-addressed and immutable: cache them hard so
# repeat visits never re-download the 1.8 MB three.js/globe.gl chunk.
@app.middleware("http")
async def cache_static_assets(request: Request, call_next):
    response = await call_next(request)
    # Hashed build assets and the Cesium engine payload are content-addressed
    # and immutable: cache them hard so repeat visits never re-download them.
    if request.url.path.startswith(("/assets/", "/cesium/")):
        response.headers["Cache-Control"] = "public, max-age=31536000, immutable"
    return response


app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # dev only; lock down per-deployment later
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- Serve the built frontend (frontend/dist) as static files --------------
# This lets a single `python run.py` serve both the API and a production build
# of the UI (no Vite dev server, no unminified code, proper HTTP caching).
_DIST = Path(__file__).resolve().parent.parent.parent / "frontend" / "dist"
_ASSETS = _DIST / "assets"


def _cache_headers() -> dict[str, str]:
    # Hashed asset filenames are content-addressed and immutable; cache hard.
    return {"Cache-Control": "public, max-age=31536000, immutable"}


if _DIST.exists() and _ASSETS.exists():
    # Hashed build assets (JS/CSS) — long-lived immutable cache.
    app.mount(
        "/assets",
        StaticFiles(directory=str(_ASSETS), html=False, check_dir=False),
        name="assets",
    )


class Birth(BaseModel):
    datetime: str  # ISO-8601, timezone-aware, e.g. "1990-05-15T14:30:00+10:00"
    latitude: float
    longitude: float


class ACGRequest(BaseModel):
    birth: Birth
    bodies: Optional[list[str]] = None
    lat_step: float = 1.0


class TransitACGRequest(BaseModel):
    birth: Birth
    transit_iso: str  # ISO-8601 with UTC offset
    bodies: Optional[list[str]] = None
    lat_step: float = 1.0


class ProgressedACGRequest(BaseModel):
    birth: Birth
    age_years: float  # secondary progression: 1 day = 1 year
    bodies: Optional[list[str]] = None
    lat_step: float = 1.0


class GeodeticRequest(BaseModel):
    birth: Birth


class FixedStarsRequest(BaseModel):
    birth: Birth
    names: Optional[list[str]] = None


class MidpointsRequest(BaseModel):
    birth: Birth
    pairs: Optional[list[list[str]]] = None


class CrossingsRequest(BaseModel):
    birth: Birth
    bodies: Optional[list[str]] = None


class LocationAnalysisRequest(BaseModel):
    birth: Birth
    location: dict[str, float]  # {"latitude": float, "longitude": float}
    bodies: Optional[list[str]] = None
    house_system: str = "P"


class TopCitiesRequest(BaseModel):
    birth: Birth
    focus: str = "all"  # love, career, wealth, peace, growth, all
    limit: int = 15
    # Per-domain goal weights from the UI sliders (0–10 each). When provided,
    # they blend with (and override) the focus preset's emphasis.
    weights: Optional[dict[str, float]] = None
    include_breakdown: bool = True
    # Dual-chart mode: when set, cities are ranked for the couple and the
    # partner's lines can be overlaid on the globe.
    second_birth: Optional[Birth] = None


class ReturnRequest(BaseModel):
    birth: Birth
    bodies: Optional[list[str]] = None
    lat_step: float = 1.0
    year: int = 2026          # year for solar return / optional for lunar return
    month: Optional[int] = None  # optional: lunar return in this calendar month


class TravelTimingRequest(BaseModel):
    birth: Birth
    dest_lat: float
    dest_lon: float
    start_date: str          # ISO date "YYYY-MM-DD" (UTC assumed)
    days: int = 30



class BirthEntry(BaseModel):
    name: str
    datetime: str
    latitude: float
    longitude: float
    note: Optional[str] = None


class BirthEntryUpdate(BaseModel):
    name: Optional[str] = None
    datetime: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    note: Optional[str] = None


@app.get("/")
def root() -> Any:
    # Serve the built SPA at the site root. Fall back to a JSON health/status
    # response when the frontend hasn't been built yet.
    index = _DIST / "index.html"
    if index.is_file():
        return FileResponse(index, headers={})
    return {
        "status": "online",
        "service": "Astrocartography API",
        "version": "0.1.0",
        "endpoints": {
            "astrocartography": "/api/astrocartography",
            "location-analysis": "/api/location-analysis",
            "top-cities": "/api/top-cities",
            "births": "/api/births",
            "docs": "/docs",
        },
    }


@app.post("/api/astrocartography")
def astrocartography(req: ACGRequest) -> dict[str, Any]:
    key = payload_key(
        "acg", req.birth.datetime, req.birth.latitude, req.birth.longitude,
        req.bodies, req.lat_step,
    )
    try:
        return cached(key, lambda: generate_acg(
            req.birth.datetime,
            req.birth.latitude,
            req.birth.longitude,
            bodies=req.bodies,
            lat_step=req.lat_step,
        ))
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc) or "Invalid birth data")
    except Exception as exc:  # surface calculation errors clearly
        raise HTTPException(status_code=500, detail=f"Calculation error: {exc}")


@app.post("/api/transit-acg")
def transit_acg(req: TransitACGRequest) -> dict[str, Any]:
    try:
        return generate_transit_acg(
            req.birth.datetime,
            req.birth.latitude,
            req.birth.longitude,
            req.transit_iso,
            bodies=req.bodies,
            lat_step=req.lat_step,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc) or "Invalid birth data")
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Calculation error: {exc}")


@app.post("/api/progressed-acg")
def progressed_acg(req: ProgressedACGRequest) -> dict[str, Any]:
    try:
        return generate_progressed_acg(
            req.birth.datetime,
            req.birth.latitude,
            req.birth.longitude,
            req.age_years,
            bodies=req.bodies,
            lat_step=req.lat_step,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc) or "Invalid birth data")
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Calculation error: {exc}")


@app.post("/api/geodetic")
def geodetic(req: GeodeticRequest) -> dict[str, Any]:
    try:
        return generate_geodetic(
            req.birth.datetime,
            req.birth.latitude,
            req.birth.longitude,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc) or "Invalid birth data")
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Calculation error: {exc}")


@app.post("/api/fixed-stars")
def fixed_stars(req: FixedStarsRequest) -> dict[str, Any]:
    try:
        return generate_fixed_star_lines(
            req.birth.datetime,
            req.birth.latitude,
            req.birth.longitude,
            names=req.names,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc) or "Invalid birth data")
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Calculation error: {exc}")


@app.post("/api/midpoints")
def midpoints(req: MidpointsRequest) -> dict[str, Any]:
    try:
        return generate_midpoint_lines(
            req.birth.datetime,
            req.birth.latitude,
            req.birth.longitude,
            pairs=req.pairs,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc) or "Invalid birth data")
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Midpoints calculation error: {exc}")


@app.post("/api/crossings")
def crossings(req: CrossingsRequest) -> dict[str, Any]:
    """Power places: natal line crossings + parans as clickable markers."""
    key = payload_key(
        "crossings", req.birth.datetime, req.birth.latitude, req.birth.longitude, req.bodies,
    )
    try:
        return cached(key, lambda: generate_crossings(
            req.birth.datetime,
            req.birth.latitude,
            req.birth.longitude,
            bodies=req.bodies,
        ))
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc) or "Invalid birth data")
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Crossings calculation error: {exc}")


@app.post("/api/solar-return")
def solar_return(req: ReturnRequest) -> dict[str, Any]:
    """Solar return ACG overlay for the given year."""
    key = payload_key(
        "solar-return", req.birth.datetime, req.birth.latitude, req.birth.longitude,
        req.year, req.bodies, req.lat_step,
    )
    try:
        return cached(key, lambda: generate_solar_return_acg(
            req.birth.datetime, req.birth.latitude, req.birth.longitude,
            year=req.year, bodies=req.bodies, lat_step=req.lat_step,
        ))
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc) or "Invalid birth data")
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Solar return error: {exc}")


@app.post("/api/lunar-return")
def lunar_return(req: ReturnRequest) -> dict[str, Any]:
    """Lunar return ACG overlay."""
    key = payload_key(
        "lunar-return", req.birth.datetime, req.birth.latitude, req.birth.longitude,
        req.year, req.month, req.bodies, req.lat_step,
    )
    try:
        return cached(key, lambda: generate_lunar_return_acg(
            req.birth.datetime, req.birth.latitude, req.birth.longitude,
            year=req.year, month=req.month, bodies=req.bodies, lat_step=req.lat_step,
        ))
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc) or "Invalid birth data")
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Lunar return error: {exc}")


@app.post("/api/travel-timing")
def travel_timing(req: TravelTimingRequest) -> list[dict[str, Any]]:
    """Score each day in a window for travel favourability to a destination."""
    key = payload_key(
        "travel-timing", req.birth.datetime, req.birth.latitude, req.birth.longitude,
        req.dest_lat, req.dest_lon, req.start_date, req.days,
    )
    try:
        return cached(key, lambda: rate_travel_window(
            req.birth.datetime, req.birth.latitude, req.birth.longitude,
            req.dest_lat, req.dest_lon, req.start_date, days=req.days,
        ))
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc) or "Invalid request")
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Travel timing error: {exc}")




@app.post("/api/location-analysis")
def location_analysis(req: LocationAnalysisRequest) -> dict[str, Any]:
    lat = req.location.get("latitude")
    lng = req.location.get("longitude")
    if lat is None or lng is None:
        raise HTTPException(status_code=400, detail="location.latitude/longitude required")
    try:
        return generate_analysis(
            req.birth.datetime,
            req.birth.latitude,
            req.birth.longitude,
            float(lat),
            float(lng),
            bodies=req.bodies,
            house_system=req.house_system,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc) or "Invalid analysis data")
    except Exception as exc:  # surface calculation errors clearly
        raise HTTPException(status_code=500, detail=f"Calculation error: {exc}")


@app.post("/api/top-cities")
def top_cities(req: TopCitiesRequest) -> list[dict[str, Any]]:
    key = payload_key(
        "top-cities", req.birth.datetime, req.birth.latitude, req.birth.longitude,
        req.focus, req.limit, req.weights, req.second_birth,
    )
    try:
        def _rank():
            if req.second_birth is not None:
                return rank_cities_for_couple(
                    req.birth.datetime, req.birth.latitude, req.birth.longitude,
                    req.second_birth.datetime, req.second_birth.latitude,
                    req.second_birth.longitude,
                    focus=req.focus, limit=req.limit, weights=req.weights,
                )
            return rank_cities_for_birth(
                req.birth.datetime,
                req.birth.latitude,
                req.birth.longitude,
                focus=req.focus,
                limit=req.limit,
                weights=req.weights,
                include_breakdown=req.include_breakdown,
            )
        return cached(key, _rank)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc) or "Invalid birth data")
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Top cities calculation error: {exc}")


# ---------------------------------------------------------------------------
# Saved birth entries
# ---------------------------------------------------------------------------

@app.get("/api/births")
def get_births() -> list[dict[str, Any]]:
    return list_entries()


@app.get("/api/births/{entry_id}")
def get_birth(entry_id: int) -> dict[str, Any]:
    entry = get_entry(entry_id)
    if entry is None:
        raise HTTPException(status_code=404, detail="Birth entry not found")
    return entry


@app.post("/api/births")
def add_birth(entry: BirthEntry) -> dict[str, Any]:
    try:
        return create_entry(
            entry.name,
            entry.datetime,
            entry.latitude,
            entry.longitude,
            note=entry.note,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@app.put("/api/births/{entry_id}")
def edit_birth(entry_id: int, entry: BirthEntryUpdate) -> dict[str, Any]:
    updated = update_entry(
        entry_id,
        name=entry.name,
        datetime=entry.datetime,
        latitude=entry.latitude,
        longitude=entry.longitude,
        note=entry.note,
    )
    if updated is None:
        raise HTTPException(status_code=404, detail="Birth entry not found")
    return updated


@app.delete("/api/births/{entry_id}")
def remove_birth(entry_id: int) -> dict[str, Any]:
    if not delete_entry(entry_id):
        raise HTTPException(status_code=404, detail="Birth entry not found")
    return {"deleted": entry_id}


# ---------------------------------------------------------------------------
# SPA fallback — must be registered LAST so it never shadows real API/static
# routes (route matching is order-dependent in FastAPI).
# ---------------------------------------------------------------------------


@app.get("/{full_path:path}")
def serve_frontend(full_path: str):
    # Let FastAPI's own routes (API, docs, openapi) handle their paths.
    if (
        full_path.startswith("api/")
        or full_path in ("docs", "redoc", "openapi.json")
        or full_path.startswith("docs/")
        or full_path.startswith("redoc/")
    ):
        raise HTTPException(status_code=404, detail="Not found")
    candidate = _DIST / full_path
    if candidate.is_file():
        headers = _cache_headers() if full_path.startswith("assets/") else {}
        return FileResponse(candidate, headers=headers)
    # SPA fallback — let client-side routing handle unknown paths.
    index = _DIST / "index.html"
    if index.is_file():
        return FileResponse(index, headers={})
    raise HTTPException(status_code=404, detail="Frontend not built")
