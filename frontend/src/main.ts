import './style.css';
import { fetchACG, fetchBirths, saveBirth, deleteBirth, fetchAnalysis, fetchTopCities, fetchTransitACG, fetchProgressedACG, fetchGeodetic, fetchFixedStars, fetchMidpoints, fetchCrossings, fetchSolarReturn, fetchLunarReturn, fetchTravelTiming, fetchGroupTravelTiming, fetchTripPlan } from './api';
import { initGlobe } from './globe';
import { initMap2D } from './map2d';
import type { HoverInfo, ClickInfo } from './globe';
import { renderReport, renderHoverPreview, clearReport, renderTopCitiesCards, renderCitiesSkeleton, renderTravelDays, renderTravelSkeleton, scoreColor } from './panel';
import type { ACGResponse, BirthEntry, TopCity } from './types';
import {
  acgToGeoJSON,
  acgToKML,
  downloadText,
  downloadDataURL,
  buildShareUrl,
  copyToClipboard,
  decodeShareState,
} from './export';
import type { ShareState } from './export';

interface City {
  name: string;
  lat: number;
  lng: number;
  pop?: number;
}

// Populated from /labels.json (Natural Earth cities) for the autocomplete.
let CITY_INDEX: City[] = [];

const $ = (id: string) => document.getElementById(id) as HTMLElement;

const globe = initGlobe($('globe'));
const map2d = initMap2D($('map2d'));

let is2DMode = false;
let currentGoalFocus = 'all';

// Sidebar Panel Collapse Handler
const togglePanelBtn = $('togglePanelBtn');
const panelShell = document.querySelector('.panel-shell');
togglePanelBtn?.addEventListener('click', () => {
  panelShell?.classList.toggle('collapsed');
});

// View Mode Toggle Handler
const viewModeBtn = $('ctrlViewMode');
const viewModeLabel = $('viewModeLabel');
const globeDiv = $('globe');
const map2dDiv = $('map2d');

viewModeBtn?.addEventListener('click', () => {
  is2DMode = !is2DMode;
  if (is2DMode) {
    globeDiv.classList.add('hidden');
    map2dDiv.classList.remove('hidden');
    if (viewModeLabel) viewModeLabel.textContent = '3D Globe';
    map2d.invalidateSize();
  } else {
    map2dDiv.classList.add('hidden');
    globeDiv.classList.remove('hidden');
    if (viewModeLabel) viewModeLabel.textContent = '2D Map';
  }
});

// Pin mode toggle
let pinMode = false;
const ctrlPin = $('ctrlPin') as HTMLButtonElement | null;
ctrlPin?.addEventListener('click', () => {
  pinMode = !pinMode;
  ctrlPin.classList.toggle('pin-active', pinMode);
  if (ctrlPin) ctrlPin.setAttribute('aria-pressed', String(pinMode));
  globe.setCursor(pinMode ? 'crosshair' : 'grab');
  map2d.setCursor(pinMode ? 'crosshair' : '');
  map2d.setPinMode(pinMode);
  globe.setPinMode(pinMode);
});

// Crosshair toggle
const ctrlCrosshair = $('ctrlCrosshair') as HTMLButtonElement | null;
ctrlCrosshair?.addEventListener('click', () => {
  const next = !(ctrlCrosshair.getAttribute('aria-pressed') === 'true');
  ctrlCrosshair.setAttribute('aria-pressed', String(next));
  globe.setCrosshairVisible(next);
});

// Life Goal Preset Handlers
const goalBtns = document.querySelectorAll('#goalPresets .goal-btn');
const citiesGoalBtns = document.querySelectorAll('#citiesGoalStrip .cg-btn');

function setGoalFocus(goal: string) {
  currentGoalFocus = goal;
  // Sync left sidebar buttons
  goalBtns.forEach((b) => b.classList.toggle('active', b.getAttribute('data-goal') === goal));
  // Sync in-tab buttons
  citiesGoalBtns.forEach((b) => b.classList.toggle('active', b.getAttribute('data-goal') === goal));
  applyGoalFilter(goal);
  void loadTopCities();
}

goalBtns.forEach((btn) => {
  btn.addEventListener('click', () => setGoalFocus(btn.getAttribute('data-goal') || 'all'));
});

citiesGoalBtns.forEach((btn) => {
  btn.addEventListener('click', () => setGoalFocus(btn.getAttribute('data-goal') || 'all'));
});

// ---- City goal-weight sliders -------------------------------------------
// When the user has moved any slider, the per-domain weights are sent with the
// top-cities request and take priority over the focus preset on the backend.
let weightsDirty = false;

function cityWeights(): Record<string, number> {
  const map: Record<string, string> = {
    wLove: 'love', wCareer: 'career', wHome: 'home', wPeace: 'peace', wGrowth: 'growth',
  };
  const out: Record<string, number> = {};
  for (const [id, domain] of Object.entries(map)) {
    const inp = $(id) as HTMLInputElement | null;
    if (inp) out[domain] = Number(inp.value);
  }
  return out;
}

document.querySelectorAll<HTMLInputElement>('.city-weight-row input[type="range"]').forEach((inp) => {
  inp.addEventListener('change', () => {
    weightsDirty = true;
    void loadTopCities();
  });
});

$('regionSelect')?.addEventListener('change', () => { void loadTopCities(); });

$('regionSelect')?.addEventListener('change', () => { void loadTopCities(); });

function applyGoalFilter(goal: string) {
  const goalPlanets: Record<string, string[]> = {
    love: ['Venus', 'Moon', 'Sun', 'Jupiter'],
    career: ['Sun', 'Mars', 'Jupiter', 'Saturn', 'Mercury'],
    wealth: ['Jupiter', 'Venus', 'Sun', 'Pluto'],
    peace: ['Moon', 'Neptune', 'Venus', 'Jupiter', 'Chiron'],
    growth: ['Jupiter', 'Sun', 'Uranus', 'Mercury'],
    all: [],
  };

  const activePlanets = goalPlanets[goal] || [];
  const allCheckboxes = document.querySelectorAll<HTMLInputElement>('#planetToggles input');
  allCheckboxes.forEach((cb) => {
    const planet = cb.dataset.planet;
    if (planet) {
      const show = activePlanets.length === 0 || activePlanets.includes(planet);
      cb.checked = show;
      globe.setPlanetVisible(planet, show);
      map2d.setPlanetVisible(planet, show);
    }
  });
}

// Side Panel Tabs Handler
const tabIntel = $('tabIntel');
const tabTopCities = $('tabTopCities');
const tabTravel = $('tabTravel');
const tabContentIntel = $('tabContentIntel');
const tabContentTopCities = $('tabContentTopCities');
const tabContentTravel = $('tabContentTravel');

function switchTab(tab: 'intel' | 'cities' | 'travel'): void {
  tabIntel?.classList.toggle('active', tab === 'intel');
  tabTopCities?.classList.toggle('active', tab === 'cities');
  tabTravel?.classList.toggle('active', tab === 'travel');
  tabContentIntel?.classList.toggle('active', tab === 'intel');
  tabContentTopCities?.classList.toggle('active', tab === 'cities');
  tabContentTravel?.classList.toggle('active', tab === 'travel');
}

