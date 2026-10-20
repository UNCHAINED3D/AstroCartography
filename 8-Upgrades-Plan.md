Astrocartographer Helper — 8 Upgrades: Implementation Plan
Overview
All 8 upgrades are self-contained and layer on top of the existing working stack without breaking it. The backend is Python (FastAPI + Moira), the frontend is TypeScript (Vite + globe.gl + Three.js + Leaflet).

Upgrade 1 — Full Interpretation Library (48 planet × angle combos)
Only file changed: 
interpretations.py

Replace the 1-sentence line_sentence() template with a full ACG_MEANINGS dictionary keyed by (planet, angle) — 48 entries covering all 12 planets × 4 angles, each 3–5 sentences. The existing line_sentence() function falls back to the dict, so no API changes required. Paran pair interpretation dict also added (~30 most common pairs).

Upgrade 2 — Orb Zone Shading on Globe Lines
Files changed:

globe.ts
 — add orb band paths (wide, very low alpha) per ACG line using pushLine
map2d.ts
 — add wide semi-transparent Leaflet polylines for orb zones
main.ts
 — add orb zone toggle checkbox to layer controls
Approach: For each ACG line, draw two additional paths on the globe at the same coordinates but with much wider stroke and ~8% alpha:

Strong zone: ±120 km → drawn as wider glow
The existing glow path is widened from stroke: 3.2 to stroke: 28 at alpha: 0.07 for the strong band; a second wider one at stroke: 68 at alpha: 0.04 for moderate (400 km)
No backend changes needed — orb bands are purely visual overlays in the renderer.

Upgrade 3 — Planet/Angle Layer Toggle UI (already partial, completing it)
The globe already has setPlanetVisible() and setAngleVisible() — the toggles in buildLegend() in main.ts already wire to them. What's missing is:

Angle symbol labels (MC ♑ / IC / ASC ↑ / DSC) with individual checkboxes visible in the sidebar
"Show All / Hide All" quick buttons per group
Goal presets already filter planets — just needs a cleaner UI grouping
Files changed:

main.ts
 — enhance buildLegend() to add Select All/None buttons
style.css
 — style the toggle groups
Upgrade 4 — Paran Latitude Bands
Currently parans are dots on the globe. Real paran theory says two planets are in paran when they simultaneously hold an angular relationship at the same latitude — so the meaningful display is a horizontal band across the entire globe at the paran's latitude.

Files changed:

globe.ts
 — add buildParanBands() that renders each paran as a horizontal line from -180° to +180° longitude at p.latitude, at low alpha
map2d.ts
 — same as horizontal Leaflet polylines
types.ts
 — no changes (Paran already has latitude)
The paran dots remain as clickable markers; bands are the new layer beneath them.

Upgrade 5 — Transit ACG Lines Overlay
Adds a second ACG calculation for today's date (or a user-chosen date) at the same birth location. Transit lines rendered in desaturated/dashed style overlaid on natal lines.

Backend new file: 
astrocartography/backend/timing.py

python

generate_transit_acg(birth_iso, birth_lat, birth_lon, transit_iso, bodies, lat_step)
Uses the same generate_acg() but with transit_iso as the datetime — since Moira's acg_from_chart() just needs a JD, this is trivially a second call.

Backend API: 
api/main.py
 — new endpoint POST /api/transit-acg

Frontend:

types.ts
 — add TransitRequest, TransitResponse
api.ts
 — add fetchTransitACG()
globe.ts
 — add setTransitData(), render transit lines in dashed style at 60% alpha
map2d.ts
 — add transit lines as dashed Leaflet polylines
main.ts
 — add transit date input + "Load Transits" button to the form section
style.css
 — transit controls styling
Upgrade 6 — Progressed ACG Lines
Secondary progressed chart ACG lines. Uses secondary progressions (1 day = 1 year after birth). Moira has progressions.py. The progressed chart's ACG lines shift slowly over the years — showing where the "evolved" chart lines sit.

Backend new file: 
astrocartography/backend/timing.py
 (same file as transit, adds generate_progressed_acg())

python

# Secondary progression: 1 day after birth = 1 year of life
# For age N: progressed JD = birth_jd + N
generate_progressed_acg(birth_iso, birth_lat, birth_lon, age_years, bodies, lat_step)
Backend API: New endpoint POST /api/progressed-acg

Frontend:

globe.ts
 — add setProgressedData(), render in dotted/thinner style at 50% alpha with distinct colours (lightened versions of planet colours)
