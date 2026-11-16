use crate::astro::*;
use crate::models::*;
use axum::extract::State;
use axum::http::StatusCode;
use axum::response::IntoResponse;
use axum::Json;
use serde_json::Value;
use std::sync::Arc;
use swisseph::Ephemeris;

pub struct AppState {
    pub eph: Ephemeris,
}

pub type SharedState = Arc<AppState>;

fn bodies_or_default(b: &Option<Vec<String>>) -> Vec<String> {
    b.clone().unwrap_or_default()
}

pub async fn healthz() -> Json<Value> {
    Json(serde_json::json!({"status": "ok"}))
}

pub async fn astrocartography(
    State(state): State<SharedState>,
    Json(req): Json<ACGRequest>,
) -> impl IntoResponse {
    let bodies = bodies_or_default(&req.bodies);
    match generate_acg(
        &state.eph,
        &req.birth.datetime,
        req.birth.latitude,
        req.birth.longitude,
        &bodies,
        req.lat_step,
    ) {
        Ok(v) => (StatusCode::OK, Json(v)).into_response(),
        Err(e) => (
            StatusCode::BAD_REQUEST,
            Json(serde_json::json!({"detail": e})),
        )
            .into_response(),
    }
}

pub async fn transit_acg(
    State(state): State<SharedState>,
    Json(req): Json<TransitACGRequest>,
) -> impl IntoResponse {
    let bodies = bodies_or_default(&req.bodies);
    let jd_ut = match jd_from_iso(&req.transit_iso) {
        Ok(j) => j,
        Err(e) => {
            return (
                StatusCode::BAD_REQUEST,
                Json(serde_json::json!({"detail": e})),
            )
                .into_response()
        }
    };
    // generate lines for transit moment
    let calc_bodies: Vec<String> = if bodies.is_empty() {
        BODIES.iter().map(|s| s.to_string()).collect()
    } else {
        let mut v = bodies.clone();
        if !v.iter().any(|b| b == "Chiron") {
            v.push("Chiron".to_string());
        }
        v
    };
    let chart = create_chart(&state.eph, jd_ut, req.birth.latitude, req.birth.longitude, &calc_bodies);
    let lines = acg_from_chart(&chart, &calc_bodies, req.lat_step);
    let lines_out: Vec<Value> = lines
        .iter()
        .map(|l| {
            if l.line_type == "MC" || l.line_type == "IC" {
                let lonv = l.longitude.unwrap_or(0.0);
                serde_json::json!({
                    "id": format!("{}-{}", l.planet.to_lowercase().replace(' ', "-"), l.line_type.to_lowercase()),
                    "planet": l.planet,
                    "angle": l.line_type,
                    "color": planet_color(&l.planet),
                    "geometry": {"type": "LineString", "coordinates": norm_lon_line(lonv, req.lat_step)},
                })
            } else {
                let pts = l.points.clone().unwrap_or_default();
                let segments = split_antimeridian(&pts);
                // emit first segment only for simplicity; frontend expects array of lines
                serde_json::json!({
                    "id": format!("{}-{}", l.planet.to_lowercase().replace(' ', "-"), l.line_type.to_lowercase()),
                    "planet": l.planet,
                    "angle": l.line_type,
                    "color": planet_color(&l.planet),
                    "geometry": {"type": "LineString", "coordinates": segments.into_iter().next().unwrap_or_default()},
                })
            }
        })
        .collect();
    (
        StatusCode::OK,
        Json(serde_json::json!({"lines": lines_out})),
    )
        .into_response()
}