tabIntel?.addEventListener('click', () => switchTab('intel'));
tabTopCities?.addEventListener('click', () => { switchTab('cities'); void loadTopCities(); });
tabTravel?.addEventListener('click', () => switchTab('travel'));

// ---- Travel timing (electional) -------------------------------------------
function activePin(): Pin | null {
  if (!currentPinId) return null;
  return pins.find((p) => p.id === currentPinId) ?? null;
}

$('loadTravelTiming')?.addEventListener('click', async () => {
  const b = currentBirth();
  if (!b) { setStatus('Enter a birth date and location first.', true); return; }
  const pin = activePin();
  if (!pin) { setStatus('Pin a destination on the globe first, then recalculate.', true); return; }
  const startDate = ($('travelStart') as HTMLInputElement).value;
  if (!startDate) { setStatus('Pick a start date for the travel window.', true); return; }
  const days = parseInt(($('travelDays') as HTMLInputElement)?.value || '30') || 30;
  const useGroup = ($('useGroupTiming') as HTMLInputElement | null)?.checked;
  const companionSel = $('companionSelect') as HTMLSelectElement | null;
  const companionIds = companionSel ? Array.from(companionSel.selectedOptions).map((o) => o.value) : [];
  const companions = companionIds
    .map((id) => savedBirthsCache.find((e) => String(e.id) === id))
    .filter(Boolean) as BirthEntry[];
  try {
    setStatus('Calculating travel window…');
    renderTravelSkeleton();
    const start_iso = `${startDate}T12:00:00+00:00`;
    if (useGroup && companions.length) {
      const births = [
        { datetime: b.datetime, latitude: b.latitude, longitude: b.longitude },
        ...companions.map((c) => ({ datetime: c.datetime, latitude: c.latitude, longitude: c.longitude })),
      ];
      const daysData = await fetchGroupTravelTiming({
        births,
        dest_lat: pin.lat,
        dest_lon: pin.lng,
        start_date: start_iso,
        days,
      });
      // Render combined score using renderTravelDays with adapted shape
      const adapted = daysData.map((d) => ({
        date: d.date,
        score: d.combined_score,
        influences: d.per_person.flatMap((p) => p.influences).slice(0, 5),
        warnings: d.per_person.flatMap((p) => p.warnings).slice(0, 5),
      }));
      renderTravelDays(adapted as any, pin);
      setStatus(`Group travel window: ${daysData.length} days scored.`);
    } else {
      const daysData = await fetchTravelTiming({
        birth: { datetime: b.datetime, latitude: b.latitude, longitude: b.longitude },
        dest_lat: pin.lat,
        dest_lon: pin.lng,
        start_date: start_iso,
        days,
      });
      renderTravelDays(daysData, pin);
      setStatus(`Travel window: ${daysData.length} days scored for (${pin.lat.toFixed(2)}°, ${pin.lng.toFixed(2)}°).`);
    }
  } catch (err) {
    setStatus(`Travel timing error: ${(err as Error).message}`, true);
  }
});







$('planTrip')?.addEventListener('click', async () => {
  const b = currentBirth();
  if (!b) { setStatus('Enter birth data first.', true); return; }
  if (!pins.length) { setStatus('Pin at least one destination first.', true); return; }
  const totalDays = parseInt(($('tripTotalDays') as HTMLInputElement)?.value || '14') || 14;
  const startStr = ($('tripStart') as HTMLInputElement)?.value || new Date().toISOString().slice(0, 10);
  const flexEnd = new Date(new Date(startStr).getTime() + 14 * 86400000).toISOString().slice(0, 10);
  try {
    setStatus('Planning trip…');
    const stops = pins.map((p) => ({
      latitude: p.lat,
      longitude: p.lng,
      name: p.birthName || `${p.lat.toFixed(1)},${p.lng.toFixed(1)}`,
      min_days: 2,
      max_days: 4,
      flex_start: startStr,
      flex_end: flexEnd,
    }));
    const res = await fetchTripPlan({
      birth: { datetime: b.datetime, latitude: b.latitude, longitude: b.longitude },
      stops,
      total_days: totalDays,
    });
    const container = $('tripPlanList');
    if (!container) return;
    container.innerHTML = '';
    const header = document.createElement('div');
    header.className = 'travel-summary';
    header.innerHTML = `<div class="travel-summary-title">🗺 Trip Plan</div><div class="travel-summary-sub">Total score: ${res.total_score}</div>`;
    container.appendChild(header);
    res.itinerary.forEach((it) => {
      const row = document.createElement('div');
      row.className = 'travel-row';
      row.innerHTML = `<div class="travel-date">${it.name}</div><div class="travel-score" style="background:${scoreColor(it.score)}">${it.score.toFixed(0)}</div>`;
      const inf = document.createElement('div');
      inf.className = 'travel-influences';
      const l1 = document.createElement('div'); l1.className = 'travel-inf-line'; l1.textContent = `Arrive ${it.arrival_date} · ${it.length_days} days`; inf.appendChild(l1);
      it.daily.forEach((d) => { const ld = document.createElement('div'); ld.className = 'travel-inf-line'; ld.textContent = `${d.date}: ${d.score.toFixed(0)}`; inf.appendChild(ld); });
      row.appendChild(inf);
      container.appendChild(row);
    });
    setStatus(`Trip planned: ${res.itinerary.length} stops.`);
  } catch (err) {
    setStatus(`Trip plan error: ${(err as Error).message}`, true);
  }
});
let pinned = false;
let currentPinId: string | null = null;

interface Pin {
  id: string;
  birthKey: string;
  birthName: string;
  birth: { datetime: string; latitude: number; longitude: number };
  lat: number;
  lng: number;
  createdAt: number;
}

const PINS_KEY = 'acg.pins';
const PIN_COLOR = '#ff4d6d';
function loadPins(): Pin[] {
  try {
    return JSON.parse(localStorage.getItem(PINS_KEY) || '[]') as Pin[];
  } catch {
    return [];
  }
}
let pins: Pin[] = loadPins();
function persistPins() {
  localStorage.setItem(PINS_KEY, JSON.stringify(pins));
}
function birthKey(b: { datetime: string; latitude: number; longitude: number }): string {
  return `${b.datetime}|${b.latitude}|${b.longitude}`;
}
function pinLabel(p: Pin): string {
  const ns = p.lat >= 0 ? 'N' : 'S';
  const ew = p.lng >= 0 ? 'E' : 'W';
  return `${Math.abs(p.lat).toFixed(1)}°${ns}, ${Math.abs(p.lng).toFixed(1)}°${ew}`;
}

function currentBirth(): { datetime: string; latitude: number; longitude: number } | null {
  return readBirth();
}

// Most recent ACG payload — used by the GeoJSON/KML export buttons.
let lastACGData: ACGResponse | null = null;

