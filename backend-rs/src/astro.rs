use chrono::{Datelike, Timelike};
use chrono::{DateTime, FixedOffset, Utc};
use serde_json::{json, Value};
use std::collections::BTreeMap;
use swisseph::date::julday;
use swisseph::types::{Body, CalendarType, HouseSystem};
use swisseph::{CalcFlags, Ephemeris, EphemerisConfig};

pub const BODIES: &[&str] = &[
    "Sun", "Moon", "Mercury", "Venus", "Mars", "Jupiter", "Saturn", "Uranus", "Neptune", "Pluto",
    "Chiron",
];

pub fn planet_color(name: &str) -> &'static str {
    match name {
        "Sun" => "#FFD700",
        "Moon" => "#C5C5C5",
        "Mercury" => "#FF6B35",
        "Venus" => "#F7C948",
        "Mars" => "#E63946",
        "Jupiter" => "#4CC9F0",
        "Saturn" => "#8D99AE",
        "Uranus" => "#80FFDB",
        "Neptune" => "#5A7FFF",
        "Pluto" => "#9D4EDD",
        "Chiron" => "#2EC4B6",
        "Lilith" => "#FF3366",
        "True Node" => "#FF70A6",
        _ => "#ffffff",
    }
}

#[derive(Clone)]
pub struct PlanetData {
    pub name: String,
    pub longitude: f64,
    pub latitude: f64,
    pub distance: f64,
    pub speed_long: f64,
    pub right_ascension: f64,
    pub declination: f64,
}

pub struct Chart {
    pub jd_ut: f64,
    pub lat: f64,
    pub lon: f64,
    pub planets: BTreeMap<String, PlanetData>,
}

pub fn norm(x: f64) -> f64 {
    let r = x.rem_euclid(360.0);
    r
}

pub fn norm_signed(x: f64) -> f64 {
    let mut r = x.rem_euclid(360.0);
    if r > 180.0 {
        r -= 360.0;
    }
    r
}

pub fn jd_from_iso(iso: &str) -> Result<f64, String> {
    let mut s = iso.trim().to_string();
    if s.ends_with('Z') {
        s = s[..s.len() - 1].to_string() + "+00:00";
    }
    if !s.contains('T') {
        s = format!("{}T12:00:00+00:00", s);
    }
    let dt: DateTime<FixedOffset> = s
        .parse()
        .map_err(|e| format!("bad datetime: {}", e))?;
    let utc = dt.with_timezone(&Utc);
    let h = utc.hour() as f64
        + utc.minute() as f64 / 60.0
        + utc.second() as f64 / 3600.0
        + utc.nanosecond() as f64 / 3_600_000_000_000.0;
    Ok(julday(
        utc.year(),
        utc.month() as i32,
        utc.day() as i32,
        h,
        CalendarType::Gregorian,
    ))
}

pub fn true_obliquity(jd_ut: f64) -> f64 {
    let d = jd_ut - 2451545.0;
    let t = d / 36525.0;
    23.43929111 - 0.0130041667 * t - 0.0000001639 * t * t + 0.0000005036 * t * t * t
}

pub fn ecliptic_to_equatorial(lon: f64, lat: f64, obliq: f64) -> (f64, f64) {
    let ol = lon.to_radians();
    let ob = obliq.to_radians();
    let latr = lat.to_radians();
    let ra = (ol.sin() * ob.cos() - latr.tan() * ob.sin()).atan2(ol.cos());
    let dec = (latr.sin() * ob.cos() + latr.cos() * ob.sin() * ol.sin()).asin();
    (norm(ra.to_degrees()), dec.to_degrees())
}

pub fn gmst_deg(jd_ut: f64) -> f64 {
    let d = jd_ut - 2451545.0;
    let t = d / 36525.0;
    let g = 280.46061837 + 360.98564736629 * d + 0.000387933 * t * t - (t * t * t) / 38710000.0;
    norm(g)
}

