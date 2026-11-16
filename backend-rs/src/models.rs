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
fn default_house_system() -> String {
    "P".to_string()
}