pub async fn progressed_acg(
    State(state): State<SharedState>,
    Json(req): Json<ProgressedACGRequest>,
) -> impl IntoResponse {
    let bodies = bodies_or_default(&req.bodies);
    let birth_jd = match jd_from_iso(&req.birth.datetime) {
        Ok(j) => j,
        Err(e) => {
            return (
                StatusCode::BAD_REQUEST,
                Json(serde_json::json!({"detail": e})),
            )
                .into_response()
        }
    };
    let prog_jd = birth_jd + req.age_years;
    let calc_bodies: Vec<String> = if bodies.is_empty() {
        BODIES.iter().map(|s| s.to_string()).collect()
    } else {
        let mut v = bodies.clone();
        if !v.iter().any(|b| b == "Chiron") {
            v.push("Chiron".to_string());
        }
        v
    };
    // sky positions at progressed jd
    let mut ra_dec = std::collections::BTreeMap::new();
    for b in &calc_bodies {
        if let Some(pd) = calc_body(&state.eph, b, prog_jd) {
            ra_dec.insert(b.clone(), (pd.right_ascension, pd.declination));
        }
    }
    let gmst = gmst_deg(prog_jd);
    let lines = acg_lines(&ra_dec, gmst, req.lat_step);
    let lines_out: Vec<Value> = lines
        .iter()
        .map(|l| {
            if l.line_type == "MC" || l.line_type == "IC" {
                let lonv = l.longitude.unwrap_or(0.0);
                serde_json::json!({
                    "id": format!("{}-{}", l.planet.to_lowercase().replace(' ', "-"), l.line_type.to_lowercase()),
                    "planet": l.planet,
                    "angle": l.line_type,
                    "color": planet_color(&l.planet),
                    "geometry": {"type": "LineString", "coordinates": norm_lon_line(lonv, req.lat_step)},
                })
            } else {
                let pts = l.points.clone().unwrap_or_default();
                let segments = split_antimeridian(&pts);
                serde_json::json!({
                    "id": format!("{}-{}", l.planet.to_lowercase().replace(' ', "-"), l.line_type.to_lowercase()),
                    "planet": l.planet,
                    "angle": l.line_type,
                    "color": planet_color(&l.planet),
                    "geometry": {"type": "LineString", "coordinates": segments.into_iter().next().unwrap_or_default()},
                })
            }
        })
        .collect();
    (
        StatusCode::OK,
        Json(serde_json::json!({"lines": lines_out})),
    )
        .into_response()
}

pub async fn geodetic(
    State(state): State<SharedState>,
    Json(req): Json<GeodeticRequest>,
) -> impl IntoResponse {
    match generate_geodetic(&state.eph, &req.birth.datetime, req.birth.latitude, req.birth.longitude) {
        Ok(v) => (StatusCode::OK, Json(v)).into_response(),
        Err(e) => (
            StatusCode::BAD_REQUEST,
            Json(serde_json::json!({"detail": e})),
        )
            .into_response(),
    }
}

pub async fn fixed_stars(
    State(state): State<SharedState>,
    Json(req): Json<FixedStarsRequest>,
) -> impl IntoResponse {
    let names = req.names.clone().unwrap_or_else(|| {
        vec![
            "Sirius", "Canopus", "Arcturus", "Vega", "Capella", "Rigel", "Procyon", "Betelgeuse",
            "Altair", "Aldebaran", "Spica", "Antares", "Pollux", "Fomalhaut", "Deneb", "Regulus",
            "Algol", "Alnilam", "Bellatrix", "Castor",
        ]
        .into_iter()
        .map(String::from)
        .collect()
    });
    let jd_ut = match jd_from_iso(&req.birth.datetime) {
        Ok(j) => j,
        Err(e) => {
            return (
                StatusCode::BAD_REQUEST,
                Json(serde_json::json!({"detail": e})),
            )
                .into_response()
        }
    };
    let jd_tt = jd_ut + 69.184 / 86400.0;
    let gmst = gmst_deg(jd_ut);
    let star_coords: std::collections::BTreeMap<&str, (f64, f64)> = [
        ("Sirius", (101.287, -16.716)),
        ("Canopus", (95.371, -52.697)),
        ("Arcturus", (213.915, 19.182)),
        ("Vega", (279.234, 38.784)),
        ("Capella", (79.171, 45.998)),
        ("Rigel", (78.534, -8.211)),
        ("Procyon", (114.825, 5.225)),
        ("Betelgeuse", (88.793, 7.407)),
        ("Altair", (297.686, 8.856)),
        ("Aldebaran", (68.676, 16.317)),
        ("Spica", (201.298, -11.161)),
        ("Antares", (247.342, -26.432)),
        ("Pollux", (116.329, 27.973)),
        ("Fomalhaut", (344.414, -29.622)),
        ("Deneb", (313.221, 45.293)),
        ("Regulus", (149.711, 11.967)),
        ("Algol", (70.634, 20.869)),
        ("Alnilam", (85.284, -1.184)),
        ("Bellatrix", (81.291, 6.351)),
        ("Castor", (113.651, 31.888)),
    ]
    .into_iter()
    .collect();
    let mut ra_dec = std::collections::BTreeMap::new();
    for name in &names {
        if let Some(&(lon, lat)) = star_coords.get(name.as_str()) {
            let (ra, dec) = ecliptic_to_equatorial(lon, lat, true_obliquity(jd_tt));
            ra_dec.insert(name.clone(), (ra, dec));
        }
    }
    if ra_dec.is_empty() {
        return (
            StatusCode::OK,
            Json(serde_json::json!({"lines": []})),
        )
            .into_response();
    }
    let lines = acg_lines(&ra_dec, gmst, 1.0);
    let mut lines_out: Vec<Value> = Vec::new();
    for l in &lines {
        if l.line_type == "MC" || l.line_type == "IC" {
            let lonv = l.longitude.unwrap_or(0.0);
            lines_out.push(serde_json::json!({
                "id": format!("{}-{}", l.planet.to_lowercase().replace(' ', "-"), l.line_type.to_lowercase()),
                "planet": l.planet,
                "angle": l.line_type,
                "color": "#c9a0ff",
                "geometry": {"type": "LineString", "coordinates": norm_lon_line(lonv, 1.0)},
            }));
        } else {
            let pts = l.points.clone().unwrap_or_default();
            let segments = split_antimeridian(&pts);
            for (idx, seg) in segments.iter().enumerate() {
                lines_out.push(serde_json::json!({
                    "id": if segments.len() > 1 { format!("{}-{}-{}", l.planet.to_lowercase().replace(' ', "-"), l.line_type.to_lowercase(), idx) } else { format!("{}-{}", l.planet.to_lowercase().replace(' ', "-"), l.line_type.to_lowercase()) },
                    "planet": l.planet,
                    "angle": l.line_type,
                    "color": "#c9a0ff",
                    "geometry": {"type": "LineString", "coordinates": seg},
                }));
            }
        }
    }
    (
        StatusCode::OK,
        Json(serde_json::json!({"lines": lines_out})),
    )
        .into_response()
}