// Most recent top-cities + analysis — used by the PDF report.
let lastTopCities: import('./types').TopCity[] = [];
let lastAnalysisData: import('./types').LocationAnalysis | null = null;

// ---- Dual-chart compare mode ---------------------------------------------
let savedBirthsCache: BirthEntry[] = [];
let compareBirth: BirthEntry | null = null;

function refreshCompareSelect(): void {
  const sel = $('compareSelect') as HTMLSelectElement | null;
  if (!sel) return;
  const prev = sel.value;
  // Keep only the placeholder option, then re-add saved entries.
  while (sel.options.length > 1) sel.remove(1);
  savedBirthsCache.forEach((entry) => {
    const opt = document.createElement('option');
    opt.value = String(entry.id);
    opt.textContent = entry.name;
    sel.appendChild(opt);
  });
  // Preserve the previous selection when it still exists.
  if (prev && savedBirthsCache.some((e) => String(e.id) === prev)) {
    sel.value = prev;
  } else {
    sel.value = '';
    compareBirth = null;
  }
}

function refreshCompanionSelect(): void {
  const sel = $('companionSelect') as HTMLSelectElement | null;
  if (!sel) return;
  const prev = Array.from(sel.selectedOptions).map((o) => o.value);
  sel.innerHTML = '';
  savedBirthsCache.forEach((entry) => {
    const opt = document.createElement('option');
    opt.value = String(entry.id);
    opt.textContent = entry.name;
    if (prev.includes(String(entry.id))) opt.selected = true;
    sel.appendChild(opt);
  });
}
async function setCompareBirth(entry: BirthEntry | null): Promise<void> {
  compareBirth = entry;
  if (!entry) {
    globe.setCompareVisible(false);
    map2d.setCompareVisible(false);
    return;
  }
  try {
    const data = await fetchACG({
      birth: { datetime: entry.datetime, latitude: entry.latitude, longitude: entry.longitude },
      lat_step: 1.0,
    });
    globe.setCompareData(data);
    map2d.setCompareData(data);
    globe.setCompareVisible(true);
    map2d.setCompareVisible(true);
    setStatus(`Comparing with ${entry.name} — their lines show as overlay.`);
  } catch (err) {
    setStatus(`Compare failed: ${(err as Error).message}`, true);
  }
}

$('compareSelect')?.addEventListener('change', async (e) => {
  const id = (e.target as HTMLSelectElement).value;
  const entry = savedBirthsCache.find((b) => String(b.id) === id) ?? null;
  await setCompareBirth(entry);
  void loadTopCities();
});

async function runAnalysis(lat: number, lng: number, isPinned: boolean): Promise<void> {
  const birth = currentBirth();
  if (!birth) {
    if (isPinned) setStatus('Enter a birth date and location first.', true);
    return;
  }
  try {
    const data = await fetchAnalysis(
      { datetime: birth.datetime, latitude: birth.latitude, longitude: birth.longitude },
      { latitude: lat, longitude: lng },
    );
    if (isPinned || !pinned) {
      if (isPinned) lastAnalysisData = data;
      renderReport(data, isPinned, isPinned ? () => {
        if (currentPinId) deletePin(currentPinId);
      } : undefined);
    }
  } catch (err) {
    if (isPinned) setStatus(`Analysis error: ${(err as Error).message}`, true);
  }
}

globe.setHoverHandler((info: HoverInfo | null) => {
  // Only show a preview when hovering directly over an ACG line.
  // Globe/point hover no longer fires runAnalysis — the Pin tool is required.
  if (!info || info.type !== 'line') {
    // Don't clear the report while a pin is active.
    if (!pinned) clearReport();
    return;
  }
  renderHoverPreview(info.planet, info.angle, info.color);
});
map2d.setClickHandler((info: ClickInfo) => handleMapClick(info));
globe.setClickHandler((info: ClickInfo) => handleMapClick(info));
map2d.setPinClickHandler((id: string) => selectPin(id));
globe.setPinClickHandler((id: string) => selectPin(id));

function handleMapClick(info: ClickInfo) {
  const b = currentBirth();
  if (!b) {
    setStatus('Enter a birth date and location first.', true);
    return;
  }
  const pin: Pin = {
    id: `${Date.now().toString(36)}-${Math.random().toString(36).slice(2, 8)}`,
    birthKey: birthKey(b),
    birthName: ($('name') as HTMLInputElement).value.trim() || 'Unnamed',
    birth: { datetime: b.datetime, latitude: b.latitude, longitude: b.longitude },
    lat: info.lat,
    lng: info.lng,
    createdAt: Date.now(),
  };
  pins.push(pin);
  persistPins();
  currentPinId = pin.id;
  pinned = true;

  switchTab('intel');

  // Re-render immediately so the persisted pin always shows, even if the
  // focus/analysis calls below throw.
  renderPins();

  try {
    void runAnalysis(info.lat, info.lng, true);
    globe.focusBirth(info.lat, info.lng);
    map2d.focusLocation(info.lat, info.lng);
  } catch (err) {
    console.error('Post-pin UI update failed', err);
  }
}

async function loadTopCities(): Promise<void> {
  const birth = currentBirth();
  if (!birth) return;

  // Show skeleton while loading
  renderCitiesSkeleton();

  try {
    const cities = await fetchTopCities(
      { datetime: birth.datetime, latitude: birth.latitude, longitude: birth.longitude },
      currentGoalFocus,
      15,
      weightsDirty ? cityWeights() : undefined,
      compareBirth
        ? { datetime: compareBirth.datetime, latitude: compareBirth.latitude, longitude: compareBirth.longitude }
        : undefined,
      undefined,
      ($('regionSelect') as HTMLSelectElement | null)?.value || undefined,
    );
    lastTopCities = cities;
    renderTopCitiesCards(cities, (city: TopCity) => {
      // Fly to city & inspect
      globe.focusBirth(city.latitude, city.longitude);
      map2d.focusLocation(city.latitude, city.longitude, 7);

      const clickInfo: ClickInfo = { type: 'click', lat: city.latitude, lng: city.longitude };
      handleMapClick(clickInfo);
    }, currentGoalFocus);
  } catch (err) {
    const container = $('top-cities-list');
    if (container) {
      container.innerHTML = `<p class="report-empty error">Could not load recommendations: ${(err as Error).message}</p>`;
    }
  }
}

clearReport();

// ---- Birthplace autocomplete (search cities from /labels.json) ----
const citySearch = $('citySearch') as HTMLInputElement;
const citySuggest = $('citySuggest') as HTMLUListElement;
let activeSuggest = -1;

function renderSuggestions(q: string) {
  const query = q.trim().toLowerCase();
  if (!query) {
    citySuggest.hidden = true;
    citySuggest.innerHTML = '';
    return;
  }
  const matches = CITY_INDEX.filter((c) => c.name.toLowerCase().includes(query)).slice(0, 8);
  if (!matches.length) {
    citySuggest.innerHTML = '<li class="empty">No matching cities</li>';
    citySuggest.hidden = false;
    return;
  }
  citySuggest.innerHTML = '';
  matches.forEach((c, i) => {
    const li = document.createElement('li');
    if (i === activeSuggest) li.setAttribute('aria-selected', 'true');
    li.innerHTML = `<span>${c.name}</span><span class="meta">${c.lat.toFixed(1)}, ${c.lng.toFixed(1)}</span>`;
    li.addEventListener('click', () => selectCity(c));
    citySuggest.appendChild(li);
  });
  citySuggest.hidden = false;
}

