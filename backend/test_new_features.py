"""Smoke test for the new backend features (crossings, returns, travel-timing)."""
import os
import sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from api.main import app
from fastapi.testclient import TestClient

client = TestClient(app)

birth = {'datetime': '1990-06-15T12:00:00+00:00', 'latitude': 40.7, 'longitude': -74.0}

# 1. Crossings
resp = client.post('/api/crossings', json={'birth': birth})
print('Crossings:', resp.status_code)
if resp.status_code == 200:
    data = resp.json()
    print(f'  Markers: {len(data.get("crossings", []))}')

# 2. Solar return
resp = client.post('/api/solar-return', json={'birth': birth, 'year': 2026})
print('Solar return:', resp.status_code)
if resp.status_code == 200:
    data = resp.json()
    print(f'  Lines: {len(data.get("lines", []))}, moment: {data.get("return_moment_iso")}')

# 3. Lunar return
resp = client.post('/api/lunar-return', json={'birth': birth, 'year': 2026, 'month': 9})
print('Lunar return:', resp.status_code)
if resp.status_code == 200:
    data = resp.json()
    print(f'  Lines: {len(data.get("lines", []))}, moment: {data.get("return_moment_iso")}')

# 4. Travel timing
resp = client.post('/api/travel-timing', json={
    'birth': birth, 'dest_lat': 52.5, 'dest_lon': 13.4,
    'start_date': '2026-09-06', 'days': 7,
})
print('Travel timing:', resp.status_code)
if resp.status_code == 200:
    data = resp.json()
    print(f'  Days: {len(data)}, first: {data[0]}')