pub async fn midpoints(
    State(state): State<SharedState>,
    Json(req): Json<MidpointsRequest>,
) -> impl IntoResponse {
    let jd_ut = match jd_from_iso(&req.birth.datetime) {
        Ok(j) => j,
        Err(e) => {
            return (
                StatusCode::BAD_REQUEST,
                Json(serde_json::json!({"detail": e})),
            )
                .into_response()
        }
    };
    let jd_tt = jd_ut + 69.184 / 86400.0;
    let bodies_list: Vec<String> = BODIES.iter().map(|s| s.to_string()).collect();
    let chart = create_chart(&state.eph, jd_ut, req.birth.latitude, req.birth.longitude, &bodies_list);
    let longitudes: std::collections::BTreeMap<String, f64> =
        chart.planets.iter().map(|(k, v)| (k.clone(), v.longitude)).collect();
    let default_pairs = vec![
        vec!["Venus".to_string(), "Jupiter".to_string()],
        vec!["Sun".to_string(), "Moon".to_string()],
        vec!["Mars".to_string(), "Saturn".to_string()],
        vec!["Sun".to_string(), "Venus".to_string()],
        vec!["Moon".to_string(), "Jupiter".to_string()],
        vec!["Mercury".to_string(), "Venus".to_string()],
        vec!["Jupiter".to_string(), "Uranus".to_string()],
    ];
    let pairs = req.pairs.clone().unwrap_or(default_pairs);
    let gmst = gmst_deg(jd_ut);
    let mut ra_dec = std::collections::BTreeMap::new();
    for pair in &pairs {
        if pair.len() < 2 {
            continue;
        }
        let a = &pair[0];
        let b = &pair[1];
        if let (Some(&la), Some(&lb)) = (longitudes.get(a), longitudes.get(b)) {
            let mlon = shorter_arc_midpoint(la, lb);
            let (ra, dec) = ecliptic_to_equatorial(mlon, 0.0, true_obliquity(jd_tt));
            ra_dec.insert(format!("{}/{}", a, b), (ra, dec));
        }
    }
    if ra_dec.is_empty() {
        return (
            StatusCode::OK,
            Json(serde_json::json!({"lines": []})),
        )
            .into_response();
    }
    let lines = acg_lines(&ra_dec, gmst, 1.0);
    let mut lines_out: Vec<Value> = Vec::new();
    for l in &lines {
        if l.line_type == "MC" || l.line_type == "IC" {
            let lonv = l.longitude.unwrap_or(0.0);
            lines_out.push(serde_json::json!({
                "id": format!("{}-{}", l.planet.to_lowercase().replace(' ', "-").replace('/', "-"), l.line_type.to_lowercase()),
                "planet": l.planet,
                "angle": l.line_type,
                "color": planet_color(&l.planet.split('/').next().unwrap_or("")),
                "geometry": {"type": "LineString", "coordinates": norm_lon_line(lonv, 1.0)},
            }));
        } else {
            let pts = l.points.clone().unwrap_or_default();
            let segments = split_antimeridian(&pts);
            for (idx, seg) in segments.iter().enumerate() {
                lines_out.push(serde_json::json!({
                    "id": if segments.len() > 1 { format!("{}-{}-{}", l.planet.to_lowercase().replace(' ', "-").replace('/', "-"), l.line_type.to_lowercase(), idx) } else { format!("{}-{}", l.planet.to_lowercase().replace(' ', "-").replace('/', "-"), l.line_type.to_lowercase()) },
                    "planet": l.planet,
                    "angle": l.line_type,
                    "color": planet_color(&l.planet.split('/').next().unwrap_or("")),
                    "geometry": {"type": "LineString", "coordinates": seg},
                }));
            }
        }
    }
    (
        StatusCode::OK,
        Json(serde_json::json!({"lines": lines_out})),
    )
        .into_response()
}