function selectCity(c: City) {
  citySearch.value = c.name;
  ( $('lat') as HTMLInputElement).value = String(c.lat);
  ( $('lng') as HTMLInputElement).value = String(c.lng);
  citySuggest.hidden = true;
  activeSuggest = -1;
}

citySearch.addEventListener('input', () => {
  activeSuggest = -1;
  renderSuggestions(citySearch.value);
});
citySearch.addEventListener('keydown', (e) => {
  const items = Array.from(citySuggest.querySelectorAll('li:not(.empty)'));
  if (!items.length) return;
  if (e.key === 'ArrowDown') {
    e.preventDefault();
    activeSuggest = Math.min(items.length - 1, activeSuggest + 1);
    renderSuggestions(citySearch.value);
  } else if (e.key === 'ArrowUp') {
    e.preventDefault();
    activeSuggest = Math.max(0, activeSuggest - 1);
    renderSuggestions(citySearch.value);
  } else if (e.key === 'Enter' && activeSuggest >= 0) {
    e.preventDefault();
    selectCity(CITY_INDEX.filter((c) => c.name.toLowerCase().includes(citySearch.value.trim().toLowerCase()))[activeSuggest]);
  } else if (e.key === 'Escape') {
    citySuggest.hidden = true;
  }
});
document.addEventListener('click', (e) => {
  if (!citySuggest.contains(e.target as Node) && e.target !== citySearch) {
    citySuggest.hidden = true;
  }
});

// ---- "Use my location" (reverse-geocode-free: fill raw coords) ----
$('useLocation').addEventListener('click', () => {
  if (!navigator.geolocation) {
    setStatus('Geolocation is not supported by this browser.', true);
    return;
  }
  setStatus('Locating…');
  navigator.geolocation.getCurrentPosition(
    (pos) => {
      ($('lat') as HTMLInputElement).value = pos.coords.latitude.toFixed(4);
      ($('lng') as HTMLInputElement).value = pos.coords.longitude.toFixed(4);
      citySearch.value = '';
      setStatus('Location set from your device.');
    },
    () => setStatus('Could not get location. Enter coordinates manually.', true),
    { enableHighAccuracy: false, timeout: 10000 },
  );
});

function setStatus(msg: string, isError = false) {
  const el = $('status');
  el.textContent = msg;
  el.className = isError ? 'error' : '';
}

function syncPins(): void {
  const b = currentBirth();
  const mine = b ? pins.filter((p) => p.birthKey === birthKey(b)) : [];
  const mapped = mine.map((p) => ({ id: p.id, lat: p.lat, lng: p.lng, color: PIN_COLOR }));
  globe.setPins(mapped);
  map2d.setPins(mapped);
}

function selectPin(id: string): void {
  const pin = pins.find((p) => p.id === id);
  if (!pin) return;
  currentPinId = pin.id;
  pinned = true;
  switchTab('intel');
  globe.focusBirth(pin.lat, pin.lng);
  map2d.focusLocation(pin.lat, pin.lng);
  void runAnalysis(pin.lat, pin.lng, true);
  renderPins();
}

function renderPins(): void {
  const list = $('pinList');
  if (!list) return;
  list.innerHTML = '';
  const b = currentBirth();
  const mine = b ? pins.filter((p) => p.birthKey === birthKey(b)) : [];
  if (!b) {
    list.innerHTML = '<li class="empty">Load a birth first.</li>';
    syncPins();
    return;
  }
  if (!mine.length) {
    list.innerHTML = '<li class="empty">No saved pins yet.</li>';
    syncPins();
    return;
  }
  mine.forEach((p) => {
    const li = document.createElement('li');
    const go = document.createElement('button');
    go.className = 'link';
    go.textContent = pinLabel(p);
    go.title = `${p.birthName} · ${p.lat.toFixed(2)}, ${p.lng.toFixed(2)} — click to fly here`;
    go.addEventListener('click', () => selectPin(p.id));
    const del = document.createElement('button');
    del.className = 'del';
    del.textContent = '✕';
    del.title = 'Delete pin';
    del.addEventListener('click', () => deletePin(p.id));
    li.append(go, del);
    list.appendChild(li);
  });
  syncPins();
}

function deletePin(id: string): void {
  pins = pins.filter((p) => p.id !== id);
  persistPins();
  if (currentPinId === id) {
    pinned = false;
    currentPinId = null;
    clearReport();
  }
  renderPins();
}

// ---------------------------------------------------------------------------
// Travel Timing (electional)
// ---------------------------------------------------------------------------

async function loadTravelTiming(): Promise<void> {
  const b = currentBirth();
  if (!b) {
    const c = $('travelTimingList');
    if (c) c.innerHTML = '<p class="report-empty">Enter your birth data first.</p>';
    return;
  }
  // Use the currently selected pin as the destination, or fall back to the
  // birth location if no pin is active.
  let destLat: number;
  let destLng: number;
  const currentPin = activePin();
  if (currentPin) {
    destLat = currentPin.lat;
    destLng = currentPin.lng;
  } else {
    destLat = b.latitude;
    destLng = b.longitude;
  }

  const startStr = ($('travelStart') as HTMLInputElement)?.value;
  const startDate = startStr ? `${startStr}T00:00:00+00:00` : new Date().toISOString();
  const days = parseInt(($('travelDays') as HTMLInputElement)?.value || '30') || 30;

  const container = $('travelTimingList');
  if (container) {
    container.innerHTML = '<div class="travel-loading">Calculating…</div>';
  }
  try {
    const results = await fetchTravelTiming({
      birth: b,
      dest_lat: destLat,
      dest_lon: destLng,
      start_date: startDate,
      days,
    });
    const pin = currentPin || { lat: destLat, lng: destLng };
    renderTravelDays(results, pin);
  } catch (err) {
    if (container) {
      container.innerHTML = `<p class="report-empty error">Travel timing error: ${(err as Error).message}</p>`;
    }
  }
}

// Travel timing uses renderTravelDays from panel.ts — wired below.
$('loadTravelTiming')?.addEventListener('click', () => { void loadTravelTiming(); });
$('travelStart')?.addEventListener('change', () => { void loadTravelTiming(); });
$('travelDays')?.addEventListener('change', () => { void loadTravelTiming(); });