main.ts
 — add "Show Progressed Lines" toggle + age/year selector
Upgrade 7 — Domain Score Card (Career/Love/Home ★★★★☆)
Backend file changed: 
analysis.py

Add _domain_scores() function that takes nearest_acg + near_parans + planet_houses and scores 5 domains (Love, Career, Home, Growth, Peace) on a 0–5 scale based on:

Which planets are nearby and their distance (strength)
Which house the relocated planets occupy
Whether parans are present
Returns a scores dict added to the existing generate_analysis() response — no API signature change, just an addtional key.

Frontend:

types.ts
 — add DomainScores to LocationAnalysis
panel.ts
 — add renderScoreCard() that shows star ratings at the top of the report
style.css
 — star rating styles
Upgrade 8 — Geodetic Chart, Fixed Star Lines, Midpoint Lines
Three distinct sub-features added as optional ACG overlay layers, all using Moira modules.

8A. Geodetic Lines
Moira has geodetic.py. Geodetic ACG maps the 360° zodiac directly onto Earth's 360° of longitude (0° Aries = 0° longitude). Each sign boundary and planet's geodetic position becomes a meridian line.

Backend addition in acg.py: generate_geodetic(iso_datetime, birth_lat, birth_lon) — uses moira.geodetic

New API endpoint: POST /api/geodetic

8B. Fixed Star ACG Lines
Moira has stars.py with a star catalog and paran_stars.py. For each bright fixed star, compute its MC/IC line (its right ascension gives a meridian). Top ~20 classical fixed stars (Spica, Regulus, Aldebaran, Algol, etc.).

Backend addition in acg.py: generate_fixed_star_lines(iso_datetime, birth_lat, birth_lon) — calls moira.stars + ACG math for each star's RA/Dec

New API endpoint: POST /api/fixed-stars

8C. Midpoint ACG Lines
Moira has midpoints.py. For key midpoint pairs (e.g. Venus/Jupiter, Sun/Moon, Mars/Saturn), compute the composite RA/Dec midpoint and generate its ACG lines.

Backend addition in acg.py: generate_midpoint_lines(iso_datetime, birth_lat, birth_lon, pairs) — calls moira.midpoints for each pair

New API endpoint: POST /api/midpoints

Frontend (all three):

api.ts
 — add fetchGeodetic(), fetchFixedStars(), fetchMidpoints()
globe.ts
 — add setGeodeticData(), setFixedStarData(), setMidpointData() — each rendered in distinct visual styles
main.ts
 — add advanced overlay toggles: [Geodetic] [Fixed Stars] [Midpoints] buttons that lazy-load when toggled on
Files Modified/Created Summary
File	Action	Upgrades
backend/interpretations.py	Modify	1
backend/analysis.py	Modify	7
backend/acg.py	Modify	8A, 8B, 8C
backend/timing.py	NEW	5, 6
backend/api/main.py	Modify	5, 6, 8A, 8B, 8C
frontend/src/types.ts	Modify	5, 6, 7
frontend/src/api.ts	Modify	5, 6, 8A, 8B, 8C
frontend/src/globe.ts	Modify	2, 4, 5, 6, 8A, 8B, 8C
frontend/src/map2d.ts	Modify	2, 4
frontend/src/panel.ts	Modify	7
frontend/src/main.ts	Modify	3, 5, 6, 8A, 8B, 8C
frontend/src/style.css	Modify	2, 3, 5, 7
Verification Plan
After all changes:

Run backend from astrocartography/backend: python run.py — verify no import errors
Rebuild frontend from astrocartography/frontend: npm run build — verify no TypeScript errors
Test U1 (interpretations): Click a location → panel should show multi-sentence ACG descriptions
Test U2 (orbs): Toggle orb zones → shaded bands appear around lines
Test U4 (paran bands): Enable parans → horizontal lines appear at paran latitudes
Test U5 (transits): Enter a transit date, click Load Transits → secondary dashed lines appear
Test U6 (progressed): Toggle progressed → dotted lines appear in lighter colours
Test U7 (score card): Click a location → 5-domain star rating appears at panel top
Test U8: Toggle Geodetic/Fixed Stars/Midpoints → additional overlay lines appear
IMPORTANT

Moira's geodetic.py, midpoints.py, and stars.py APIs need to be verified against the actual cloned source before wiring — if any don't expose the expected functions, the backend will gracefully return empty lists rather than erroring.