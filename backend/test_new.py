"""Quick smoke test for the new endpoints."""
from fastapi.testclient import TestClient
from api.main import app

client = TestClient(app)

# Test travel timing
resp = client.post('/api/travel-timing', json={
    'birth': {'datetime': '1990-06-15T12:00:00+00:00', 'latitude': 40.7, 'longitude': -74.0},
    'dest_lat': 52.5, 'dest_lon': 13.4,
    'start_date': '2026-09-06', 'days': 7
})
print('Travel timing:', resp.status_code, '-', len(resp.json()), 'days')
for d in resp.json():
    print(f'  {d["date"]}: {d["score"]} - {d["influences"][:2]}')

# Test solar return
resp = client.post('/api/solar-return', json={
    'birth': {'datetime': '1990-06-15T12:00:00+00:00', 'latitude': 40.7, 'longitude': -74.0},
    'year': 2026
})
print('Solar return:', resp.status_code)
data = resp.json()
print('  Lines:', len(data.get('lines', [])))
print('  Moment:', data.get('return_moment_iso'))

# Test lunar return
resp = client.post('/api/lunar-return', json={
    'birth': {'datetime': '1990-06-15T12:00:00+00:00', 'latitude': 40.7, 'longitude': -74.0},
    'year': 2026, 'month': 9
})
print('Lunar return:', resp.status_code)
data = resp.json()
print('  Lines:', len(data.get('lines', [])))
print('  Moment:', data.get('return_moment_iso'))

# Test crossings
resp = client.post('/api/crossings', json={
    'birth': {'datetime': '1990-06-15T12:00:00+00:00', 'latitude': 40.7, 'longitude': -74.0}
})
print('Crossings:', resp.status_code)
data = resp.json()
print('  Crossings:', len(data.get('crossings', [])))