function buildLegend(data: ACGResponse) {
  const planets = [...new Set(data.lines.map((l) => l.planet))];
  const colorOf = (p: string) =>
    data.lines.find((l) => l.planet === p)?.color ?? '#ffffff';

  const ANGLE_SYMBOLS: Record<string, string> = { MC: '⬆', IC: '⬇', ASC: '↗', DSC: '↘' };

  // Small "Show all / None" action cluster inserted after a group's heading.
  function addGroupActions(block: HTMLElement, setVisible: (on: boolean) => void) {
    const h = block.querySelector('h2');
    if (!h) return;
    const actions = document.createElement('div');
    actions.className = 'legend-actions';
    const all = document.createElement('button');
    all.type = 'button';
    all.className = 'legend-action';
    all.textContent = 'All';
    all.addEventListener('click', () => setVisible(true));
    const none = document.createElement('button');
    none.type = 'button';
    none.className = 'legend-action';
    none.textContent = 'None';
    none.addEventListener('click', () => setVisible(false));
    actions.append(all, none);
    block.querySelector(':scope > .legend-actions')?.remove();
    h.insertAdjacentElement('afterend', actions);
  }

  const pt = $('planetToggles');
  pt.innerHTML = '';
  planets.forEach((p) => {
    const label = document.createElement('label');
    label.className = 'toggle';
    const cb = document.createElement('input');
    cb.type = 'checkbox';
    cb.checked = true;
    cb.dataset.planet = p;
    cb.addEventListener('change', () => {
      globe.setPlanetVisible(p, cb.checked);
      map2d.setPlanetVisible(p, cb.checked);
    });
    const sw = document.createElement('span');
    sw.className = 'swatch';
    sw.style.background = colorOf(p);
    label.append(cb, sw, document.createTextNode(' ' + p));
    pt.appendChild(label);
  });
  addGroupActions(pt.closest('.legend-block') as HTMLElement, (on) => {
    pt.querySelectorAll<HTMLInputElement>('input').forEach((cb) => {
      cb.checked = on;
      globe.setPlanetVisible(cb.dataset.planet!, on);
      map2d.setPlanetVisible(cb.dataset.planet!, on);
    });
  });

  const angles = ['MC', 'IC', 'ASC', 'DSC'];
  const at = $('angleToggles');
  at.innerHTML = '';
  angles.forEach((a) => {
    const label = document.createElement('label');
    label.className = 'toggle';
    const cb = document.createElement('input');
    cb.type = 'checkbox';
    cb.checked = true;
    cb.addEventListener('change', () => {
      globe.setAngleVisible(a, cb.checked);
      map2d.setAngleVisible(a, cb.checked);
    });
    const sym = document.createElement('span');
    sym.className = 'angle-sym';
    sym.textContent = ANGLE_SYMBOLS[a] ?? '';
    label.append(cb, sym, document.createTextNode(' ' + a));
    at.appendChild(label);
  });
  addGroupActions(at.closest('.legend-block') as HTMLElement, (on) => {
    at.querySelectorAll<HTMLInputElement>('input').forEach((cb) => {
      cb.checked = on;
      // Each angle checkbox has no dataset; map by index.
    });
    angles.forEach((a) => {
      globe.setAngleVisible(a, on);
      map2d.setAngleVisible(a, on);
    });
  });
}

$('dayMode')?.addEventListener('change', (e) => {
  globe.setDayMode((e.target as HTMLInputElement).checked);
});

$('globeBrightness')?.addEventListener('input', (e) => {
  const v = parseFloat((e.target as HTMLInputElement).value);
  const valEl = $('globeBrightnessVal');
  if (valEl) valEl.textContent = v.toFixed(2);
  globe.setBrightness(v);
});

$('globeContrast')?.addEventListener('input', (e) => {
  const v = parseFloat((e.target as HTMLInputElement).value);
  const valEl = $('globeContrastVal');
  if (valEl) valEl.textContent = v.toFixed(2);
  globe.setContrast(v);
});

$('autoRotate')?.addEventListener('change', (e) => {
  globe.setAutoRotate((e.target as HTMLInputElement).checked);
});

$('localSpace')?.addEventListener('change', (e) => {
  globe.setLocalSpaceVisible((e.target as HTMLInputElement).checked);
  map2d.setLocalSpaceVisible((e.target as HTMLInputElement).checked);
});

$('parans')?.addEventListener('change', (e) => {
  globe.setParansVisible((e.target as HTMLInputElement).checked);
  map2d.setParansVisible((e.target as HTMLInputElement).checked);
});
// ---- Advanced overlays: transit / progressed / geodetic / stars / midpoints ----
let transitLoaded = false;
const showTransitToggle = $('showTransit') as HTMLInputElement | null;

showTransitToggle?.addEventListener('change', () => {
  const on = showTransitToggle.checked;
  globe.setTransitVisible(on);
  map2d.setTransitVisible(on);
  // First-time enable with nothing loaded yet -> fetch, then show.
  if (on && !transitLoaded) loadTransitBtn?.click();
});

const loadTransitBtn = $('loadTransit') as HTMLButtonElement | null;
loadTransitBtn?.addEventListener('click', async () => {
  const b = currentBirth();
  if (!b) { setStatus('Enter a birth date and location first.', true); return; }
  const date = ($('transitDate') as HTMLInputElement).value;
  const time = ($('transitTime') as HTMLInputElement).value || '00:00';
  const iso = `${date}T${time}:00+00:00`;
  try {
    setStatus('Loading transit lines…');
    const data = await fetchTransitACG({ birth: b, transit_iso: iso });
    globe.setTransitData(data);
    map2d.setTransitData(data);
    transitLoaded = true;
    if (showTransitToggle && !showTransitToggle.checked) showTransitToggle.checked = true;
    globe.setTransitVisible(true);
    map2d.setTransitVisible(true);
    setStatus(`Transit lines: ${data.lines.length} loaded.`);
  } catch (err) {
    setStatus(`Transit error: ${(err as Error).message}`, true);
  }
});

const progressedToggle = $('progressedToggle') as HTMLInputElement | null;
let progressedLoadedAge: number | null = null;
progressedToggle?.addEventListener('change', async () => {
  const on = progressedToggle.checked;
  globe.setProgressedVisible(on);
  map2d.setProgressedVisible(on);
  if (!on) return;
  const b = currentBirth();
  if (!b) { setStatus('Enter a birth date and location first.', true); return; }
  const age = parseFloat(($('progressedAge') as HTMLInputElement).value) || 0;
  // Already fetched for this birth + age -> just toggle visibility.
  if (progressedLoadedAge === age && progressedLoadedAge !== null) return;
  try {
    setStatus('Loading progressed lines…');
    const data = await fetchProgressedACG({ birth: b, age_years: age });
    globe.setProgressedData(data);
    map2d.setProgressedData(data);
    progressedLoadedAge = age;
    setStatus(`Progressed lines: ${data.lines.length} loaded.`);
  } catch (err) {
    setStatus(`Progressed error: ${(err as Error).message}`, true);
  }
});
$('progressedAge')?.addEventListener('change', () => {
  if ((progressedToggle as HTMLInputElement)?.checked) progressedToggle?.dispatchEvent(new Event('change'));
});

