export interface ACGLine {
  id: string;
  planet: string;
  angle: string; // "MC" | "IC" | "ASC" | "DSC"
  color: string;
  geometry: {
    type: string; // "LineString"
    coordinates: number[][]; // [longitude, latitude]
  };
}

export interface SubPoint {
  planet: string;
  type: string; // "Zenith" | "Nadir"
  latitude: number;
  longitude: number;
  color: string;
}

export interface LocalSpaceRay {
  planet: string;
  azimuth: number;
  altitude: number;
  is_above: boolean;
  color: string;
  geometry: {
    type: string;
    coordinates: number[][]; // [longitude, latitude]
  };
}

export interface Paran {
  planet_a: string;
  circle_a: string;
  planet_b: string;
  circle_b: string;
  orb_min: number;
  latitude: number;
  longitude: number;
  distance_km?: number;
}

export interface ACGResponse {
  lines: ACGLine[];
  subplanetary_points: SubPoint[];
  local_space: LocalSpaceRay[];
  parans: Paran[];
}

export interface Birth {
  datetime: string; // ISO-8601 with UTC offset
  latitude: number;
  longitude: number;
}

export interface ACGRequest {
  birth: Birth;
  lat_step?: number;
  bodies?: string[];
}

// ---- Advanced overlay requests (transit / progressed / geodetic / stars / midpoints) ----
export interface TransitRequest {
  birth: Birth;
  transit_iso: string;
  bodies?: string[];
  lat_step?: number;
}
export interface ProgressedRequest {
  birth: Birth;
  age_years: number;
  bodies?: string[];
  lat_step?: number;
}
export interface GeodeticRequest {
  birth: Birth;
}
export interface FixedStarsRequest {
  birth: Birth;
  names?: string[];
}
export interface MidpointsRequest {
  birth: Birth;
  pairs?: string[][];
}

// All overlay endpoints return the same lightweight shape: just their lines.
export interface OverlayResponse {
  lines: ACGLine[];
}

export interface DomainScores {
  Love: number;
  Career: number;
  Home: number;
  Growth: number;
  Peace: number;
}

export interface BirthEntry {
  id: number;
  name: string;
  datetime: string; // ISO-8601 with UTC offset
  latitude: number;
  longitude: number;
  note: string | null;
  created_at: string;
}

// ---- Location analysis (right-side panel) ----

export interface AngleInfo {
  sign: string;
  longitude: number;
}

export interface RelocPlanet {
  name: string;
  longitude: number;
  sign: string;
  house: number;
  notable: boolean;
}

export interface NearestLine {
  planet: string;
  angle: string;
  distance_km: number;
  strength: string;
  color: string;
}

export interface RelocationBlock {
  angles: {
    asc: AngleInfo;
    mc: AngleInfo;
    dsc: AngleInfo;
    ic: AngleInfo;
  };
  planets: RelocPlanet[];
  summary: string;
}

export interface HouseRegion {
  house: number;
  theme: string;
  sentence: string;
}

export interface AnalysisInterpretations {
  relocation: string;
  nearest_acg: string[];
  parans: string[];
  overall: string;
}

export interface LocationAnalysis {
  location: { latitude: number; longitude: number };
  relocation: RelocationBlock;
  nearest_acg: NearestLine[];
  local_space: LocalSpaceRay[];
  parans: Paran[];
  crossings?: Crossing[];
  house_region: HouseRegion;
  domain_scores: DomainScores;
  interpretations: AnalysisInterpretations;
}

export interface PrimaryInfluence {
  planet: string;
  angle: string;
  color: string;
  distance_km: number;
  score_contribution: number;
}

export interface TopCity {
  name: string;
  country: string;
  region: string;
  latitude: number;
  longitude: number;
  overall_score: number;
  scores: {
    love: number;
    career: number;
    peace: number;
    growth: number;
  };
  primary_influences: PrimaryInfluence[];
  summary: string;
  score_breakdown?: {
    acg: number;
    houses: number;
    parans: number;
  };
  house_placements?: {
    planet: string;
    house: number;
    domain: string;
    points: number;
  }[];
}

export interface Crossing {
  type: 'line-cross' | 'paran';
  planet_a: string;
  angle_a: string;
  planet_b: string;
  angle_b: string;
  latitude: number;
  longitude: number;
  interpretation: string;
  color_a?: string;
  color_b?: string;
}

export interface CrossingResponse {
  crossings: Crossing[];
}

export interface TravelDay {
  date: string;
  score: number;
  influences: string[];
  best_hour?: number;
  hourly?: { hour: number; score: number }[];
  arrival_score?: number;
  stay_score?: number;
  departure_score?: number | null;
  warnings?: string[];
}

export interface TravelTimingRequest {
  birth: { datetime: string; latitude: number; longitude: number };
  dest_lat: number;
  dest_lon: number;
  start_date: string;
  days: number;
  hour_step?: number;
  stay_days?: number;
  include_warnings?: boolean;
}

export interface GroupTravelDay {
  date: string;
  combined_score: number;
  per_person: { index: number; score: number; influences: string[]; warnings: string[] }[];
}

export interface TripStop {
  latitude: number;
  longitude: number;
  name?: string;
  min_days?: number;
  max_days?: number;
  flex_start: string;
  flex_end: string;
}

export interface TripPlanRequest {
  birth: { datetime: string; latitude: number; longitude: number };
  stops: TripStop[];
  total_days?: number;
  hour_step?: number;
}

export interface TripPlanResponse {
  total_score: number;
  itinerary: {
    name: string;
    latitude: number;
    longitude: number;
    arrival_date: string;
    length_days: number;
    score: number;
    daily: { date: string; score: number }[];
  }[];
}

export type TravelTimingDay = TravelDay;

export interface SolarReturnRequest {
  birth: { datetime: string; latitude: number; longitude: number };
  year: number;
}

export interface LunarReturnRequest {
  birth: { datetime: string; latitude: number; longitude: number };
  year: number;
  month?: number;
}


