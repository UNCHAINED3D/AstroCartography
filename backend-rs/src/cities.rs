use crate::astro::*;
use serde_json::{json, Value};
use std::collections::BTreeMap;
use swisseph::Ephemeris;

const WORLD_CITIES_JSON: &str = include_str!("../../backend/data/world_cities.json");

fn load_cities() -> Vec<Value> {
    serde_json::from_str(WORLD_CITIES_JSON).unwrap_or_else(|_| Vec::new())
}

fn haversine_km(lat1: f64, lon1: f64, lat2: f64, lon2: f64) -> f64 {
    let r = 6371.0088;
    let p1 = lat1.to_radians();
    let p2 = lat2.to_radians();
    let dphi = (lat2 - lat1).to_radians();
    let dlam = (lon2 - lon1).to_radians();
    let a = (dphi / 2.0).sin().powi(2)
        + p1.cos() * p2.cos() * (dlam / 2.0).sin().powi(2);
    2.0 * r * a.sqrt().asin().min(1.0)
}

fn bearing_deg(lat1: f64, lon1: f64, lat2: f64, lon2: f64) -> f64 {
    let p1 = lat1.to_radians();
    let p2 = lat2.to_radians();
    let dlon = (lon2 - lon1).to_radians();
    let x = dlon.sin() * p2.cos();
    let y = p1.cos() * p2.sin() - p1.sin() * p2.cos() * dlon.cos();
    (x.atan2(y).to_degrees() + 360.0) % 360.0
}

fn point_to_segment(plat: f64, plon: f64, a: &[f64], b: &[f64]) -> f64 {
    let alat = a[1];
    let alon = a[0];
    let blat = b[1];
    let blon = b[0];
    let seg_bearing = bearing_deg(alat, alon, blat, blon).to_radians();
    let seg_dist = haversine_km(alat, alon, blat, blon);
    let dlat = (plat - alat).to_radians();
    let dlon = (plon - alon).to_radians();
    let along = (dlat * seg_bearing.cos() + dlon * seg_bearing.sin()) * 111.0;
    let along = along.clamp(0.0, seg_dist);
    let perp_sq = haversine_km(alat, alon, plat, plon).powi(2) - along.powi(2);
    if perp_sq < 0.0 {
        0.0
    } else {
        perp_sq.sqrt()
    }
}

fn distance_to_line(lat: f64, lon: f64, coords: &[Value]) -> f64 {
    if coords.is_empty() {
        return f64::INFINITY;
    }
    let mut best = haversine_km(lat, lon, coords[0][1].as_f64().unwrap_or(0.0), coords[0][0].as_f64().unwrap_or(0.0));
    for i in 0..coords.len().saturating_sub(1) {
        let a = &coords[i];
        let b = &coords[i + 1];
        let arr_a = vec![a[0].as_f64().unwrap_or(0.0), a[1].as_f64().unwrap_or(0.0)];
        let arr_b = vec![b[0].as_f64().unwrap_or(0.0), b[1].as_f64().unwrap_or(0.0)];
        let d = point_to_segment(lat, lon, &arr_a, &arr_b);
        if d < best {
            best = d;
        }
    }
    best
}

// scoring tables
fn domain_planets() -> BTreeMap<&'static str, Vec<&'static str>> {
    let mut m = BTreeMap::new();
    m.insert("Love", vec!["Venus", "Moon", "Sun", "Jupiter"]);
    m.insert("Career", vec!["Sun", "Mars", "Jupiter", "Saturn", "Mercury"]);
    m.insert("Home", vec!["Moon", "Venus", "Saturn", "Jupiter"]);
    m.insert("Growth", vec!["Jupiter", "Sun", "Uranus", "Mercury"]);
    m.insert("Peace", vec!["Moon", "Neptune", "Venus", "Jupiter", "Chiron"]);
    m
}