pub fn body_from_name(name: &str) -> Option<Body> {
    match name {
        "Sun" => Some(Body::Sun),
        "Moon" => Some(Body::Moon),
        "Mercury" => Some(Body::Mercury),
        "Venus" => Some(Body::Venus),
        "Mars" => Some(Body::Mars),
        "Jupiter" => Some(Body::Jupiter),
        "Saturn" => Some(Body::Saturn),
        "Uranus" => Some(Body::Uranus),
        "Neptune" => Some(Body::Neptune),
        "Pluto" => Some(Body::Pluto),
        "Chiron" => Some(Body::Chiron),
        "True Node" | "North Node" => Some(Body::TrueNode),
        "Mean Node" => Some(Body::MeanNode),
        "Lilith" | "Mean Lilith" | "Black Moon Lilith" => Some(Body::MeanApogee),
        _ => None,
    }
}

pub fn calc_body(eph: &Ephemeris, name: &str, jd_ut: f64) -> Option<PlanetData> {
    let body = body_from_name(name)?;
    let res = eph.calc_ut(jd_ut, body, CalcFlags::SPEED).ok()?;
    let lon = norm(res.data[0]);
    let lat = res.data[1];
    let dist = res.data[2];
    let speed = res.data[3];
    let (ra, dec) = ecliptic_to_equatorial(lon, lat, true_obliquity(jd_ut));
    Some(PlanetData {
        name: name.to_string(),
        longitude: lon,
        latitude: lat,
        distance: dist,
        speed_long: speed,
        right_ascension: norm(ra),
        declination: dec,
    })
}

pub fn create_chart(eph: &Ephemeris, jd_ut: f64, lat: f64, lon: f64, bodies: &[String]) -> Chart {
    let mut planets = BTreeMap::new();
    for name in bodies {
        if let Some(pd) = calc_body(eph, name, jd_ut) {
            planets.insert(name.clone(), pd);
        }
    }
    Chart { jd_ut, lat, lon, planets }
}

pub fn acg_curves(
    ra: f64,
    dec: f64,
    gmst: f64,
    lat_step: f64,
) -> (Vec<(f64, f64)>, Vec<(f64, f64)>) {
    let mut asc_pts = Vec::new();
    let mut dsc_pts = Vec::new();
    if dec.to_radians().cos() == 0.0 {
        return (asc_pts, dsc_pts);
    }
    let tan_dec = dec.to_radians().tan();
    let mut lat: f64 = -90.0;
    while lat <= 90.0 + 1e-9 {
        let arg = (-lat.to_radians().tan() * tan_dec).clamp(-1.0, 1.0);
        let h0 = arg.acos().to_degrees();
        let asc_lon = norm(ra - h0 - gmst);
        let dsc_lon = norm(ra + h0 - gmst);
        asc_pts.push((lat, asc_lon));
        dsc_pts.push((lat, dsc_lon));
        lat += lat_step;
    }
    (asc_pts, dsc_pts)
}

#[derive(Clone)]
pub struct ACGLine {
    pub planet: String,
    pub line_type: String,
    pub longitude: Option<f64>,
    pub points: Option<Vec<(f64, f64)>>,
}

pub fn acg_lines(ra_dec: &BTreeMap<String, (f64, f64)>, gmst: f64, lat_step: f64) -> Vec<ACGLine> {
    let mut lines = Vec::new();
    for (planet, (ra, dec)) in ra_dec {
        let ra = norm(*ra);
        let mc_lon = norm(ra - gmst);
        let ic_lon = norm(mc_lon + 180.0);
        lines.push(ACGLine {
            planet: planet.clone(),
            line_type: "MC".to_string(),
            longitude: Some(mc_lon),
            points: None,
        });
        lines.push(ACGLine {
            planet: planet.clone(),
            line_type: "IC".to_string(),
            longitude: Some(ic_lon),
            points: None,
        });
        let (asc_pts, dsc_pts) = acg_curves(ra, *dec, gmst, lat_step);
        if !asc_pts.is_empty() {
            lines.push(ACGLine {
                planet: planet.clone(),
                line_type: "ASC".to_string(),
                longitude: None,
                points: Some(asc_pts),
            });
        }
        if !dsc_pts.is_empty() {
            lines.push(ACGLine {
                planet: planet.clone(),
                line_type: "DSC".to_string(),
                longitude: None,
                points: Some(dsc_pts),
            });
        }
    }
    lines
}

