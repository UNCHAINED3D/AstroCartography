"""Quick verification test for returns and electional endpoints."""

from fastapi.testclient import TestClient

from api.main import app

client = TestClient(app)

# Test travel timing
resp = client.post('/api/travel-timing', json={
    'birth': {'datetime': '1990-06-15T12:00:00+00:00', 'latitude': 40.7, 'longitude': -74.0},
    'dest_lat': 52.5, 'dest_lon': 13.4,
    'start_date': '2026-09-06', 'days': 7,
})
assert resp.status_code == 200, f'Travel timing failed: {resp.status_code} {resp.text}'
data = resp.json()
print(f'Travel timing: {len(data)} days scored')
for d in data:
    print(f"  {d['date']}: {d['score']} - {d['influences'][:2]}")
assert len(data) == 7

# Test solar return
resp = client.post('/api/solar-return', json={
    'birth': {'datetime': '1990-06-15T12:00:00+00:00', 'latitude': 40.7, 'longitude': -74.0},
    'year': 2026,
})
assert resp.status_code == 200, f'Solar return failed: {resp.status_code} {resp.text}'
data = resp.json()
print(f'Solar return: {data["return_moment_iso"]}, {len(data["lines"])} lines')
assert data['return_type'] == 'solar'
assert 'lines' in data
assert 'return_moment_iso' in data

# Test lunar return
resp = client.post('/api/lunar-return', json={
    'birth': {'datetime': '1990-06-15T12:00:00+00:00', 'latitude': 40.7, 'longitude': -74.0},
    'year': 2026, 'month': 9,
})
assert resp.status_code == 200, f'Lunar return failed: {resp.status_code} {resp.text}'
data = resp.json()
print(f'Lunar return: {data["return_moment_iso"]}, {len(data["lines"])} lines')
assert data['return_type'] == 'lunar'

print('\nAll returns/electional tests passed.')
