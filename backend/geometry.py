"""
Geometry helpers for the globe.

Moira returns ACG points as ``(latitude, longitude)`` tuples. The globe and
GeoJSON expect ``[longitude, latitude]``. These helpers keep conversion and
seam-handling in one place.
"""

from __future__ import annotations

import math
from typing import Sequence

# Web Mercator / globe seam threshold. A jump larger than this between adjacent
# longitudes means the line crossed the antimeridian and must be split.
_ANTIMERIDIAN_JUMP = 180.0


def _normalize_lon(lon: float) -> float:
    """Wrap a longitude into the [-180, 180] range the globe expects."""
    return ((lon + 180.0) % 360.0) - 180.0


def to_geojson_points(points: Sequence[tuple[float, float]]) -> list[list[float]]:
    """Convert Moira ``(lat, lon)`` tuples to GeoJSON ``[lon, lat]`` pairs.

    Longitudes are normalized into [-180, 180] so the globe renders correctly.
    """
    return [[round(_normalize_lon(lon), 6), round(lat, 6)] for lat, lon in points]


def longitude_line(longitude: float, lat_step: float = 1.0) -> list[list[float]]:
    """Build a constant-longitude meridian (MC/IC line) from pole to pole."""
    lon = round(_normalize_lon(longitude), 6)
    coords: list[list[float]] = []
    lat = -90.0
    while lat <= 90.0 + 1e-9:
        coords.append([lon, round(lat, 6)])
        lat += lat_step
    return coords


def split_antimeridian(points: Sequence[tuple[float, float]]) -> list[list[list[float]]]:
    """Split a polyline at the ±180° seam into continuous segments.

    ``points`` are ``(lat, lon)`` tuples (Moira order). Returns a list of
    GeoJSON-style segments (each a list of ``[lon, lat]`` pairs), with
    longitudes normalized into [-180, 180].
    """
    if not points:
        return []

    segments: list[list[list[float]]] = []
    first = to_geojson_points([points[0]])[0]
    current: list[list[float]] = [first]
    prev_lon = first[0]

    for i in range(1, len(points)):
        lon = _normalize_lon(points[i][1])
        lat = points[i][0]
        if abs(lon - prev_lon) > _ANTIMERIDIAN_JUMP:
            segments.append(current)
            current = [[round(lon, 6), round(lat, 6)]]
        else:
            current.append([round(lon, 6), round(lat, 6)])
        prev_lon = lon

    segments.append(current)
    return [s for s in segments if len(s) >= 1]


def haversine_km(
    lat1: float, lon1: float, lat2: float, lon2: float
) -> float:
    """Great-circle distance in kilometres between two lat/lon points."""
    r = 6371.0088
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlam = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dlam / 2) ** 2
    return 2 * r * math.asin(min(1.0, math.sqrt(a)))


def destination_point(
    lat: float, lon: float, bearing_deg: float, distance_deg: float
) -> tuple[float, float]:
    """Great-circle destination point given a start, bearing and angular distance.

    Bearing follows the compass convention: ``0° = North``, ``90° = East``.
    Returns ``(latitude, longitude)`` with longitude normalised to [-180, 180].
    """
    lat1 = math.radians(lat)
    lon1 = math.radians(lon)
    brng = math.radians(bearing_deg)
    d = math.radians(distance_deg)
    lat2 = math.asin(
        math.sin(lat1) * math.cos(d) + math.cos(lat1) * math.sin(d) * math.cos(brng)
    )
    lon2 = lon1 + math.atan2(
        math.sin(brng) * math.sin(d) * math.cos(lat1),
        math.cos(d) - math.sin(lat1) * math.sin(lat2),
    )
    return round(math.degrees(lat2), 6), round(_normalize_lon(math.degrees(lon2)), 6)