pub fn acg_from_chart(chart: &Chart, bodies: &[String], lat_step: f64) -> Vec<ACGLine> {
    let mut ra_dec = BTreeMap::new();
    let bs = if bodies.is_empty() {
        chart.planets.keys().cloned().collect::<Vec<_>>()
    } else {
        bodies.to_vec()
    };
    for name in bs {
        if let Some(pd) = chart.planets.get(&name) {
            ra_dec.insert(name, (pd.right_ascension, pd.declination));
        }
    }
    let gmst = gmst_deg(chart.jd_ut);
    acg_lines(&ra_dec, gmst, lat_step)
}

pub fn subplanetary_from_chart(chart: &Chart, bodies: &[String]) -> Vec<(String, String, f64, f64)> {
    let bs = if bodies.is_empty() {
        chart.planets.keys().cloned().collect::<Vec<_>>()
    } else {
        bodies.to_vec()
    };
    let gmst = gmst_deg(chart.jd_ut);
    let mut out = Vec::new();
    for name in bs {
        if let Some(pd) = chart.planets.get(&name) {
            let lon = norm(pd.right_ascension - gmst);
            out.push((name.clone(), "Zenith".to_string(), pd.declination, lon));
            out.push((name.clone(), "Nadir".to_string(), -pd.declination, norm(lon + 180.0)));
        }
    }
    out
}

pub fn local_space_from_chart(chart: &Chart, lat: f64, lon: f64, bodies: &[String]) -> Vec<Value> {
    let bs = if bodies.is_empty() {
        chart.planets.keys().cloned().collect::<Vec<_>>()
    } else {
        bodies.to_vec()
    };
    let gmst = gmst_deg(chart.jd_ut);
    let lst = norm(gmst + lon);
    let lat_r = lat.to_radians();
    let mut out = Vec::new();
    for name in bs {
        if let Some(pd) = chart.planets.get(&name) {
            let h = norm_signed(lst - pd.right_ascension);
            let alt_r = (lat_r.sin() * pd.declination.to_radians().sin()
                + lat_r.cos() * pd.declination.to_radians().cos() * h.to_radians().cos())
            .asin();
            let alt = alt_r.to_degrees();
            let cos_alt = alt_r.cos();
            let az = if cos_alt.abs() < 1e-9 {
                0.0
            } else {
                let sin_az = -pd.declination.to_radians().cos() * h.to_radians().sin() / cos_alt;
                let den = cos_alt * lat_r.cos();
                let cos_az = if den.abs() > 1e-9 {
                    (pd.declination.to_radians().sin() - alt_r.sin() * lat_r.sin()) / den
                } else {
                    0.0
                };
                let sin_az = sin_az.clamp(-1.0, 1.0);
                let cos_az = cos_az.clamp(-1.0, 1.0);
                norm((sin_az).atan2(cos_az).to_degrees())
            };
            out.push(json!({
                "planet": name,
                "azimuth": (az * 100.0).round() / 100.0,
                "altitude": (alt * 1e6).round() / 1e6,
                "is_above": alt > 0.0,
                "color": planet_color(&name),
            }));
        }
    }
    out
}

pub fn norm_lon_line(lon: f64, lat_step: f64) -> Vec<Vec<f64>> {
    let mut coords = Vec::new();
    let mut lat: f64 = -90.0;
    while lat <= 90.0 + 1e-9 {
        coords.push(vec![round6(lon), round6(lat)]);
        lat += lat_step;
    }
    coords
}

fn round6(x: f64) -> f64 {
    (x * 1_000_000.0).round() / 1_000_000.0
}

pub fn split_antimeridian(points: &[(f64, f64)]) -> Vec<Vec<Vec<f64>>> {
    // points are (lat, lon); output segments of [lon, lat]
    let mut segments: Vec<Vec<Vec<f64>>> = Vec::new();
    let mut current: Vec<Vec<f64>> = Vec::new();
    let mut prev_lon: Option<f64> = None;
    for (lat, lon) in points {
        let lon = norm(*lon);
        if let Some(pl) = prev_lon {
            if (lon - pl).abs() > 180.0 {
                if !current.is_empty() {
                    segments.push(current);
                    current = Vec::new();
                }
            }
        }
        current.push(vec![round6(lon), round6(*lat)]);
        prev_lon = Some(lon);
    }
    if !current.is_empty() {
        segments.push(current);
    }
    if segments.is_empty() {
        segments.push(Vec::new());
    }
    segments
}