fn domain_houses() -> BTreeMap<&'static str, Vec<i64>> {
    let mut m = BTreeMap::new();
    m.insert("Love", vec![5, 7, 8]);
    m.insert("Career", vec![2, 6, 10]);
    m.insert("Home", vec![1, 4, 12]);
    m.insert("Growth", vec![1, 9, 11]);
    m.insert("Peace", vec![4, 9, 12]);
    m
}

fn domain_angle_boost() -> BTreeMap<&'static str, BTreeMap<&'static str, f64>> {
    let mut m = BTreeMap::new();
    let mut mc = BTreeMap::new();
    mc.insert("Career", 0.5);
    m.insert("MC", mc);
    let mut ic = BTreeMap::new();
    ic.insert("Home", 0.5);
    m.insert("IC", ic);
    let mut asc = BTreeMap::new();
    asc.insert("Love", 0.3);
    asc.insert("Growth", 0.3);
    m.insert("ASC", asc);
    let mut dsc = BTreeMap::new();
    dsc.insert("Love", 0.5);
    m.insert("DSC", dsc);
    m
}

fn line_domain_weight(planet: &str, angle: &str) -> BTreeMap<String, f64> {
    let dp = domain_planets();
    let boost = domain_angle_boost();
    let mut weights = BTreeMap::new();
    for (domain, planets) in &dp {
        let mut w = if planets.contains(&planet) { 1.0 } else { 0.15 };
        if let Some(b) = boost.get(angle) {
            if let Some(v) = b.get(domain) {
                w += v;
            }
        }
        weights.insert(domain.to_string(), (w * 1000.0).round() / 1000.0);
    }
    weights
}

fn slider_to_domain() -> BTreeMap<&'static str, &'static str> {
    let mut m = BTreeMap::new();
    m.insert("love", "Love");
    m.insert("career", "Career");
    m.insert("home", "Home");
    m.insert("growth", "Growth");
    m.insert("peace", "Peace");
    m
}

fn category_weights() -> BTreeMap<&'static str, BTreeMap<&'static str, f64>> {
    // focus preset weights: planet-angle -> weight
    let mut m = BTreeMap::new();
    // love
    let mut love = BTreeMap::new();
    for (k, v) in [
        ("Venus-asc", 10.0), ("Venus-dsc", 10.0), ("Venus-mc", 8.0), ("Venus-ic", 7.0),
        ("Moon-dsc", 8.0), ("Moon-asc", 7.0), ("Sun-dsc", 7.0), ("Jupiter-dsc", 8.0),
        ("Neptune-dsc", 5.0), ("Mars-dsc", 6.0),
    ] { love.insert(k, v); }
    m.insert("love", love);
    let mut career = BTreeMap::new();
    for (k, v) in [
        ("Sun-mc", 10.0), ("Mars-mc", 9.0), ("Jupiter-mc", 9.0), ("Saturn-mc", 7.0),
        ("Mercury-mc", 8.0), ("Sun-asc", 7.0), ("Pluto-mc", 6.0), ("Mars-asc", 7.0),
    ] { career.insert(k, v); }
    m.insert("career", career);
    let mut wealth = BTreeMap::new();
    for (k, v) in [
        ("Jupiter-mc", 10.0), ("Venus-mc", 9.0), ("Jupiter-asc", 9.0), ("Sun-mc", 8.0),
        ("Pluto-mc", 7.0), ("Mercury-mc", 6.0), ("Venus-asc", 7.0),
    ] { wealth.insert(k, v); }
    m.insert("wealth", wealth);
    let mut peace = BTreeMap::new();
    for (k, v) in [
        ("Moon-ic", 10.0), ("Neptune-ic", 9.0), ("Venus-ic", 8.0), ("Jupiter-ic", 8.0),
        ("Sun-ic", 7.0), ("Chiron-ic", 6.0), ("Moon-asc", 7.0),
    ] { peace.insert(k, v); }
    m.insert("peace", peace);
    let mut growth = BTreeMap::new();
    for (k, v) in [
        ("Jupiter-asc", 10.0), ("Sun-asc", 9.0), ("Uranus-asc", 7.0), ("Mercury-asc", 8.0),
        ("Chiron-asc", 7.0), ("Pluto-asc", 6.0), ("Jupiter-mc", 8.0),
    ] { growth.insert(k, v); }
    m.insert("growth", growth);
    let mut all = BTreeMap::new();
    for (k, v) in [
        ("Venus-dsc", 8.0), ("Sun-mc", 8.0), ("Jupiter-mc", 9.0), ("Jupiter-asc", 8.0),
        ("Venus-asc", 8.0), ("Moon-ic", 7.0), ("Mars-mc", 6.0), ("Mercury-mc", 6.0),
    ] { all.insert(k, v); }
    m.insert("all", all);
    m
}

