import type { ACGRequest, ACGResponse, BirthEntry, LocationAnalysis, TopCity, OverlayResponse, TransitRequest, ProgressedRequest, GeodeticRequest, FixedStarsRequest, MidpointsRequest, CrossingResponse, TravelDay, TravelTimingRequest, GroupTravelDay, TripPlanRequest, TripPlanResponse } from './types';

const API_BASE = '/api';

export async function fetchACG(req: ACGRequest): Promise<ACGResponse> {
  const res = await fetch(`${API_BASE}/astrocartography`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ ...req, lat_step: req.lat_step ?? 1.0 }),
  });
  if (!res.ok) {
    let detail = `HTTP ${res.status}`;
    try {
      const data = await res.json();
      if (data?.detail) detail = data.detail;
    } catch {
      /* ignore */
    }
    throw new Error(detail);
  }
  return res.json();
}

export async function fetchBirths(): Promise<BirthEntry[]> {
  const res = await fetch(`${API_BASE}/births`);
  if (!res.ok) throw new Error(`HTTP ${res.status}`);
  return res.json();
}

export async function saveBirth(entry: Omit<BirthEntry, 'id' | 'created_at'>): Promise<BirthEntry> {
  const res = await fetch(`${API_BASE}/births`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(entry),
  });
  if (!res.ok) {
    let detail = `HTTP ${res.status}`;
    try {
      const data = await res.json();
      if (data?.detail) detail = data.detail;
    } catch {
      /* ignore */
    }
    throw new Error(detail);
  }
  return res.json();
}

export async function deleteBirth(id: number): Promise<void> {
  const res = await fetch(`${API_BASE}/births/${id}`, { method: 'DELETE' });
  if (!res.ok) throw new Error(`HTTP ${res.status}`);
}

export async function fetchAnalysis(
  birth: { datetime: string; latitude: number; longitude: number },
  location: { latitude: number; longitude: number },
  bodies?: string[],
): Promise<LocationAnalysis> {
  const res = await fetch(`${API_BASE}/location-analysis`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ birth, location, bodies }),
  });
  if (!res.ok) {
    let detail = `HTTP ${res.status}`;
    try {
      const data = await res.json();
      if (data?.detail) detail = data.detail;
    } catch {
      /* ignore */
    }
    throw new Error(detail);
  }
  return res.json();
}

export async function fetchTopCities(
  birth: { datetime: string; latitude: number; longitude: number },
  focus: string = 'all',
  limit: number = 15,
  weights?: Record<string, number>,
  secondBirth?: { datetime: string; latitude: number; longitude: number },
  births?: { datetime: string; latitude: number; longitude: number }[],
  region?: string,
  center?: { lat: number; lon: number; radius_km: number },
  bbox?: [[number, number], [number, number]],
  maxDistanceKm?: number,
  grid?: boolean,
): Promise<TopCity[]> {
  const res = await fetch(`${API_BASE}/top-cities`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      birth, focus, limit, weights, second_birth: secondBirth, births,
      region, center_lat: center?.lat, center_lon: center?.lon, radius_km: center?.radius_km,
      bbox, max_distance_from_birth_km: maxDistanceKm, grid,
    }),
  });
  if (!res.ok) {
    let detail = `HTTP ${res.status}`;
    try {
      const data = await res.json();
      if (data?.detail) detail = data.detail;
    } catch {
      /* ignore */
    }
    throw new Error(detail);
  }
  return res.json();
}

async function postOverlay(url: string, body: unknown): Promise<OverlayResponse> {
  const res = await fetch(`${API_BASE}${url}`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  });
  if (!res.ok) {
    let detail = `HTTP ${res.status}`;
    try {
      const data = await res.json();
      if (data?.detail) detail = data.detail;
    } catch {
      /* ignore */
    }
    throw new Error(detail);
  }
  return res.json();
}

export async function fetchTransitACG(req: TransitRequest): Promise<OverlayResponse> {
  return postOverlay('/transit-acg', req);
}
export async function fetchProgressedACG(req: ProgressedRequest): Promise<OverlayResponse> {
  return postOverlay('/progressed-acg', req);
}
export async function fetchGeodetic(req: GeodeticRequest): Promise<OverlayResponse> {
  return postOverlay('/geodetic', req);
}
export async function fetchFixedStars(req: FixedStarsRequest): Promise<OverlayResponse> {
  return postOverlay('/fixed-stars', req);
}
export async function fetchMidpoints(req: MidpointsRequest): Promise<OverlayResponse> {
  return postOverlay('/midpoints', req);
}

export async function fetchCrossings(req: { birth: { datetime: string; latitude: number; longitude: number }; bodies?: string[] }): Promise<CrossingResponse> {
  const res = await fetch(`${API_BASE}/crossings`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(req),
  });
  if (!res.ok) throw new Error(`HTTP ${res.status}`);
  return res.json();
}

export async function fetchSolarReturn(req: { birth: { datetime: string; latitude: number; longitude: number }; year: number; bodies?: string[]; lat_step?: number }): Promise<OverlayResponse> {
  return postOverlay('/solar-return', req);
}

export async function fetchLunarReturn(req: { birth: { datetime: string; latitude: number; longitude: number }; year: number; month?: number; bodies?: string[]; lat_step?: number }): Promise<OverlayResponse> {
  return postOverlay('/lunar-return', req);
}

export async function fetchTravelTiming(req: TravelTimingRequest): Promise<TravelDay[]> {
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), 60000);
  try {
    const res = await fetch(`${API_BASE}/travel-timing`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(req),
      signal: controller.signal,
    });
    if (!res.ok) {
      let detail = `HTTP ${res.status}`;
      try {
        const data = await res.json();
        if (data?.detail) detail = data.detail;
      } catch { /* ignore */ }
      throw new Error(detail);
    }
    return res.json();
  } catch (err) {
    if ((err as any)?.name === 'AbortError') throw new Error('Travel timing timed out (60s).');
    throw err;
  } finally {
    clearTimeout(timer);
  }
}

export async function fetchGroupTravelTiming(req: {
  births: { datetime: string; latitude: number; longitude: number }[];
  dest_lat: number;
  dest_lon: number;
  start_date: string;
  days: number;
  hour_step?: number;
  stay_days?: number;
  include_warnings?: boolean;
  combine?: string;
}): Promise<GroupTravelDay[]> {
  const res = await fetch(`${API_BASE}/group-travel-timing`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(req),
  });
  if (!res.ok) throw new Error(`HTTP ${res.status}`);
  return res.json();
}

export async function fetchTripPlan(req: TripPlanRequest): Promise<TripPlanResponse> {
  const res = await fetch(`${API_BASE}/trip-plan`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(req),
  });
  if (!res.ok) throw new Error(`HTTP ${res.status}`);
  return res.json();
}