// Drop every overlay layer (data + visibility + UI state). Called whenever a
// new birth chart is drawn so overlays can never mix two different charts.
function clearOverlays() {
  transitLoaded = false;
  progressedLoadedAge = null;
  const empty = { lines: [] };
  globe.setTransitData(empty); globe.setProgressedData(empty);
  globe.setGeodeticData(empty); globe.setFixedStarData(empty); globe.setMidpointData(empty);
  globe.setSolarReturnData(empty); globe.setLunarReturnData(empty);
  globe.setCrossings({ crossings: [] });
  map2d.setTransitData(empty); map2d.setProgressedData(empty);
  map2d.setGeodeticData(empty); map2d.setFixedStarData(empty); map2d.setMidpointData(empty);
  map2d.setSolarReturnData(empty); map2d.setLunarReturnData(empty);
  map2d.setCrossings({ crossings: [] });
  globe.setTransitVisible(false); globe.setProgressedVisible(false);
  globe.setGeodeticVisible(false); globe.setFixedStarsVisible(false); globe.setMidpointsVisible(false);
  globe.setSolarReturnVisible(false); globe.setLunarReturnVisible(false);
  globe.setCrossingsVisible(false);
  map2d.setTransitVisible(false); map2d.setProgressedVisible(false);
  map2d.setGeodeticVisible(false); map2d.setFixedStarsVisible(false); map2d.setMidpointsVisible(false);
  map2d.setSolarReturnVisible(false); map2d.setLunarReturnVisible(false);
  map2d.setCrossingsVisible(false);
  if (showTransitToggle) showTransitToggle.checked = false;
  if (progressedToggle) progressedToggle.checked = false;
  for (const id of ['ovGeodetic', 'ovFixedStars', 'ovMidpoints', 'ovCrossings', 'ovSolarReturn', 'ovLunarReturn']) {
    $(id)?.classList.remove('active');
  }
}

function wireLazyOverlay(
  btnId: string,
  fetchFn: (b: any) => Promise<{ lines: any[] }>,
  gSet: (d: { lines: any[] }) => void,
  gVis: (on: boolean) => void,
  mSet: (d: { lines: any[] }) => void,
  mVis: (on: boolean) => void,
) {
  const btn = $(btnId) as HTMLButtonElement | null;
  if (!btn) return;
  btn.addEventListener('click', async () => {
    const b = currentBirth();
    if (!b) { setStatus('Enter a birth date and location first.', true); return; }
    const on = !btn.classList.contains('active');
    btn.classList.toggle('active', on);
    btn.setAttribute('aria-pressed', String(on));
    if (!on) { gVis(false); mVis(false); return; }
    try {
      setStatus(`Loading ${btn.textContent?.trim()}…`);
      const data = await fetchFn({ birth: b });
      gSet(data); gVis(true);
      mSet(data); mVis(true);
      setStatus(`${btn.textContent?.trim()}: ${data.lines.length} lines.`);
    } catch (err) {
      btn.classList.remove('active');
      setStatus(`${(btn.textContent || 'Overlay').trim()} error: ${(err as Error).message}`, true);
    }
  });
}

wireLazyOverlay('ovGeodetic', fetchGeodetic, globe.setGeodeticData.bind(globe) as any, globe.setGeodeticVisible.bind(globe) as any, map2d.setGeodeticData.bind(map2d) as any, map2d.setGeodeticVisible.bind(map2d) as any);
wireLazyOverlay('ovFixedStars', fetchFixedStars, globe.setFixedStarData.bind(globe) as any, globe.setFixedStarsVisible.bind(globe) as any, map2d.setFixedStarData.bind(map2d) as any, map2d.setFixedStarsVisible.bind(map2d) as any);
wireLazyOverlay('ovMidpoints', fetchMidpoints, globe.setMidpointData.bind(globe) as any, globe.setMidpointsVisible.bind(globe) as any, map2d.setMidpointData.bind(map2d) as any, map2d.setMidpointsVisible.bind(map2d) as any);

// Crossings (power places) — point markers, not lines
$('ovCrossings')?.addEventListener('click', async () => {
  const b = currentBirth();
  if (!b) { setStatus('Enter a birth date and location first.', true); return; }
  const btn = $('ovCrossings') as HTMLButtonElement;
  const on = !btn.classList.contains('active');
  btn.classList.toggle('active', on);
  btn.setAttribute('aria-pressed', String(on));
  if (!on) { globe.setCrossingsVisible(false); map2d.setCrossingsVisible(false); return; }
  try {
    setStatus('Loading power places…');
    const data = await fetchCrossings({ birth: b });
    globe.setCrossings(data); globe.setCrossingsVisible(true);
    map2d.setCrossings(data); map2d.setCrossingsVisible(true);
    setStatus(`Power places: ${data.crossings.length} markers.`);
  } catch (err) {
    btn.classList.remove('active');
    setStatus(`Power places error: ${(err as Error).message}`, true);
  }
});

// Solar return overlay
$('ovSolarReturn')?.addEventListener('click', async () => {
  const b = currentBirth();
  if (!b) { setStatus('Enter a birth date and location first.', true); return; }
  const btn = $('ovSolarReturn') as HTMLButtonElement;
  const on = !btn.classList.contains('active');
  btn.classList.toggle('active', on);
  btn.setAttribute('aria-pressed', String(on));
  if (!on) { globe.setSolarReturnVisible(false); map2d.setSolarReturnVisible(false); return; }
  try {
    const year = parseInt(($('returnYear') as HTMLInputElement)?.value || '2000') || 2000;
    setStatus('Loading solar return…');
    const data = await fetchSolarReturn({ birth: b, year });
    globe.setSolarReturnData(data); globe.setSolarReturnVisible(true);
    map2d.setSolarReturnData(data); map2d.setSolarReturnVisible(true);
    const moment = (data as any).return_moment_iso ? ` (moment: ${(data as any).return_moment_iso})` : '';
    setStatus(`Solar return ${year}: ${data.lines.length} lines.${moment}`);
  } catch (err) {
    btn.classList.remove('active');
    setStatus(`Solar return error: ${(err as Error).message}`, true);
  }
});

// Lunar return overlay
$('ovLunarReturn')?.addEventListener('click', async () => {
  const b = currentBirth();
  if (!b) { setStatus('Enter a birth date and location first.', true); return; }
  const btn = $('ovLunarReturn') as HTMLButtonElement;
  const on = !btn.classList.contains('active');
  btn.classList.toggle('active', on);
  btn.setAttribute('aria-pressed', String(on));
  if (!on) { globe.setLunarReturnVisible(false); map2d.setLunarReturnVisible(false); return; }
  try {
    const year = parseInt(($('returnYear') as HTMLInputElement)?.value || '2000') || 2000;
    const monthStr = ($('returnMonth') as HTMLInputElement)?.value;
    const month = monthStr ? parseInt(monthStr) || undefined : undefined;
    setStatus('Loading lunar return…');
    const data = await fetchLunarReturn({ birth: b, year, month });
    globe.setLunarReturnData(data); globe.setLunarReturnVisible(true);
    map2d.setLunarReturnData(data); map2d.setLunarReturnVisible(true);
    const moment = (data as any).return_moment_iso ? ` (moment: ${(data as any).return_moment_iso})` : '';
    setStatus(`Lunar return: ${data.lines.length} lines.${moment}`);
  } catch (err) {
    btn.classList.remove('active');
    setStatus(`Lunar return error: ${(err as Error).message}`, true);
  }
});
$('labels')?.addEventListener('change', (e) => {
  globe.setLabelsVisible((e.target as HTMLInputElement).checked);
});

