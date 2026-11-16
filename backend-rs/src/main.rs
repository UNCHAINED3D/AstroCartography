mod astro;
mod cities;
mod handlers;
mod models;

use axum::{
    routing::{get, post},
    Router,
};
use handlers::{AppState, SharedState};
use std::net::SocketAddr;
use std::sync::Arc;
use swisseph::Ephemeris;
use swisseph::EphemerisConfig;
use swisseph::types::EphemerisSource;
use tower_http::cors::{Any, CorsLayer};
use tower_http::services::ServeDir;
use tower_http::compression::CompressionLayer;

#[tokio::main]
async fn main() {
    tracing_subscriber::fmt::init();

    // Configure ephemeris to use bundled .se1 files (Moshier fallback if absent).
    let ephe_path = std::path::PathBuf::from("../backend/ephe");
    let config = if ephe_path.exists() {
        EphemerisConfig {
            ephemeris_source: swisseph::types::EphemerisSource::Swiss,
            ephe_path: Some(ephe_path),
            ..Default::default()
        }
    } else {
        EphemerisConfig::default()
    };
    let eph = Ephemeris::new(config).expect("failed to init ephemeris");

    let state: SharedState = Arc::new(AppState { eph });

    let cors = CorsLayer::new()
        .allow_origin(Any)
        .allow_methods(Any)
        .allow_headers(Any);

    let mut app = Router::new()
        .route("/healthz", get(handlers::healthz))
        .route("/api/astrocartography", post(handlers::astrocartography))
        .route("/api/transit-acg", post(handlers::transit_acg))
        .route("/api/progressed-acg", post(handlers::progressed_acg))
        .route("/api/geodetic", post(handlers::geodetic))
        .route("/api/fixed-stars", post(handlers::fixed_stars))
        .route("/api/midpoints", post(handlers::midpoints))
        .route("/api/crossings", post(handlers::crossings))
        .route("/api/top-cities", post(handlers::top_cities))
        .with_state(state)
        .layer(cors)
        .layer(CompressionLayer::new());

    // Serve frontend if built.
    let dist = std::path::Path::new("../frontend/dist");
    if dist.exists() {
        let serve = ServeDir::new(dist);
        app = app.fallback_service(serve);
    }

    let port: u16 = std::env::var("PORT").ok().and_then(|p| p.parse().ok()).unwrap_or(8000);
    let addr = SocketAddr::from(([0, 0, 0, 0], port));
    println!("Astrocartography Rust backend listening on {}", addr);
    let listener = tokio::net::TcpListener::bind(addr).await.unwrap();
    axum::serve(listener, app).await.unwrap();
}