fn shorter_arc_midpoint(lon_a: f64, lon_b: f64) -> f64 {
    let a = lon_a.rem_euclid(360.0);
    let b = lon_b.rem_euclid(360.0);
    let diff = (a - b).abs();
    if diff <= 180.0 {
        (a + b) / 2.0 % 360.0
    } else {
        ((a + b) / 2.0 + 180.0) % 360.0
    }
}

pub async fn crossings(
    State(state): State<SharedState>,
    Json(req): Json<CrossingsRequest>,
) -> impl IntoResponse {
    // Reuse generate_acg then compute crossings like Python
    let bodies = bodies_or_default(&req.bodies);
    let acg = match generate_acg(
        &state.eph,
        &req.birth.datetime,
        req.birth.latitude,
        req.birth.longitude,
        &bodies,
        1.0,
    ) {
        Ok(v) => v,
        Err(e) => {
            return (
                StatusCode::BAD_REQUEST,
                Json(serde_json::json!({"detail": e})),
            )
                .into_response()
        }
    };
    let lines = acg.get("lines").and_then(|x| x.as_array()).cloned().unwrap_or_default();
    let parans = acg.get("parans").and_then(|x| x.as_array()).cloned().unwrap_or_default();
    let meridians: Vec<Value> = lines.iter().filter(|l| {
        l.get("angle").and_then(|x| x.as_str()).map(|a| a == "MC" || a == "IC").unwrap_or(false)
    }).cloned().collect();
    let curves: Vec<Value> = lines.iter().filter(|l| {
        l.get("angle").and_then(|x| x.as_str()).map(|a| a == "ASC" || a == "DSC").unwrap_or(false)
    }).cloned().collect();

    let mut crossings: Vec<Value> = Vec::new();
    let mut seen: std::collections::HashSet<(i64, i64)> = std::collections::HashSet::new();
    for m in &meridians {
        let mcoords = m.get("geometry").and_then(|g| g.get("coordinates")).and_then(|c| c.as_array()).cloned().unwrap_or_default();
        if mcoords.is_empty() { continue; }
        let mlon = mcoords[0][0].as_f64().unwrap_or(0.0);
        for c in &curves {
            let ccoords = c.get("geometry").and_then(|g| g.get("coordinates")).and_then(|c| c.as_array()).cloned().unwrap_or_default();
            for i in 0..ccoords.len().saturating_sub(1) {
                let lon1 = ccoords[i][0].as_f64().unwrap_or(0.0);
                let lat1 = ccoords[i][1].as_f64().unwrap_or(0.0);
                let lon2 = ccoords[i + 1][0].as_f64().unwrap_or(0.0);
                let lat2 = ccoords[i + 1][1].as_f64().unwrap_or(0.0);
                if (lon2 - lon1).abs() > 180.0 { continue; }
                let d1 = lon1 - mlon;
                let d2 = lon2 - mlon;
                let tval = if d1 == 0.0 {
                    0.0
                } else if d1 * d2 <= 0.0 && d1 != d2 {
                    d1 / (d1 - d2)
                } else {
                    continue;
                };
                let lat = lat1 + tval * (lat2 - lat1);
                let key = ((lat * 1.0).round() as i64, (mlon * 1.0).round() as i64);
                if seen.contains(&key) { continue; }
                seen.insert(key);
                crossings.push(serde_json::json!({
                    "type": "line-cross",
                    "planet_a": m.get("planet"),
                    "angle_a": m.get("angle"),
                    "planet_b": c.get("planet"),
                    "angle_b": c.get("angle"),
                    "color_a": m.get("color"),
                    "color_b": c.get("color"),
                    "latitude": (lat * 10000.0).round() / 10000.0,
                    "longitude": (mlon * 10000.0).round() / 10000.0,
                    "interpretation": format!("{} {} meets {} {}.", m.get("planet").and_then(|x|x.as_str()).unwrap_or(""), m.get("angle").and_then(|x|x.as_str()).unwrap_or(""), c.get("planet").and_then(|x|x.as_str()).unwrap_or(""), c.get("angle").and_then(|x|x.as_str()).unwrap_or("")),
                }));
                break;
            }
        }
    }
    // paran markers
    for p in &parans {
        let p_lat = p.get("latitude").and_then(|x| x.as_f64()).unwrap_or(0.0);
        let p_lng = p.get("longitude").and_then(|x| x.as_f64()).unwrap_or(0.0);
        if p_lat.abs() < 0.01 && p_lng.abs() < 0.01 { continue; }
        crossings.push(serde_json::json!({
            "type": "paran",
            "planet_a": p.get("planet_a"),
            "angle_a": p.get("circle_a"),
            "planet_b": p.get("planet_b"),
            "angle_b": p.get("circle_b"),
            "latitude": p.get("latitude"),
            "longitude": p.get("longitude"),
            "interpretation": format!("{} {} meets {} {}.", p.get("planet_a").and_then(|x|x.as_str()).unwrap_or(""), p.get("circle_a").and_then(|x|x.as_str()).unwrap_or(""), p.get("planet_b").and_then(|x|x.as_str()).unwrap_or(""), p.get("circle_b").and_then(|x|x.as_str()).unwrap_or("")),
        }));
    }
    crossings.sort_by(|a, b| {
        let la = a.get("latitude").and_then(|x| x.as_f64()).unwrap_or(0.0);
        let lb = b.get("latitude").and_then(|x| x.as_f64()).unwrap_or(0.0);
        (la - req.birth.latitude).abs().partial_cmp(&(lb - req.birth.latitude).abs()).unwrap()
    });
    let max = 80;
    let crossings: Vec<Value> = crossings.into_iter().take(max).collect();
    (
        StatusCode::OK,
        Json(serde_json::json!({"crossings": crossings})),
    )
        .into_response()
}