// ---- Globe control cluster (bottom-left) ----
const ctrlRotate = $('ctrlRotate') as HTMLButtonElement;
const ctrlGraticule = $('ctrlGraticule') as HTMLButtonElement;

ctrlRotate?.addEventListener('click', () => {
  const next = !(ctrlRotate.getAttribute('aria-pressed') === 'true');
  ctrlRotate.setAttribute('aria-pressed', String(next));
  ($('autoRotate') as HTMLInputElement).checked = next;
  globe.setAutoRotate(next);
});
// Fullscreen toggle (Esc exits via the browser; label stays in sync on any exit)
const ctrlFullscreen = $('ctrlFullscreen') as HTMLButtonElement;
function syncFullscreenBtn() {
  const active = !!document.fullscreenElement;
  ctrlFullscreen.setAttribute('aria-pressed', String(active));
  ctrlFullscreen.innerHTML = active ? '⛶ Exit Fullscreen' : '⛶ Fullscreen';
  ctrlFullscreen.title = active ? 'Exit fullscreen (Esc)' : 'Toggle fullscreen (Esc to exit)';
  // Leaving fullscreen always restores the panels; entering starts the idle timer.
  document.body.classList.remove('fs-hide-ui');
  if (active) showFsUi();
  else if (fsIdleTimer) {
    clearTimeout(fsIdleTimer);
    fsIdleTimer = null;
  }
}
ctrlFullscreen?.addEventListener('click', () => {
  if (document.fullscreenElement) {
    void document.exitFullscreen();
  } else {
    void document.documentElement.requestFullscreen();
  }
});
document.addEventListener('fullscreenchange', syncFullscreenBtn);

// While in fullscreen, hide the three panels after 3s without mouse movement;
// any mouse move (or exiting fullscreen) shows them again.
const FS_IDLE_MS = 3000;
let fsIdleTimer: ReturnType<typeof setTimeout> | null = null;
function showFsUi() {
  document.body.classList.remove('fs-hide-ui');
  if (fsIdleTimer) clearTimeout(fsIdleTimer);
  fsIdleTimer = setTimeout(() => {
    if (document.fullscreenElement) document.body.classList.add('fs-hide-ui');
  }, FS_IDLE_MS);
}
document.addEventListener('mousemove', showFsUi);

syncFullscreenBtn();



ctrlGraticule?.addEventListener('click', () => {
  const next = !(ctrlGraticule.getAttribute('aria-pressed') === 'true');
  ctrlGraticule.setAttribute('aria-pressed', String(next));
  globe.setGraticuleVisible(next);
});

$('ctrlReset')?.addEventListener('click', () => {
  globe.resetView();
  map2d.resetView();
});

$('zoomIn')?.addEventListener('click', () => globe.zoom(1 / 1.5));
$('zoomOut')?.addEventListener('click', () => globe.zoom(1.5));

const zoomPctEl = $('zoomPct');
function updateZoomPct() {
  if (zoomPctEl) zoomPctEl.textContent = `${globe.getZoomPercent()}%`;
}
globe.onZoomChange(updateZoomPct);
updateZoomPct();

function readBirth(): { datetime: string; latitude: number; longitude: number } | null {
  const date = ($('date') as HTMLInputElement).value;
  const time = ($('time') as HTMLInputElement).value || '00:00';
  const offset = parseFloat(($('offset') as HTMLInputElement).value) || 0;
  const lat = parseFloat(($('lat') as HTMLInputElement).value);
  const lng = parseFloat(($('lng') as HTMLInputElement).value);

  if (!date || Number.isNaN(lat) || Number.isNaN(lng)) {
    return null;
  }

  const sign = offset >= 0 ? '+' : '-';
  const abs = Math.abs(offset);
  const oh = String(Math.floor(abs)).padStart(2, '0');
  const om = String(Math.round((abs % 1) * 60)).padStart(2, '0');
  const datetime = `${date}T${time}:00${sign}${oh}:${om}`;

  return { datetime, latitude: lat, longitude: lng };
}

async function drawCurrentBirth(): Promise<void> {
  const birth = readBirth();
  if (!birth) {
    setStatus('Please fill in the date and coordinates.', true);
    return;
  }

  setStatus('Calculating…');
  try {
    const data = await fetchACG({
      birth: { datetime: birth.datetime, latitude: birth.latitude, longitude: birth.longitude },
      lat_step: 1.0,
    });
    lastACGData = data;
    globe.setData(data, { lat: birth.latitude, lng: birth.longitude });
    map2d.setData(data, { lat: birth.latitude, lng: birth.longitude });
    buildLegend(data);
    // New chart drawn -> drop any overlays that belonged to the previous one.
    clearOverlays();
    const planetCount = new Set(data.lines.map((l) => l.planet)).size;
    setStatus(`Rendered ${data.lines.length} lines for ${planetCount} planets.`);

    // Load top cities recommendations for current birth
    void loadTopCities();
  } catch (err) {
    setStatus(`Error: ${(err as Error).message}`, true);
  }
  renderPins();
  if (!booted) { booted = true; hideLoader(); }
}

$('birthForm').addEventListener('submit', async (e) => {
  e.preventDefault();
  await drawCurrentBirth();
});

$('saveEntry').addEventListener('click', async () => {
  const birth = readBirth();
  if (!birth) {
    setStatus('Please fill in the date and coordinates.', true);
    return;
  }
  const name = (($('name') as HTMLInputElement).value || '').trim() || 'Unnamed';
  setStatus('Saving…');
  try {
    await saveBirth({ name, ...birth, note: null });
    setStatus(`Saved "${name}".`);
  } catch (err) {
    setStatus(`Error: ${(err as Error).message}`, true);
  } finally {
    await refreshSaved();
  }
});

function applyBirth(entry: BirthEntry) {
  const m = entry.datetime.match(/^(\d{4}-\d{2}-\d{2})T(\d{2}:\d{2})/);
  if (m) {
    ($('date') as HTMLInputElement).value = m[1];
    ($('time') as HTMLInputElement).value = m[2];
  }
  const off = entry.datetime.match(/([+-]\d{2}):(\d{2})$/);
  if (off) {
    ($('offset') as HTMLInputElement).value = String(
      parseFloat(off[1]) + parseFloat(off[2]) / 60 * (off[1].startsWith('-') ? -1 : 1),
    );
  }
  ($('lat') as HTMLInputElement).value = String(entry.latitude);
  ($('lng') as HTMLInputElement).value = String(entry.longitude);
  ($('name') as HTMLInputElement).value = entry.name;
}