pub fn generate_acg(
    eph: &Ephemeris,
    iso: &str,
    lat: f64,
    lon: f64,
    bodies: &[String],
    lat_step: f64,
) -> Result<Value, String> {
    let jd_ut = jd_from_iso(iso)?;
    let calc_bodies: Vec<String> = if bodies.is_empty() {
        BODIES.iter().map(|s| s.to_string()).collect()
    } else {
        let mut v = bodies.to_vec();
        if !v.iter().any(|b| b == "Chiron") {
            v.push("Chiron".to_string());
        }
        v
    };
    let minor: std::collections::HashSet<String> =
        calc_bodies.iter().filter(|b| !BODIES.contains(&b.as_str())).cloned().collect();
    let planet_bodies: Vec<String> = calc_bodies.iter().filter(|b| !minor.contains(*b)).cloned().collect();

    let chart = create_chart(eph, jd_ut, lat, lon, &calc_bodies);

    let acg_main = acg_from_chart(&chart, &calc_bodies, lat_step);

    // node lines
    let mut node_lines = Vec::new();
    // True Node ACG
    if let Some(nd) = calc_body(eph, "True Node", jd_ut) {
        let obliq = true_obliquity(jd_ut);
        let (ra, dec) = ecliptic_to_equatorial(nd.longitude, 0.0, obliq);
        let gmst = gmst_deg(jd_ut);
        let mut m = BTreeMap::new();
        m.insert("True Node".to_string(), (ra, dec));
        node_lines = acg_lines(&m, gmst, lat_step);
    }
    // Lilith
    let mut lilith_lines = Vec::new();
    if let Some(ld) = calc_body(eph, "Lilith", jd_ut) {
        let obliq = true_obliquity(jd_ut);
        let (ra, dec) = ecliptic_to_equatorial(ld.longitude, 0.0, obliq);
        let gmst = gmst_deg(jd_ut);
        let mut m = BTreeMap::new();
        m.insert("Lilith".to_string(), (ra, dec));
        lilith_lines = acg_lines(&m, gmst, lat_step);
    }

    let mut all_acg = acg_main;
    all_acg.extend(node_lines);
    all_acg.extend(lilith_lines);

    // Build lines_out and polylines
    let mut lines_out: Vec<Value> = Vec::new();
    let mut polylines: BTreeMap<(String, String), Vec<Vec<f64>>> = BTreeMap::new();

    for line in &all_acg {
        let color = planet_color(&line.planet);
        if line.line_type == "MC" || line.line_type == "IC" {
            let lonv = line.longitude.unwrap_or(0.0);
            let coords = norm_lon_line(lonv, lat_step);
            polylines.insert((line.planet.clone(), line.line_type.clone()), coords.clone());
            lines_out.push(json!({
                "id": format!("{}-{}", line.planet.to_lowercase().replace(' ', "-"), line.line_type.to_lowercase()),
                "planet": line.planet,
                "angle": line.line_type,
                "color": color,
                "geometry": {"type": "LineString", "coordinates": coords},
            }));
        } else {
            let pts = line.points.clone().unwrap_or_default();
            let full: Vec<Vec<f64>> = pts
                .iter()
                .map(|(latv, lonv)| vec![round6(norm(*lonv)), round6(*latv)])
                .collect();
            polylines.insert((line.planet.clone(), line.line_type.clone()), full);
            let segments = split_antimeridian(&pts);
            for (idx, seg) in segments.iter().enumerate() {
                let id = if segments.len() > 1 {
                    format!(
                        "{}-{}-{}",
                        line.planet.to_lowercase().replace(' ', "-"),
                        line.line_type.to_lowercase(),
                        idx
                    )
                } else {
                    format!(
                        "{}-{}",
                        line.planet.to_lowercase().replace(' ', "-"),
                        line.line_type.to_lowercase()
                    )
                };
                lines_out.push(json!({
                    "id": id,
                    "planet": line.planet,
                    "angle": line.line_type,
                    "color": color,
                    "geometry": {"type": "LineString", "coordinates": seg},
                }));
            }
        }
    }

    // subplanetary
    let subpoints = subplanetary_from_chart(&chart, &planet_bodies);
    let mut sub_out: Vec<Value> = Vec::new();
    for (planet, ptype, slat, slon) in subpoints {
        sub_out.push(json!({
            "planet": planet,
            "type": ptype,
            "latitude": (slat * 1e6).round() / 1e6,
            "longitude": (slon * 1e6).round() / 1e6,
            "color": planet_color(&planet),
        }));
    }

    // local space
    let ls = local_space_from_chart(&chart, lat, lon, &planet_bodies);
    let ls_out: Vec<Value> = ls
        .into_iter()
        .map(|mut v| {
            // already json objects
            v
        })
        .collect();

    // parans
    let parans = natal_parans(eph, &chart, &planet_bodies, jd_ut, lat, lon);
    let mut paran_out: Vec<Value> = Vec::new();
    for p in parans {
        let a = polylines.get(&(p.body1.clone(), circle_to_angle(&p.circle1)));
        let b = polylines.get(&(p.body2.clone(), circle_to_angle(&p.circle2)));
        let pt = if let (Some(a), Some(b)) = (a, b) {
            intersect_lines(a, b)
        } else {
            None
        };
        let (plx, ply) = if let Some(pt) = pt {
            (pt.0, pt.1)
        } else {
            (lon, lat)
        };
        paran_out.push(json!({
            "planet_a": p.body1,
            "circle_a": p.circle1,
            "planet_b": p.body2,
            "circle_b": p.circle2,
            "orb_min": (p.orb_min * 100.0).round() / 100.0,
            "latitude": (ply * 1e6).round() / 1e6,
            "longitude": (plx * 1e6).round() / 1e6,
        }));
    }

    Ok(json!({
        "lines": lines_out,
        "subplanetary_points": sub_out,
        "local_space": ls_out,
        "parans": paran_out,
    }))
}