pub async fn location_analysis(
    State(state): State<SharedState>,
    Json(req): Json<LocationAnalysisRequest>,
) -> impl IntoResponse {
    let lat = req.location.get("latitude").copied().unwrap_or(0.0);
    let lng = req.location.get("longitude").copied().unwrap_or(0.0);
    if lat == 0.0 && lng == 0.0 && !req.location.contains_key("latitude") {
        return (
            StatusCode::BAD_REQUEST,
            Json(serde_json::json!({"detail": "location.latitude/longitude required"})),
        )
            .into_response();
    }
    let bodies = bodies_or_default(&req.bodies);
    let calc_bodies: Vec<String> = if bodies.is_empty() {
        BODIES.iter().map(|s| s.to_string()).collect()
    } else {
        bodies.clone()
    };
    let jd_ut = match jd_from_iso(&req.birth.datetime) {
        Ok(j) => j,
        Err(e) => {
            return (
                StatusCode::BAD_REQUEST,
                Json(serde_json::json!({"detail": e})),
            )
                .into_response()
        }
    };
    // basic analysis: planet positions at birth and location angles
    let mut planets_out = serde_json::Map::new();
    for b in &calc_bodies {
        if let Some(pd) = calc_body(&state.eph, b, jd_ut) {
            planets_out.insert(b.clone(), serde_json::json!({
                "longitude": pd.longitude,
                "latitude": pd.latitude,
                "right_ascension": pd.right_ascension,
                "declination": pd.declination,
            }));
        }
    }
    (
        StatusCode::OK,
        Json(serde_json::json!({
            "birth": {"latitude": req.birth.latitude, "longitude": req.birth.longitude},
            "location": {"latitude": lat, "longitude": lng},
            "planets": planets_out,
        })),
    )
        .into_response()
}