async function refreshSaved() {
  const list = $('savedList');
  try {
    const entries = await fetchBirths();
    savedBirthsCache = entries;
    refreshCompareSelect();
    refreshCompanionSelect();
    list.innerHTML = '';
    if (entries.length === 0) {
      const li = document.createElement('li');
      li.className = 'empty';
      li.textContent = 'No saved births yet.';
      list.appendChild(li);
      return;
    }
    entries.forEach((entry) => {
      const li = document.createElement('li');

      const load = document.createElement('button');
      load.className = 'link';
      load.textContent = entry.name;
      load.title = `${entry.datetime}  (${entry.latitude}, ${entry.longitude})`;
      load.addEventListener('click', () => {
        applyBirth(entry);
        drawCurrentBirth();
      });

      const del = document.createElement('button');
      del.className = 'del';
      del.textContent = '✕';
      del.title = 'Delete';
      del.addEventListener('click', async () => {
        try {
          await deleteBirth(entry.id);
          await refreshSaved();
        } catch (err) {
          setStatus(`Error: ${(err as Error).message}`, true);
        }
      });

      li.append(load, del);
      list.appendChild(li);
    });
  } catch (err) {
    // Don't wipe an already-loaded list on a transient fetch error.
    setStatus(`Could not refresh saved list: ${(err as Error).message}`, true);
  }
}

// ---- Loading overlay ----
let booted = false;
function showLoader() {
  document.getElementById('loader')?.classList.remove('hidden');
}
function hideLoader() {
  document.getElementById('loader')?.classList.add('hidden');
}
function setProgress(frac: number) {
  const pct = Math.max(0, Math.min(1, frac));
  const bar = document.getElementById('loaderBar');
  const label = document.getElementById('loaderPct');
  if (bar) bar.style.width = `${Math.round(pct * 100)}%`;
  if (label) label.textContent = `${Math.round(pct * 100)}%`;
}

// Load the demo chart immediately on startup.
refreshSaved();
void boot();

async function boot() {
  showLoader();
  try {
    await globe.preloadTextures(setProgress);
  } catch {
    /* texture failed to preload — globe.gl will still attempt to load it */
  }
  loadLabels();
  setProgress(0.85);
  ($('birthForm') as HTMLFormElement).requestSubmit();
}

function loadLabels() {
  fetch('/labels.json')
    .then((r) => (r.ok ? r.json() : Promise.reject()))
    .then((data) => {
      globe.setLabels(data);
      map2d.setCities(data.cities || []);
      if (Array.isArray(data.cities)) CITY_INDEX = data.cities;
    })
    .catch(() => { /* labels are optional */ });
}

// ---------------------------------------------------------------------------
// Export & Share
// ---------------------------------------------------------------------------

function shareState(): ShareState {
  const state: ShareState = {};
  const b = currentBirth();
  if (b) state.b = b;
  if (weightsDirty) state.w = cityWeights();
  state.g = currentGoalFocus;
  return state;
}

$('shareLink')?.addEventListener('click', async () => {
  const url = buildShareUrl(shareState());
  history.replaceState(null, '', url);
  const ok = await copyToClipboard(url);
  setStatus(ok ? 'Share link copied to clipboard.' : 'Link placed in the URL bar — copy it from there.', !ok);
});

$('exportPng')?.addEventListener('click', () => {
  try {
    downloadDataURL(globe.captureImage(), 'astro-map.png');
    setStatus('Globe image saved as astro-map.png');
  } catch (err) {
    setStatus(`Image export failed: ${(err as Error).message}`, true);
  }
});

$('exportGeojson')?.addEventListener('click', () => {
  if (!lastACGData?.lines?.length) {
    setStatus('Draw a chart first — there are no lines to export.', true);
    return;
  }
  const birth = currentBirth();
  downloadText(
    acgToGeoJSON(lastACGData.lines, { birth: birth?.datetime ?? null }),
    'astro-lines.geojson',
    'application/geo+json',
  );
  setStatus(`Exported ${lastACGData.lines.length} lines as GeoJSON.`);
});

$('exportKml')?.addEventListener('click', () => {
  if (!lastACGData?.lines?.length) {
    setStatus('Draw a chart first — there are no lines to export.', true);
    return;
  }
  downloadText(
    acgToKML(lastACGData.lines, { title: 'Astrocartography lines' }),
    'astro-lines.kml',
    'application/vnd.google-earth.kml+xml',
  );
  setStatus(`Exported ${lastACGData.lines.length} lines as KML.`);
});

$('printReport')?.addEventListener('click', () => {
  const birth = currentBirth();
  if (!birth) {
    setStatus('Draw your chart first before printing a report.', true);
    return;
  }
  const container = $('printReportContainer');
  if (!container) { window.print(); return; }

  // Capture globe image (Cesium canvas)
  let mapImgDataUrl = '';
  try { mapImgDataUrl = globe.captureImage(); } catch { /* optional */ }

  // Import and invoke the report builder
  import('./panel').then(({ buildFullPrintReportHTML }) => {
    container.innerHTML = buildFullPrintReportHTML({
      birthName: ($('name') as HTMLInputElement)?.value?.trim() || 'Birth Chart',
      birth,
      mapImgDataUrl,
      topCities: lastTopCities.length ? lastTopCities : undefined,
      lastAnalysis: lastAnalysisData,
    });
    // Force a paint before opening print dialog to ensure content is rendered
    requestAnimationFrame(() => {
      requestAnimationFrame(() => {
        window.print();
      });
    });
  }).catch(() => {
    // Fallback: just print as-is
    window.print();
  });
});

// ---------------------------------------------------------------------------
// Share-link restore — fills the birth form (and weights) from #s=… hash
// ---------------------------------------------------------------------------

(function restoreFromHash(): void {
  const restored = decodeShareState(location.hash);
  if (!restored?.b) return;
  const m = restored.b.datetime.match(/^(\d{4}-\d{2}-\d{2})T(\d{2}):(\d{2})/);
  const off = restored.b.datetime.match(/([+-])(\d{2}):(\d{2})$/);
  if (m) {
    ($('date') as HTMLInputElement).value = m[1];
    ($('time') as HTMLInputElement).value = `${m[2]}:${m[3]}`;
  }
  if (off) {
    const h = Number(off[2]);
    const mins = Number(off[3]);
    const val = (h + mins / 60) * (off[1] === '-' ? -1 : 1);
    ($('offset') as HTMLInputElement).value = String(val);
  }
  ($('lat') as HTMLInputElement).value = String(restored.b.latitude);
  ($('lng') as HTMLInputElement).value = String(restored.b.longitude);

  if (restored.w) {
    const map: Record<string, string> = {
      love: 'wLove', career: 'wCareer', home: 'wHome', peace: 'wPeace', growth: 'wGrowth',
    };
    for (const [domain, id] of Object.entries(map)) {
      const inp = $(id) as HTMLInputElement | null;
      const v = restored.w[domain];
      if (inp && typeof v === 'number' && v >= 0 && v <= 10) inp.value = String(v);
    }
    weightsDirty = true;
  }
  // Redraw automatically with the shared state.
  void drawCurrentBirth();
})();