fn house_of(lon: f64, cusps: &[f64]) -> i64 {
    let lon = lon.rem_euclid(360.0);
    let n = cusps.len();
    for h in 1..=n {
        let start = cusps[h - 1].rem_euclid(360.0);
        let end = cusps[h % n].rem_euclid(360.0);
        if start <= end {
            if start <= lon && lon < end {
                return h as i64;
            }
        } else if lon >= start || lon < end {
            return h as i64;
        }
    }
    n as i64
}

pub fn rank_cities_for_birth(
    eph: &Ephemeris,
    iso: &str,
    birth_lat: f64,
    birth_lon: f64,
    focus: &str,
    limit: usize,
    weights: &Option<std::collections::HashMap<String, f64>>,
    include_breakdown: bool,
    region: &Option<String>,
    center_lat: &Option<f64>,
    center_lon: &Option<f64>,
    radius_km: &Option<f64>,
    bbox: &Option<Vec<f64>>,
    max_distance_from_birth_km: &Option<f64>,
) -> Vec<Value> {
    let focus_key = if ["love", "career", "wealth", "peace", "growth", "all"].contains(&focus.to_lowercase().as_str()) {
        focus.to_lowercase()
    } else {
        "all".to_string()
    };
    let cw = category_weights();
    let preset_weights = cw.get(focus_key.as_str()).cloned().unwrap_or_default();

    // sliders
    let mut sliders: BTreeMap<String, f64> = BTreeMap::new();
    if let Some(w) = weights {
        for (k, v) in w {
            let domain = match k.to_lowercase().as_str() {
                "love" => "Love",
                "career" => "Career",
                "home" => "Home",
                "growth" => "Growth",
                "peace" => "Peace",
                _ => continue,
            };
            let val = v.clamp(0.0, 10.0) / 10.0;
            sliders.insert(domain.to_string(), val);
        }
    }
    let use_sliders = !sliders.is_empty() && sliders.values().any(|&v| v > 0.0);

    // acg
    let bodies: Vec<String> = BODIES.iter().map(|s| s.to_string()).collect();
    let acg = generate_acg(eph, iso, birth_lat, birth_lon, &bodies, 1.0).unwrap_or(json!({}));
    let lines = acg.get("lines").and_then(|x| x.as_array()).cloned().unwrap_or_default();
    let parans = acg.get("parans").and_then(|x| x.as_array()).cloned().unwrap_or_default();

    // relocated charts
    let jd_ut = jd_from_iso(iso).unwrap_or(0.0);
    let all_cities = load_cities();
    // filter cities
    let mut cities: Vec<Value> = Vec::new();
    for c in &all_cities {
        let clat = c.get("lat").and_then(|x| x.as_f64()).unwrap_or(0.0);
        let clng = c.get("lng").and_then(|x| x.as_f64()).unwrap_or(0.0);
        if let Some(reg) = region {
            if c.get("region").and_then(|x| x.as_str()).unwrap_or("").to_lowercase() != reg.to_lowercase() {
                continue;
            }
        }
        if let (Some(cla), Some(clo), Some(rad)) = (center_lat, center_lon, radius_km) {
            if haversine_km(*cla, *clo, clat, clng) > *rad {
                continue;
            }
        }
        if let Some(bb) = bbox {
            if bb.len() == 4 {
                let (la1, lo1, la2, lo2) = (bb[0], bb[1], bb[2], bb[3]);
                if !(la1.min(la2) <= clat && clat <= la1.max(la2) && lo1.min(lo2) <= clng && clng <= lo1.max(lo2)) {
                    continue;
                }
            }
        }
        if let Some(md) = max_distance_from_birth_km {
            if haversine_km(birth_lat, birth_lon, clat, clng) > *md {
                continue;
            }
        }
        cities.push(c.clone());
    }
    if cities.is_empty() {
        cities = all_cities.clone();
    }

    // relocated
    let mut relocated: BTreeMap<String, (Vec<f64>, BTreeMap<String, f64>)> = BTreeMap::new();
    for city in &cities {
        let cname = city.get("name").and_then(|x| x.as_str()).unwrap_or("").to_string();
        let clat = city.get("lat").and_then(|x| x.as_f64()).unwrap_or(0.0);
        let clng = city.get("lng").and_then(|x| x.as_f64()).unwrap_or(0.0);
        if let Ok(hr) = eph.houses(jd_ut, clat, clng, swisseph::types::HouseSystem::Placidus) {
            let cusps: Vec<f64> = hr.cusps[1..13].to_vec();
            // planet longitudes same as birth; compute from eph at jd_ut
            let mut planets = BTreeMap::new();
            for b in &bodies {
                if let Some(pd) = calc_body(eph, b, jd_ut) {
                    planets.insert(b.clone(), pd.longitude);
                }
            }
            relocated.insert(cname, (cusps, planets));
        }
    }

    // effective weight closure
    let effective_weight = |planet: &str, angle: &str| -> f64 {
        let key = format!("{}-{}", planet, angle.to_lowercase());
        if use_sliders {
            let dw = line_domain_weight(planet, angle);
            let mut blended = 0.0;
            for (domain, slider) in &sliders {
                if *slider <= 0.0 {
                    continue;
                }
                if let Some(w) = dw.get(domain) {
                    blended += slider * w;
                }
            }
            (blended * 1000.0).round() / 1000.0
        } else {
            *preset_weights.get(key.as_str()).unwrap_or(&if focus_key == "all" { 2.0 } else { 0.5 })
        }
    };

    let mut results: Vec<Value> = Vec::new();
    for city in &cities {
        let cname = city.get("name").and_then(|x| x.as_str()).unwrap_or("").to_string();
        let country = city.get("country").and_then(|x| x.as_str()).unwrap_or("").to_string();
        let region = city.get("region").and_then(|x| x.as_str()).unwrap_or("").to_string();
        let clat = city.get("lat").and_then(|x| x.as_f64()).unwrap_or(0.0);
        let clng = city.get("lng").and_then(|x| x.as_f64()).unwrap_or(0.0);

        let mut acg_points = 0.0;
        let mut house_points = 0.0;
        let mut paran_points = 0.0;
        let mut nearby: Vec<Value> = Vec::new();

        for line in &lines {
            let planet = line.get("planet").and_then(|x| x.as_str()).unwrap_or("");
            let angle = line.get("angle").and_then(|x| x.as_str()).unwrap_or("");
            let weight = effective_weight(planet, angle);
            if weight <= 0.0 {
                continue;
            }
            let coords = line.get("geometry").and_then(|g| g.get("coordinates")).and_then(|c| c.as_array()).cloned().unwrap_or_default();
            let min_dist = distance_to_line(clat, clng, &coords);
            if min_dist <= 750.0 {
                let proximity = (1.0 - (min_dist / 750.0)).powf(1.5);
                let influence = weight * 4.5 * proximity;
                acg_points += influence;
                nearby.push(json!({
                    "planet": planet,
                    "angle": angle,
                    "color": line.get("color").cloned().unwrap_or(json!("#ffaa00")),
                    "distance_km": min_dist.round() as i64,
                    "score_contribution": (influence * 10.0).round() / 10.0,
                }));
            }
        }

        // house scoring
        let mut house_placements: Vec<Value> = Vec::new();
        if let Some((cusps, planets)) = relocated.get(&cname) {
            for (name, lon) in planets {
                let house = house_of(*lon, cusps);
                for (domain, dplanets) in domain_planets() {
                    if dplanets.contains(&name.as_str()) && domain_houses().get(domain).map(|v| v.contains(&house)).unwrap_or(false) {
                        let slider = sliders.get(domain).copied().unwrap_or(if use_sliders { 0.0 } else { 0.5 });
                        let pts = 1.5 * (if use_sliders { slider } else { 1.0 });
                        house_points += pts;
                        house_placements.push(json!({
                            "planet": name,
                            "house": house,
                            "domain": domain,
                            "points": (pts * 100.0).round() / 100.0,
                        }));
                    }
                }
            }
        }
        if house_points > 15.0 {
            house_points = 15.0;
        }

        // paran scoring
        let mut city_paran_names: Vec<String> = Vec::new();
        for p in &parans {
            let plat = p.get("latitude").and_then(|x| x.as_f64()).unwrap_or(0.0);
            let d = (plat - clat).abs();
            if d <= 6.0 {
                let mut pts = 3.0 * (1.0 - (d / 6.0));
                if use_sliders {
                    if let Some(mx) = sliders.values().cloned().fold(None::<f64>, |a, b| Some(a.map_or(b, |x| x.max(b)))) {
                        pts *= mx;
                    } else {
                        pts *= 1.0;
                    }
                }
                paran_points += pts;
                city_paran_names.push(format!(
                    "{} × {}",
                    p.get("planet_a").and_then(|x| x.as_str()).unwrap_or("?"),
                    p.get("planet_b").and_then(|x| x.as_str()).unwrap_or("?")
                ));
            }
        }
        if paran_points > 8.0 {
            paran_points = 8.0;
        }

        let city_score = 45.0 + acg_points + house_points + paran_points;
        nearby.sort_by(|a, b| {
            let da = a.get("distance_km").and_then(|x| x.as_i64()).unwrap_or(0);
            let db = b.get("distance_km").and_then(|x| x.as_i64()).unwrap_or(0);
            da.cmp(&db)
        });
        let top_influences: Vec<Value> = nearby.into_iter().take(4).collect();

        let love_score = (city_score * 0.95 + if top_influences.iter().any(|i| {
            let pl = i.get("planet").and_then(|x| x.as_str()).unwrap_or("");
            pl == "Venus" || pl == "Moon"
        }) { 10.0 } else { 0.0 })
        .round()
        .min(99.0) as i64;
        let career_score = (city_score * 0.92 + if top_influences.iter().any(|i| {
            let pl = i.get("planet").and_then(|x| x.as_str()).unwrap_or("");
            pl == "Sun" || pl == "Mars" || pl == "Jupiter"
        }) { 10.0 } else { 0.0 })
        .round()
        .min(99.0) as i64;
        let peace_score = (city_score * 0.88 + if top_influences.iter().any(|i| {
            let pl = i.get("planet").and_then(|x| x.as_str()).unwrap_or("");
            pl == "Neptune" || pl == "Moon"
        }) { 10.0 } else { 0.0 })
        .round()
        .min(99.0) as i64;
        let growth_score = (city_score * 0.90 + if top_influences.iter().any(|i| {
            let pl = i.get("planet").and_then(|x| x.as_str()).unwrap_or("");
            pl == "Jupiter" || pl == "Sun"
        }) { 10.0 } else { 0.0 })
        .round()
        .min(99.0) as i64;

        let overall_score = (city_score.round() as i64).clamp(45, 99);

        let summary = if !top_influences.is_empty() {
            let bi = &top_influences[0];
            format!(
                "Strong {} {} influence within {} km.",
                bi.get("planet").and_then(|x| x.as_str()).unwrap_or(""),
                bi.get("angle").and_then(|x| x.as_str()).unwrap_or(""),
                bi.get("distance_km").and_then(|x| x.as_i64()).unwrap_or(0)
            )
        } else if !city_paran_names.is_empty() {
            format!("Paran blending of {} near this latitude.", city_paran_names[0])
        } else if !house_placements.is_empty() {
            let hp = &house_placements[0];
            format!(
                "Relocated {} in house {} ({} region).",
                hp.get("planet").and_then(|x| x.as_str()).unwrap_or(""),
                hp.get("house").and_then(|x| x.as_i64()).unwrap_or(0),
                hp.get("domain").and_then(|x| x.as_str()).unwrap_or("")
            )
        } else {
            "Harmonious ambient energy location.".to_string()
        };

        let mut result = json!({
            "name": cname,
            "country": country,
            "region": region,
            "latitude": clat,
            "longitude": clng,
            "overall_score": overall_score,
            "scores": {
                "love": love_score,
                "career": career_score,
                "peace": peace_score,
                "growth": growth_score,
            },
            "primary_influences": top_influences,
            "summary": summary,
        });
        if include_breakdown {
            result["score_breakdown"] = json!({
                "acg": (acg_points * 10.0).round() / 10.0,
                "houses": (house_points * 10.0).round() / 10.0,
                "parans": (paran_points * 10.0).round() / 10.0,
            });
            result["house_placements"] = json!(house_placements.into_iter().take(4).collect::<Vec<_>>());
        }
        results.push(result);
    }

    results.sort_by(|a, b| {
        let sa = a.get("overall_score").and_then(|x| x.as_i64()).unwrap_or(0);
        let sb = b.get("overall_score").and_then(|x| x.as_i64()).unwrap_or(0);
        sb.cmp(&sa)
    });
    results.truncate(limit);
    results
}

