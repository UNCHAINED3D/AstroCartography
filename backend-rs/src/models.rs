use serde::{Deserialize, Serialize};

#[derive(Debug, Clone, Deserialize, Serialize)]
pub struct Birth {
    pub datetime: String,
    pub latitude: f64,
    pub longitude: f64,
}

#[derive(Debug, Deserialize)]
pub struct ACGRequest {
    pub birth: Birth,
    #[serde(default)]
    pub bodies: Option<Vec<String>>,
    #[serde(default = "default_lat_step")]
    pub lat_step: f64,
}

#[derive(Debug, Deserialize)]
pub struct TransitACGRequest {
    pub birth: Birth,
    pub transit_iso: String,
    #[serde(default)]
    pub bodies: Option<Vec<String>>,
    #[serde(default = "default_lat_step")]
    pub lat_step: f64,
}

#[derive(Debug, Deserialize)]
pub struct ProgressedACGRequest {
    pub birth: Birth,
    pub age_years: f64,
    #[serde(default)]
    pub bodies: Option<Vec<String>>,
    #[serde(default = "default_lat_step")]
    pub lat_step: f64,
}

#[derive(Debug, Deserialize)]
pub struct GeodeticRequest {
    pub birth: Birth,
}

#[derive(Debug, Deserialize)]
pub struct FixedStarsRequest {
    pub birth: Birth,
    #[serde(default)]
    pub names: Option<Vec<String>>,
}

#[derive(Debug, Deserialize)]
pub struct MidpointsRequest {
    pub birth: Birth,
    #[serde(default)]
    pub pairs: Option<Vec<Vec<String>>>,
}

#[derive(Debug, Deserialize)]
pub struct CrossingsRequest {
    pub birth: Birth,
    #[serde(default)]
    pub bodies: Option<Vec<String>>,
}

#[derive(Debug, Deserialize)]
pub struct LocationAnalysisRequest {
    pub birth: Birth,
    pub location: std::collections::HashMap<String, f64>,
    #[serde(default)]
    pub bodies: Option<Vec<String>>,
    #[serde(default = "default_house_system")]
    pub house_system: String,
}

fn default_lat_step() -> f64 {
    1.0
}
#[derive(Debug, Deserialize)]
pub struct TopCitiesRequest {
    pub birth: Birth,
    #[serde(default = "default_focus")]
    pub focus: String,
    #[serde(default = "default_limit")]
    pub limit: i64,
    #[serde(default)]
    pub weights: Option<std::collections::HashMap<String, f64>>,
    #[serde(default = "default_true")]
    pub include_breakdown: bool,
    #[serde(default)]
    pub second_birth: Option<Birth>,
    #[serde(default)]
    pub births: Option<Vec<Birth>>,
    #[serde(default)]
    pub region: Option<String>,
    #[serde(default)]
    pub center_lat: Option<f64>,
    #[serde(default)]
    pub center_lon: Option<f64>,
    #[serde(default)]
    pub radius_km: Option<f64>,
    #[serde(default)]
    pub bbox: Option<Vec<f64>>,
    #[serde(default)]
    pub max_distance_from_birth_km: Option<f64>,
    #[serde(default)]
    pub grid: bool,
}

fn default_house_system() -> String {
    "P".to_string()
}
fn default_focus() -> String {
    "all".to_string()
}
fn default_limit() -> i64 {
    15
}
fn default_true() -> bool {
    true
}