pub fn circle_to_angle(c: &str) -> String {
    let c = c.to_lowercase();
    if c.contains("ris") {
        "ASC".to_string()
    } else if c.contains("set") {
        "DSC".to_string()
    } else if c.contains("culm") || c.contains("mc") {
        "MC".to_string()
    } else if c.contains("anti") || c.contains("ic") {
        "IC".to_string()
    } else {
        c.to_uppercase()
    }
}

#[derive(Clone)]
pub struct Paran {
    pub body1: String,
    pub circle1: String,
    pub body2: String,
    pub circle2: String,
    pub orb_min: f64,
}

pub fn natal_parans(eph: &Ephemeris, chart: &Chart, bodies: &[String], jd_ut: f64, lat: f64, lon: f64) -> Vec<Paran> {
    let bs = bodies.to_vec();
    let half_span = 0.5;
    let step = 2.0 / 24.0 / 60.0;
    let mut t = jd_ut - half_span;
    let mut seen: std::collections::HashSet<(String, String, String, String)> = std::collections::HashSet::new();
    let mut out = Vec::new();
    while t <= jd_ut + half_span + 1e-9 {
        let on_angle = scan_angles(eph, t, lat, lon, &bs);
        let mut names: Vec<String> = on_angle.iter().filter(|(_, c)| c.is_some()).map(|(n, _)| n.clone()).collect();
        names.sort();
        for i in 0..names.len() {
            for j in (i + 1)..names.len() {
                let a = &names[i];
                let b = &names[j];
                let ca = on_angle.get(a).unwrap().clone().unwrap();
                let cb = on_angle.get(b).unwrap().clone().unwrap();
                let mut key = vec![a.clone(), ca.clone(), b.clone(), cb.clone()];
                key.sort();
                let keyt = (key[0].clone(), key[1].clone(), key[2].clone(), key[3].clone());
                if seen.contains(&keyt) {
                    continue;
                }
                seen.insert(keyt);
                out.push(Paran {
                    body1: a.clone(),
                    circle1: ca,
                    body2: b.clone(),
                    circle2: cb,
                    orb_min: 0.0,
                });
                if out.len() >= 200 {
                    return out;
                }
            }
        }
        t += step;
    }
    out
}

