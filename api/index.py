"""
Vercel Python serverless handler for the Astrocartography FastAPI app.

Downloads the JPL de440 planetary kernel to /tmp before importing the backend
(moira_engine validates the kernel path at import time), then adapts each
Vercel HTTP request into an ASGI call against the FastAPI application.
"""

from __future__ import annotations

import asyncio
import json
import os
import sys
import urllib.request
from pathlib import Path

# ---------------------------------------------------------------------------
# 1. Ensure the de440 kernel is available before backend modules are imported.
#    moira_engine raises FileNotFoundError at import time if the kernel is
#    missing, so we fetch it to /tmp on cold start and point MOIRA_KERNEL_PATH
#    at it.
# ---------------------------------------------------------------------------
_KERNEL_URL = "https://naif.jpl.nasa.gov/pub/naif/generic_kernels/spk/planets/de440.bsp"
_KERNEL_PATH = Path("/tmp/de440.bsp")

if not _KERNEL_PATH.exists():
    try:
        _KERNEL_PATH.parent.mkdir(parents=True, exist_ok=True)
        urllib.request.urlretrieve(_KERNEL_URL, str(_KERNEL_PATH))
    except Exception as exc:  # noqa: BLE001
        print(f"[vercel] kernel download failed: {exc}", file=sys.stderr)

os.environ.setdefault("MOIRA_KERNEL_PATH", str(_KERNEL_PATH))

# ---------------------------------------------------------------------------
# 2. Import the FastAPI application (project root must be on sys.path).
# ---------------------------------------------------------------------------
_ROOT = Path(__file__).resolve().parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from backend.api.main import app as fastapi_app  # noqa: E402


def _build_scope(event: dict) -> dict:
    """Convert a Vercel request event into an ASGI scope dict."""
    headers_raw = event.get("headers") or {}
    if isinstance(headers_raw, list):
        header_pairs = [(str(k).lower().encode(), str(v).encode()) for k, v in headers_raw]
    else:
        header_pairs = [(str(k).lower().encode(), str(v).encode()) for k, v in headers_raw.items()]

    method = str(event.get("method", "GET")).upper()
    path = str(event.get("path", "/"))
    query = event.get("query", "")
    query_string = query.encode() if isinstance(query, str) else (query or b"")

    return {
        "type": "http",
        "asgi": {"version": "3.0", "spec_version": "2.0"},
        "http_version": "1.1",
        "method": method,
        "scheme": "https",
        "path": path,
        "raw_path": path.encode(),
        "query_string": query_string,
        "headers": header_pairs,
        "client": ["127.0.0.1", 0],
        "server": ["vercel", 443],
    }


async def _run_asgi(scope: dict, event: dict) -> dict:
    """Drive the FastAPI app through one ASGI request/response cycle."""
    body = event.get("body", "")
    if isinstance(body, str):
        body = body.encode()
    elif body is None:
        body = b""

    sent_body = False

    async def receive():
        nonlocal sent_body
        if not sent_body:
            sent_body = True
            return {"type": "http.request", "body": body, "more_body": False}
        return {"type": "http.request", "body": b"", "more_body": False}

    status_code = 200
    response_headers: list[tuple[str, str]] = []
    response_body = bytearray()

    async def send(message):
        nonlocal status_code, response_headers, response_body
        if message["type"] == "http.response.start":
            status_code = int(message.get("status", 200))
            response_headers = [
                (k.decode(), v.decode()) for k, v in message.get("headers", [])
            ]
        elif message["type"] == "http.response.body":
            chunk = message.get("body", b"")
            if chunk:
                response_body.extend(chunk)

    await fastapi_app(scope, receive, send)

    return {
        "statusCode": status_code,
        "headers": dict(response_headers),
        "body": response_body.decode("utf-8", errors="replace"),
        "isBase64Encoded": False,
    }


def handler(event, context=None):
    """Vercel serverless function entry point."""
    try:
        scope = _build_scope(event)
        result = asyncio.run(_run_asgi(scope, event))
    except Exception as exc:  # noqa: BLE001
        return {
            "statusCode": 500,
            "headers": {"Content-Type": "application/json"},
            "body": json.dumps({"detail": f"Internal server error: {exc}"}),
        }
    return result
