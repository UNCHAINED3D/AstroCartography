import json, urllib.request

def fetch(url):
    print("GET", url)
    with urllib.request.urlopen(url, timeout=120) as r:
        return json.load(r)

# Countries (110m) -> centroid via vertex average
cf = fetch("https://raw.githubusercontent.com/nvkelso/natural-earth-vector/master/geojson/ne_110m_admin_0_countries.geojson")
countries = []
for f in cf["features"]:
    p = f.get("properties", {})
    name = p.get("NAME") or p.get("ADMIN") or p.get("NAME_LONG")
    if not name:
        continue
    g = f["geometry"]
    if g is None:
        continue
    t = g["type"]; coords = g["coordinates"]
    pts = []
    if t == "Polygon":
        for ring in coords:
            pts += ring
    elif t == "MultiPolygon":
        for poly in coords:
            for ring in poly:
                pts += ring
    if not pts:
        continue
    sx = sum(c[0] for c in pts); sy = sum(c[1] for c in pts)
    countries.append({"name": name, "lat": round(sy/len(pts), 3), "lng": round(sx/len(pts), 3)})

# Cities (50m populated places) -> pop-filtered
pf = fetch("https://raw.githubusercontent.com/nvkelso/natural-earth-vector/master/geojson/ne_50m_populated_places.geojson")
cities = []
for f in pf["features"]:
    p = f.get("properties", {})
    name = p.get("NAME")
    pop = p.get("POP_MAX") or p.get("POP_MIN") or 0
    try:
        pop = float(pop)
    except Exception:
        pop = 0
    if not name or pop < 100000:
        continue
    g = f["geometry"]
    if g is None or g["type"] != "Point":
        continue
    lng, lat = g["coordinates"]
    cities.append({"name": name, "lat": round(lat, 3), "lng": round(lng, 3), "pop": int(pop)})

cities.sort(key=lambda c: c["pop"], reverse=True)
print("countries", len(countries), "cities", len(cities))
out = {"countries": countries, "cities": cities}
import os
with open(r"C:\Users\Evand\Desktop\UNCHAINED3D\ASTRO\astrocartography\frontend\public\labels.json", "w", encoding="utf-8") as fh:
    json.dump(out, fh, ensure_ascii=False)
print("written labels.json")