pub fn scan_angles(eph: &Ephemeris, t: f64, lat: f64, lon: f64, bodies: &[String]) -> BTreeMap<String, Option<String>> {
    let gmst = gmst_deg(t);
    let lst = norm(gmst + lon);
    let mut out = BTreeMap::new();
    for name in bodies {
        let pd = calc_body(eph, name, t);
        let pd = match pd {
            Some(p) => p,
            None => {
                out.insert(name.clone(), None);
                continue;
            }
        };
        let dec = pd.declination;
        let h = norm_signed(lst - pd.right_ascension);
        if dec.to_radians().cos() == 0.0 {
            out.insert(name.clone(), None);
            continue;
        }
        let tan_dec = dec.to_radians().tan();
        let arg = (-lat.to_radians().tan() * tan_dec).clamp(-1.0, 1.0);
        let h0 = arg.acos().to_degrees();
        let dist_mc = norm_signed(h).abs();
        let dist_ic = norm_signed(h - 180.0).abs();
        let dist_asc = norm_signed(h + h0).abs();
        let dist_dsc = norm_signed(h - h0).abs();
        let candidates = [("MC", dist_mc), ("IC", dist_ic), ("ASC", dist_asc), ("DSC", dist_dsc)];
        let best = candidates.iter().min_by(|a, b| a.1.partial_cmp(&b.1).unwrap()).unwrap();
        let chosen = if best.1 <= 3.0 { Some(best.0.to_string()) } else { None };
        out.insert(name.clone(), chosen);
    }
    out
}

pub fn intersect_lines(a: &[Vec<f64>], b: &[Vec<f64>]) -> Option<(f64, f64)> {
    // a, b are list of [lon, lat]
    if a.is_empty() || b.is_empty() {
        return None;
    }
    // Use first point longitude as meridian
    let mlon = a[0][0];
    for i in 0..b.len().saturating_sub(1) {
        let lon1 = b[i][0];
        let lat1 = b[i][1];
        let lon2 = b[i + 1][0];
        let lat2 = b[i + 1][1];
        if (lon2 - lon1).abs() > 180.0 {
            continue;
        }
        let d1 = lon1 - mlon;
        let d2 = lon2 - mlon;
        if d1 == 0.0 {
            let t = 0.0;
            let lat = lat1 + t * (lat2 - lat1);
            return Some((mlon, lat));
        }
        if d1 * d2 <= 0.0 && d1 != d2 {
            let t = d1 / (d1 - d2);
            let lat = lat1 + t * (lat2 - lat1);
            return Some((mlon, lat));
        }
    }
    None
}

pub fn generate_geodetic(eph: &Ephemeris, iso: &str, _lat: f64, _lon: f64) -> Result<Value, String> {
    let jd_ut = jd_from_iso(iso)?;
    let mut chart = create_chart(eph, jd_ut, 0.0, 0.0, &BODIES.iter().map(|s| s.to_string()).collect::<Vec<_>>());
    // houses not needed
    let mut longitudes: BTreeMap<String, f64> = BTreeMap::new();
    for (name, pd) in &chart.planets {
        longitudes.insert(name.clone(), pd.longitude);
    }
    let mut lines: Vec<Value> = Vec::new();
    for i in 0..12 {
        let lon = i as f64 * 30.0;
        lines.push(json!({
            "id": format!("sign-{}-geo", i*30),
            "planet": format!("Sign {}°", i*30),
            "angle": "GEO",
            "color": "#6ea8ff",
            "geometry": {"type": "LineString", "coordinates": norm_lon_line(lon, 1.0)},
        }));
    }
    for (name, lon) in &longitudes {
        lines.push(json!({
            "id": format!("{}-geo", name.to_lowercase()),
            "planet": name,
            "angle": "GEO",
            "color": planet_color(name),
            "geometry": {"type": "LineString", "coordinates": norm_lon_line(*lon, 1.0)},
        }));
    }
    let _ = chart;
    Ok(json!({"lines": lines}))
}
