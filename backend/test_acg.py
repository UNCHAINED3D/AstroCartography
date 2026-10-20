"""
Validation: compute ACG (with local space + parans + node lines) for the
Brisbane example and sanity-check the output.

Run from the backend/ directory:

    python test_acg.py
"""
from acg import generate_acg

ISO = "1990-05-15T14:30:00+10:00"  # Brisbane, UTC+10
LAT, LON = -27.4705, 153.0260

result = generate_acg(ISO, LAT, LON, lat_step=1.0)

lines = result["lines"]
subs = result["subplanetary_points"]
local = result["local_space"]
parans = result["parans"]

print(f"Total line features : {len(lines)}")
print(f"Subplanetary points : {len(subs)}")
print(f"Local space rays    : {len(local)}")
print(f"Parans              : {len(parans)}")

planets = sorted({l["planet"] for l in lines})
print("Planets with lines  :", planets)
print("Node line present   :", any(l["planet"] == "True Node" for l in lines))
print("Chiron line present :", any(l["planet"] == "Chiron" for l in lines))

errors = []

# Line coordinate sanity
for ln in lines:
    for lon, lat in ln["geometry"]["coordinates"]:
        if not (-180.0 <= lon <= 180.0):
            errors.append(f"{ln['id']} longitude out of range: {lon}")
        if not (-90.0 <= lat <= 90.0):
            errors.append(f"{ln['id']} latitude out of range: {lat}")
for ln in lines:
    cs = ln["geometry"]["coordinates"]
    for i in range(1, len(cs)):
        if abs(cs[i][0] - cs[i - 1][0]) > 180:
            errors.append(f"{ln['id']} un-split antimeridian jump at index {i}")
            break

# Local space rays: birth endpoint + a destination, valid coords
for r in local:
    coords = r["geometry"]["coordinates"]
    if len(coords) != 2:
        errors.append(f"local space {r['planet']} should have 2 points")
    for lon, lat in coords:
        if not (-180.0 <= lon <= 180.0 and -90.0 <= lat <= 90.0):
            errors.append(f"local space {r['planet']} coord out of range: {lon},{lat}")

# Parans: finite point
for p in parans:
    if not (-180.0 <= p["longitude"] <= 180.0 and -90.0 <= p["latitude"] <= 90.0):
        errors.append(f"paran {p['planet_a']}/{p['planet_b']} point out of range")

if errors:
    print("\nVALIDATION FAILED:")
    for e in errors[:40]:
        print("  -", e)
    raise SystemExit(1)

print("\nVALIDATION OK")