def _seg_intersection(
    p1: tuple[float, float],
    p2: tuple[float, float],
    p3: tuple[float, float],
    p4: tuple[float, float],
) -> tuple[float, float] | None:
    """2D segment-segment intersection in (lon, lat) space, or None."""
    x1, y1 = p1
    x2, y2 = p2
    x3, y3 = p3
    x4, y4 = p4
    denom = (x1 - x2) * (y3 - y4) - (y1 - y2) * (x3 - x4)
    if denom == 0:
        return None
    t = ((x1 - x3) * (y3 - y4) - (y1 - y3) * (x3 - x4)) / denom
    u = ((x1 - x3) * (y1 - y2) - (y1 - y3) * (x1 - x2)) / denom
    if 0 <= t <= 1 and 0 <= u <= 1:
        return (x1 + t * (x2 - x1), y1 + t * (y2 - y1))
    return None


def bearing_deg(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Initial compass bearing (degrees, 0=N, 90=E) from point 1 to point 2."""
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dlon = math.radians(lon2 - lon1)
    x = math.sin(dlon) * math.cos(p2)
    y = math.cos(p1) * math.sin(p2) - math.sin(p1) * math.cos(p2) * math.cos(dlon)
    return (math.degrees(math.atan2(x, y)) + 360.0) % 360.0


def _point_to_segment(
    plat: float, plon: float, a: list[float], b: list[float]
) -> float:
    """Great-circle distance (km) from a point to a single geodesic segment."""
    # Project the point onto the segment in a local equirectangular frame centred
    # on point a, then fall back to the nearer endpoint.
    alat, alon = a[1], a[0]
    blat, blon = b[1], b[0]
    dlon = math.radians(plon - alon)
    dlat = math.radians(plat - alat)
    # Bearing of the segment from a.
    seg_bearing = math.radians(bearing_deg(alat, alon, blat, blon))
    seg_dist = haversine_km(alat, alon, blat, blon)
    # Distance along the segment (clamped to [0, seg_dist]).
    along = (dlat * math.cos(seg_bearing) + dlon * math.sin(seg_bearing)) * 111.0
    along = max(0.0, min(seg_dist, along))
    perp = haversine_km(alat, alon, plat, plon) ** 2 - along**2
    perp = 0.0 if perp < 0 else math.sqrt(perp)
    return perp


def distance_to_line(
    lat: float, lon: float, coords: Sequence[list[float]]
) -> float:
    """Minimum great-circle distance (km) from a point to a polyline.

    ``coords`` is a GeoJSON-style ``[lon, lat]`` polyline (the globe/ACG order).
    """
    if not coords:
        return float("inf")
    best = haversine_km(lat, lon, coords[0][1], coords[0][0])
    for i in range(len(coords) - 1):
        d = _point_to_segment(lat, lon, coords[i], coords[i + 1])
        if d < best:
            best = d
    return best


# Local-space house mapping: 12 thirty-degree azimuth sectors (clockwise from
# North) onto the natal houses. North = IC (4th cusp), East = ASC (1st cusp),
# South = MC (10th cusp), West = DSC (7th cusp). Approximate equal-house
# local-space layout — fine for a "which house region is this?" readout.
_HOUSE_SECTORS = [4, 3, 2, 1, 12, 11, 10, 9, 8, 7, 6, 5]


def point_to_house_sector(bearing: float) -> int:
    """Map a compass bearing (0=N, 90=E) to a natal house 1–12 (approximate)."""
    sector = int(((bearing % 360.0) // 30.0)) % 12
    return _HOUSE_SECTORS[sector]


def intersect_lines(
    coords_a: Sequence[list[float]], coords_b: Sequence[list[float]]
) -> list[float] | None:
    """Approximate geographic intersection of two ACG polylines.

    Both inputs are GeoJSON-style ``[lon, lat]`` polylines. Segments that jump
    across the antimeridian are skipped. Returns ``[lon, lat]`` or ``None``.
    """
    for i in range(len(coords_a) - 1):
        a1, a2 = coords_a[i], coords_a[i + 1]
        if abs(a1[0] - a2[0]) > 180:
            continue
        for j in range(len(coords_b) - 1):
            b1, b2 = coords_b[j], coords_b[j + 1]
            if abs(b1[0] - b2[0]) > 180:
                continue
            pt = _seg_intersection(a1, a2, b1, b2)
            if pt:
                return [round(pt[0], 6), round(pt[1], 6)]
    return None