pub fn rank_cities_for_couple(
    eph: &Ephemeris,
    iso_a: &str, lat_a: f64, lon_a: f64,
    iso_b: &str, lat_b: f64, lon_b: f64,
    focus: &str,
    limit: usize,
    weights: &Option<std::collections::HashMap<String, f64>>,
) -> Vec<Value> {
    let full = load_cities().len();
    let ra = rank_cities_for_birth(eph, iso_a, lat_a, lon_a, focus, full, weights, false, &None, &None, &None, &None, &None, &None);
    let rb = rank_cities_for_birth(eph, iso_b, lat_b, lon_b, focus, full, weights, false, &None, &None, &None, &None, &None, &None);
    let max_a = ra.iter().map(|c| c.get("overall_score").and_then(|x| x.as_i64()).unwrap_or(0)).max().unwrap_or(1).max(1);
    let max_b = rb.iter().map(|c| c.get("overall_score").and_then(|x| x.as_i64()).unwrap_or(0)).max().unwrap_or(1).max(1);
    let by_a: BTreeMap<String, Value> = ra.into_iter().filter_map(|c| {
        let name = c.get("name").and_then(|x| x.as_str())?.to_string();
        Some((name, c))
    }).collect();
    let by_b: BTreeMap<String, Value> = rb.into_iter().filter_map(|c| {
        let name = c.get("name").and_then(|x| x.as_str())?.to_string();
        Some((name, c))
    }).collect();

    let mut results: Vec<Value> = Vec::new();
    for (name, ca) in &by_a {
        let cb = match by_b.get(name) { Some(v) => v, None => continue };
        let sa = ca.get("overall_score").and_then(|x| x.as_i64()).unwrap_or(0) as f64;
        let sb = cb.get("overall_score").and_then(|x| x.as_i64()).unwrap_or(0) as f64;
        let na = sa / max_a as f64;
        let nb = sb / max_b as f64;
        let benefic_a = ca.get("primary_influences").and_then(|x| x.as_array()).map(|arr| arr.iter().any(|i| {
            let pl = i.get("planet").and_then(|x| x.as_str()).unwrap_or("");
            ["Venus", "Moon", "Jupiter", "Sun"].contains(&pl)
        })).unwrap_or(false);
        let benefic_b = cb.get("primary_influences").and_then(|x| x.as_array()).map(|arr| arr.iter().any(|i| {
            let pl = i.get("planet").and_then(|x| x.as_str()).unwrap_or("");
            ["Venus", "Moon", "Jupiter", "Sun"].contains(&pl)
        })).unwrap_or(false);
        let bonus = if benefic_a && benefic_b { 6.0 } else { 0.0 };
        let combined = ((0.45 * na + 0.45 * nb) * 100.0 + bonus * 1.5).round().clamp(45.0, 99.0) as i64;
        let mut influences: Vec<Value> = Vec::new();
        if let Some(a) = ca.get("primary_influences").and_then(|x| x.as_array()) { influences.extend(a.clone()); }
        if let Some(b) = cb.get("primary_influences").and_then(|x| x.as_array()) { influences.extend(b.clone()); }
        influences.sort_by(|x, y| {
            let da = x.get("distance_km").and_then(|v| v.as_i64()).unwrap_or(0);
            let db = y.get("distance_km").and_then(|v| v.as_i64()).unwrap_or(0);
            da.cmp(&db)
        });
        influences.truncate(4);
        let best = influences.first().cloned();
        let summary = if let Some(bi) = &best {
            let mut s = format!("Shared {} {} energy within {} km.", bi.get("planet").and_then(|x| x.as_str()).unwrap_or(""), bi.get("angle").and_then(|x| x.as_str()).unwrap_or(""), bi.get("distance_km").and_then(|x| x.as_i64()).unwrap_or(0));
            if bonus > 0.0 { s += " Benefic lines for both partners overlap here."; }
            s
        } else {
            "Workable for both, no dominant shared lines.".to_string()
        };
        let love = ((ca.get("scores").and_then(|s| s.get("love")).and_then(|x| x.as_i64()).unwrap_or(0) + cb.get("scores").and_then(|s| s.get("love")).and_then(|x| x.as_i64()).unwrap_or(0)) as f64 / 2.0).round() as i64;
        let career = ((ca.get("scores").and_then(|s| s.get("career")).and_then(|x| x.as_i64()).unwrap_or(0) + cb.get("scores").and_then(|s| s.get("career")).and_then(|x| x.as_i64()).unwrap_or(0)) as f64 / 2.0).round() as i64;
        let peace = ((ca.get("scores").and_then(|s| s.get("peace")).and_then(|x| x.as_i64()).unwrap_or(0) + cb.get("scores").and_then(|s| s.get("peace")).and_then(|x| x.as_i64()).unwrap_or(0)) as f64 / 2.0).round() as i64;
        let growth = ((ca.get("scores").and_then(|s| s.get("growth")).and_then(|x| x.as_i64()).unwrap_or(0) + cb.get("scores").and_then(|s| s.get("growth")).and_then(|x| x.as_i64()).unwrap_or(0)) as f64 / 2.0).round() as i64;
        results.push(json!({
            "name": name,
            "country": ca.get("country"),
            "region": ca.get("region"),
            "latitude": ca.get("latitude"),
            "longitude": ca.get("longitude"),
            "overall_score": combined,
            "scores": {"love": love, "career": career, "peace": peace, "growth": growth},
            "primary_influences": influences,
            "summary": summary,
        }));
    }
    results.sort_by(|a, b| {
        let sa = a.get("overall_score").and_then(|x| x.as_i64()).unwrap_or(0);
        let sb = b.get("overall_score").and_then(|x| x.as_i64()).unwrap_or(0);
        sb.cmp(&sa)
    });
    results.truncate(limit);
    results
}
