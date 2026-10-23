import 'cesium/Build/Cesium/Widgets/widgets.css';
import * as Cesium from 'cesium';
import type { ACGLine, ACGResponse, SubPoint, LocalSpaceRay, Paran } from './types';

// Cesium loads its Web Workers + icon assets relative to this URL. The copy
// script (scripts/copy-cesium.mjs) places a full Build/Cesium tree under
// public/cesium, so this relative path resolves in both the dev server and a
// static build (base: './').
(globalThis as { CESIUM_BASE_URL?: string }).CESIUM_BASE_URL = './cesium/';

export interface GlobeHandle {
  setData: (data: ACGResponse, birth: { lat: number; lng: number }) => void;
  setPlanetVisible: (planet: string, visible: boolean) => void;
  setAngleVisible: (angle: string, visible: boolean) => void;
  setLocalSpaceVisible: (on: boolean) => void;
  setParansVisible: (on: boolean) => void;
  setDayMode: (day: boolean) => void;
  setBrightness: (value: number) => void;
  setContrast: (value: number) => void;
  setAutoRotate: (on: boolean) => void;
  setGraticuleVisible: (on: boolean) => void;
  resetView: () => void;
  focusBirth: (lat: number, lng: number) => void;
  getPlanets: () => string[];
  setHoverHandler: (cb: ((info: HoverInfo | null) => void) | null) => void;
  setClickHandler: (cb: ((info: ClickInfo) => void) | null) => void;
  setPins: (pins: { id?: string; lat: number; lng: number; color: string }[]) => void;
  setPinClickHandler: (cb: ((id: string) => void) | null) => void;
  zoom: (factor: number) => void;
  getZoomPercent: () => number;
  onZoomChange: (cb: ((pct: number) => void) | null) => void;
  preloadTextures: (onProgress?: (frac: number) => void) => Promise<void>;
  setLabels: (data: { countries: any[]; cities: any[] }) => void;
  setLabelsVisible: (on: boolean) => void;
  setCursor: (cursor: string) => void;
  setPinMode: (on: boolean) => void;
  setCrosshairVisible: (on: boolean) => void;
  captureImage: () => string;
  setCities: (cities: any[]) => void;
  // Advanced overlays (transit / progressed / geodetic / fixed stars / midpoints)
  setTransitData: (data: { lines: ACGLine[] }) => void;
  setProgressedData: (data: { lines: ACGLine[] }) => void;
  setGeodeticData: (data: { lines: ACGLine[] }) => void;
  setFixedStarData: (data: { lines: ACGLine[] }) => void;
  setMidpointData: (data: { lines: ACGLine[] }) => void;
  setCompareData: (data: { lines: ACGLine[] }) => void;
  setCompareVisible: (on: boolean) => void;
  setTransitVisible: (on: boolean) => void;
  setProgressedVisible: (on: boolean) => void;
  setGeodeticVisible: (on: boolean) => void;
  setFixedStarsVisible: (on: boolean) => void;
  setMidpointsVisible: (on: boolean) => void;
  setSolarReturnData: (data: { lines: ACGLine[] }) => void;
  setSolarReturnVisible: (on: boolean) => void;
  setLunarReturnData: (data: { lines: ACGLine[] }) => void;
  setLunarReturnVisible: (on: boolean) => void;
  setCrossings: (data: { crossings: import('./types').Crossing[] }) => void;
  setCrossingsVisible: (on: boolean) => void;
}

export type HoverInfo =
  | { type: 'globe'; lat: number; lng: number }
  | { type: 'line'; planet: string; angle: string; color: string }
  | { type: 'point'; point: PointDatum }
  | { type: 'none' };

export type ClickInfo = { type: 'click'; lat: number; lng: number };

interface PointDatum {
  planet?: string;
  type?: string;
  latitude: number;
  longitude: number;
  color: string;
  birth?: boolean;
  paran?: boolean;
  pin?: boolean;
  planet_a?: string;
  circle_a?: string;
  planet_b?: string;
  circle_b?: string;
  interpretation?: string;
  crossingType?: string;
}

interface RingDatum {
  lat: number;
  lng: number;
  color: string;
}

// A security/type tag attached to every overlay entity so hover/click picking
// can tell lines, points and pins apart and read their metadata.
type OverlayTag =
  | { kind: 'line'; planet: string; angle: string; color: string }
  | { kind: 'point'; datum: PointDatum }
  | { kind: 'pin'; id: string }
  | { kind: 'ring' };

/** #rrggbb (or #rgb) -> Cesium.Color with optional alpha. */
function col(hex: string, alpha = 1): Cesium.Color {
  return Cesium.Color.fromCssColorString(hex).withAlpha(alpha);
}

function clamp(v: number, lo: number, hi: number): number {
  return Math.max(lo, Math.min(hi, v));
}

/** True only when lat/lng are real, finite coordinates in valid ranges. */
function isGeoValid(lat: number, lng: number): boolean {
  return (
    Number.isFinite(lat) &&
    Number.isFinite(lng) &&
    lat >= -90.0001 &&
    lat <= 90.0001 &&
    lng >= -180.0001 &&
    lng <= 180.0001
  );
}

/**
 * Split a GeoJSON LineString at the antimeridian (when consecutive longitudes
 * jump by more than 180deg) so thick surface lines never wrap the wrong way
 * across the globe.
 */
function splitCoords(coords: number[][]): number[][][] {
  const segs: number[][][] = [];
  let cur: number[][] = [];
  let prev: number | undefined;
  for (const p of coords) {
    const lon = p[0];
    if (prev !== undefined && Math.abs(lon - prev) > 180 && cur.length) {
      segs.push(cur);
      cur = [];
    }
    cur.push(p);
    prev = lon;
  }
  if (cur.length) segs.push(cur);
  return segs;
}

/** Build a Cartesian3 list at a given height (meters above the ellipsoid),
 *  skipping any non-finite or out-of-range coordinates. */
function llh(pts: number[][], h: number): Cesium.Cartesian3[] {
  const out: Cesium.Cartesian3[] = [];
  for (const p of pts) {
    if (!isGeoValid(p[1], p[0])) continue;
    out.push(Cesium.Cartesian3.fromDegrees(p[0], p[1], h));
  }
  return out;
}
/** Generate a red triangle pin marker (canvas), anchored at its tip. */
function makePinIcon(_hex: string): { canvas: HTMLCanvasElement; height: number } {
  const s = 48;
  const canvas = document.createElement('canvas');
  canvas.width = s;
  canvas.height = s;
  const g = canvas.getContext('2d')!;
  g.clearRect(0, 0, s, s);
  const cx = s / 2;
  const top = 4;
  const bottom = s - 4;
  g.beginPath();
  g.moveTo(cx, bottom);
  g.lineTo(cx - 14, top);
  g.lineTo(cx + 14, top);
  g.closePath();
  g.fillStyle = '#ff3333';
  g.fill();
  g.strokeStyle = '#ffffff';
  g.lineWidth = 1.5;
  g.stroke();
  return { canvas, height: s };
}
// ---- Free satellite imagery providers (swap any of these for another URL) ----
const DAY_BASEMAP =
  'https://services.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer';
const NIGHT_BASEMAP =
  'https://services.arcgisonline.com/ArcGIS/rest/services/Canvas/World_Dark_Gray_Base/MapServer';
// Reference labels overlay (country/city names), designed to sit on top of
// satellite imagery. Same style family as the night canvas' baked-in labels.
const REF_LABELS =
  'https://services.arcgisonline.com/ArcGIS/rest/services/Reference/World_Boundaries_and_Places/MapServer';

// Camera height bounds. min = ~129 km (just above the globe), max = ~38,268 km
// (whole Earth). Derived from the original globe.gl 1.02x-7x radius limits.
const GLOBE_RADIUS = 6_378_137;
const MIN_HEIGHT = GLOBE_RADIUS * 0.02 + 2000; // ~129 km
const MAX_HEIGHT = GLOBE_RADIUS * 6; // ~38,268 km
const CITY_HEIGHT = GLOBE_RADIUS * 0.1; // city labels/dots below ~638 km

export function initGlobe(container: HTMLElement): GlobeHandle {
  // Allow more parallel tile requests to the imagery server so the globe
  // fills in faster without reducing image quality.
  Cesium.RequestScheduler.maximumRequestsPerServer = 32;
  Cesium.RequestScheduler.maximumRequests = 128;
  // ---- Viewer (no Ion: we bring our own free imagery providers) ----
  const viewer = new Cesium.Viewer(container, {
    baseLayer: false, // do not request the default Cesium Ion basemap
    terrainProvider: new Cesium.EllipsoidTerrainProvider(), // smooth ellipsoid
    animation: false,
    timeline: false,
    geocoder: false,
    homeButton: false,
    sceneModePicker: false,
    baseLayerPicker: false,
    navigationHelpButton: false,
    fullscreenButton: false,
    infoBox: false,
    selectionIndicator: false,
    shouldAnimate: true,
  });

  const scene = viewer.scene;
  scene.globe.depthTestAgainstTerrain = false;
  // Load coarse tiles first for a fast first paint, then refine to full
  // quality shortly after.
  scene.globe.maximumScreenSpaceError = 16;
  scene.globe.preloadAncestors = true;
  scene.globe.preloadSiblings = true;
  scene.globe.tileCacheSize = 1000;
  scene.globe.showWaterEffect = false;
  // Use a dark "ocean" base color so areas where the coarse imagery hasn't
  // loaded (or is transparent) stay dark instead of flashing pale white.
  scene.globe.baseColor = Cesium.Color.fromCssColorString('#0a1626');
  scene.screenSpaceCameraController.minimumZoomDistance = MIN_HEIGHT;
  scene.screenSpaceCameraController.maximumZoomDistance = MAX_HEIGHT;
  scene.screenSpaceCameraController.inertiaSpin = 0.5;
  scene.screenSpaceCameraController.inertiaTranslate = 0.5;
  scene.screenSpaceCameraController.inertiaZoom = 0.4;

  // Dark space backdrop (matches the old night-sky look).
  viewer.scene.backgroundColor = Cesium.Color.fromCssColorString('#05070d');
  // Disable fog so the horizon doesn't trigger extra tile requests.
  viewer.scene.fog.enabled = false;
  // The ground-atmosphere haze washes the entire globe out to a pale white
  // sheet when the camera is far away — disable it so the imagery keeps its
  // true colours at every zoom level. Keep only a thin, dimmed sky rim for
  // the limb glow around the edge of the planet.
  viewer.scene.globe.showGroundAtmosphere = false;
  if (viewer.scene.skyAtmosphere) {
    viewer.scene.skyAtmosphere.show = true;
    viewer.scene.skyAtmosphere.brightnessShift = -0.35;
    viewer.scene.skyAtmosphere.saturationShift = 0.1;
  }

  const ellipsoid = scene.globe.ellipsoid;
  const entities = viewer.entities;

  // ---- Imagery layers (day + night + optional graticule) ----
  let dayLayer: Cesium.ImageryLayer | null = null;
  let nightLayer: Cesium.ImageryLayer | null = null;
  let gridLayer: Cesium.ImageryLayer | null = null;
  let dayMode = true;
  let brightness = 1.0; // 1.0 = direct, unmodified imagery (no muddy tint)
  let contrast = 1.0;

  async function ensureDayLayer() {
    if (dayLayer) return;
    const prov = await Cesium.ArcGisMapServerImageryProvider.fromUrl(DAY_BASEMAP, {
      enablePickFeatures: false,
    } as any);
    dayLayer = viewer.imageryLayers.addImageryProvider(prov);
    dayLayer.show = dayMode;
    applyImagery();
    raiseLabelsToTop();
  }
  async function ensureNightLayer() {
    if (nightLayer) return;
    const prov = await Cesium.ArcGisMapServerImageryProvider.fromUrl(NIGHT_BASEMAP, {
      enablePickFeatures: false,
    } as any);
    nightLayer = viewer.imageryLayers.addImageryProvider(prov);
    nightLayer.show = !dayMode;
    applyImagery();
    raiseLabelsToTop();
  }
  // Load only the day basemap first; pull in the label overlay afterwards so
  // the two tile streams don't compete on initial load.
  void ensureDayLayer().then(() => void ensureRefLabels());

  // Tiled place-label overlay (country + city names). Loaded lazily; shown
  // only on the day globe when labels are enabled (the night canvas already
  // has labels baked into its tiles).
  let refLabelsLayer: Cesium.ImageryLayer | null = null;
  let refLabelsVisible = true;
  function raiseLabelsToTop() {
    // The day/night basemaps load asynchronously, so whichever layer finishes
    // loading last sits on top and can completely cover the labels. Always
    // push the label overlay back to the top of the imagery stack.
    if (refLabelsLayer) viewer.imageryLayers.raiseToTop(refLabelsLayer);
  }
  async function ensureRefLabels() {
    if (refLabelsLayer) return;
    const prov = await Cesium.ArcGisMapServerImageryProvider.fromUrl(REF_LABELS, {
      enablePickFeatures: false,
    } as any);
    refLabelsLayer = viewer.imageryLayers.addImageryProvider(prov);
    refLabelsLayer.show = dayMode && refLabelsVisible;
    raiseLabelsToTop();
  }

  function refreshRefLabels() {
    if (refLabelsLayer) {
      refLabelsLayer.show = dayMode && refLabelsVisible;
      raiseLabelsToTop();
      return;
    }
    void ensureRefLabels();
  }

  function applyBrightness(value: number) {
    brightness = value;
    applyImagery();
  }
  function applyContrast(value: number) {
    contrast = value;
    applyImagery();
  }

  /**
   * Apply the user's brightness/contrast to the imagery layers at 1:1 — no
   * zoom-dependent ramp (the ramp was dulling/greying the whole globe). The
   * day layer additionally gets a saturation boost so oceans stay richly blue
   * and land stays green/lush instead of washed out.
   */
  function applyImagery() {
    for (const layer of [dayLayer, nightLayer]) {
      if (!layer) continue;
      layer.brightness = brightness;
      layer.contrast = contrast;
      layer.saturation = layer === dayLayer ? 1.25 : 1.0;
      layer.gamma = 1.0;
    }
  }

  function applyDayMode(day: boolean) {
    dayMode = day;
    if (dayLayer) dayLayer.show = day;
    if (nightLayer) nightLayer.show = !day;
    else if (!day) void ensureNightLayer();
    // Lighting is always disabled so daytime imagery is lit uniformly across
    // the whole globe (no sun terminator / day-night shadow boundary).
    scene.globe.enableLighting = false;
    refreshRefLabels();
  }

  function setGraticuleVisible(on: boolean) {
    if (on && !gridLayer) {
      gridLayer = viewer.imageryLayers.addImageryProvider(
        new Cesium.GridImageryProvider({
          color: Cesium.Color.fromCssColorString('#3b4460').withAlpha(0.35),
          glowColor: Cesium.Color.fromCssColorString('#6366f1').withAlpha(0.15),
          cells: 6,
        }),
      );
      gridLayer.show = true;
    } else if (gridLayer) {
      gridLayer.show = on;
    }
  }

  // ---- Camera helpers ----
  function camHeight(): number {
    try {
      return viewer.camera.positionCartographic.height;
    } catch {
      return 0;
    }
  }

  function zoomPercent(): number {
    const h = clamp(camHeight(), MIN_HEIGHT, MAX_HEIGHT);
    const f =
      (Math.log(MAX_HEIGHT) - Math.log(h)) /
      (Math.log(MAX_HEIGHT) - Math.log(MIN_HEIGHT));
    return Math.round(clamp(f, 0, 1) * 100);
  }
// ---- Overlay entities state + tag lookup ----
  const overlayEntities = new Set<Cesium.Entity>();
  const tagBy = new WeakMap<Cesium.Entity, OverlayTag>();

  let allLines: ACGLine[] = [];
  let allLocalSpace: LocalSpaceRay[] = [];
  let allParans: Paran[] = [];
  let subPoints: PointDatum[] = [];
  let birthPoint: PointDatum | null = null;
  let birthRing: RingDatum[] = [];
  let pinRings: RingDatum[] = [];
  let pinItems: { id?: string; lat: number; lng: number; color: string }[] = [];
  let cityList: PointDatum[] = [];
  let localSpaceVisible = false;
  let paransVisible = true;
  let lastBirth = { lat: 0, lng: 0 };
  let autoRotate = false;
  let pinModeActive = false;

  // Advanced overlay datasets + visibility flags.
  let allTransit: ACGLine[] = [];
  let allProgressed: ACGLine[] = [];
  let allGeodetic: ACGLine[] = [];
  let allFixedStars: ACGLine[] = [];
  let allMidpoints: ACGLine[] = [];
  let allCompare: ACGLine[] = [];
  let allSolarReturn: ACGLine[] = [];
  let allLunarReturn: ACGLine[] = [];
  let solarReturnVisible = false;
  let lunarReturnVisible = false;
  let crossings: import('./types').Crossing[] = [];
  let crossingsVisible = false;
  let transitVisible = false;
  let progressedVisible = false;
  let geodeticVisible = false;
  let fixedStarsVisible = false;
  let midpointsVisible = false;
  let compareVisible = false;

  const visiblePlanets = new Set<string>();
  const visibleAngles = new Set<string>(['MC', 'IC', 'ASC', 'DSC']);

  function lightenHex(hex: string, amount: number): string {
    let h = hex.replace('#', '');
    if (h.length === 3) h = h.split('').map((c) => c + c).join('');
    const n = parseInt(h, 16);
    const r = (n >> 16) & 255;
    const g = (n >> 8) & 255;
    const b = n & 255;
    const mix = (c: number) => Math.round(c + (255 - c) * amount);
    return `#${[mix(r), mix(g), mix(b)].map((v) => v.toString(16).padStart(2, '0')).join('')}`;
  }

  /** Boost a hex color's saturation (and slightly darken) for vibrant lines. */
  function saturateHex(hex: string, amount = 1.45): string {
    let h = hex.replace('#', '');
    if (h.length === 3) h = h.split('').map((c) => c + c).join('');
    const n = parseInt(h, 16);
    let r = ((n >> 16) & 255) / 255;
    let g = ((n >> 8) & 255) / 255;
    let b = (n & 255) / 255;
    const max = Math.max(r, g, b);
    const min = Math.min(r, g, b);
    const l = (max + min) / 2;
    if (max === min) return `#${h}`; // pure gray — leave as-is
    const d = max - min;
    const s = l > 0.5 ? d / (2 - max - min) : d / (max + min);
    const s2 = Math.min(1, s * amount);
    const l2 = l * 0.92; // slight darkening for punch
    const hue2rgb = (p: number, q: number, t: number): number => {
      let x = t;
      if (x < 0) x += 1;
      if (x > 1) x -= 1;
      if (x < 1 / 6) return p + (q - p) * 6 * x;
      if (x < 1 / 2) return q;
      if (x < 2 / 3) return p + (q - p) * (2 / 3 - x) * 6;
      return p;
    };
    let r2 = l2;
    let g2 = l2;
    let b2 = l2;
    if (s2 > 0) {
      const q = l2 < 0.5 ? l2 * (1 + s2) : l2 + s2 - l2 * s2;
      const p = 2 * l2 - q;
      // recover hue from original rgb
      let hr = max === r ? ((g - b) / d) % 6 : max === g ? (b - r) / d + 2 : (r - g) / d + 4;
      hr /= 6;
      if (hr < 0) hr += 1;
      r2 = hue2rgb(p, q, hr + 1 / 3);
      g2 = hue2rgb(p, q, hr);
      b2 = hue2rgb(p, q, hr - 1 / 3);
    }
    const to255 = (v: number) => Math.round(v * 255).toString(16).padStart(2, '0');
    return `#${to255(r2)}${to255(g2)}${to255(b2)}`;
  }

  /** Remove every entity that the globe owns. */
  function clearOverlay() {
    for (const t of ringTimers) window.clearInterval(t);
    ringTimers.length = 0;
    for (const e of overlayEntities) {
      entities.remove(e);
    }
    overlayEntities.clear();
  }

  function addEntity(graphics: Cesium.Entity.ConstructorOptions, tag?: OverlayTag): Cesium.Entity {
    const entity = entities.add(graphics);
    overlayEntities.add(entity);
    if (tag) tagBy.set(entity, tag);
    return entity;
  }

  function addLine(
    coords: number[][],
    color: string,
    _widthGlow: number,
    widthCore: number,
    _glowColor: string,
    tag: OverlayTag,
  ): void {
    // Solid vibrant lines only — no glow underlay. (The old translucent glow
    // polyline caused white streak artifacts and washed the colors out.)
    const vibrant = saturateHex(color);
    if (tag.kind === 'line') tag.color = vibrant;
    for (const seg of splitCoords(coords)) {
      if (seg.length < 2) continue;
      const pos = llh(seg, 240); // lift just above the imagery to avoid z-fighting
      addEntity(
        {
          polyline: {
            positions: pos,
            width: widthCore,
            arcType: Cesium.ArcType.NONE,
            material: new Cesium.ColorMaterialProperty(col(vibrant, 1)),
          },
        },
        tag,
      );
    }
  }

  function pushMainLine(paths: number[][], color: string, planetValue: string, angleValue: string): void {
    const tag: OverlayTag = { kind: 'line', planet: planetValue, angle: angleValue, color };
    addLine(paths, color, 14, 3.2, color, tag);
  }

  function pushOverlayLine(paths: number[][], color: string, planetValue: string, angleValue: string): void {
    const tag: OverlayTag = { kind: 'line', planet: planetValue, angle: angleValue, color };
    addLine(paths, color, 0, 2.4, color, tag);
  }

  function addPoint(d: PointDatum, pixel: number): void {
    if (!isGeoValid(d.latitude, d.longitude)) return;
    addEntity(
      {
        position: Cesium.Cartesian3.fromDegrees(d.longitude, d.latitude, 2500),
        point: {
          pixelSize: pixel,
          color: col(d.color, 1),
          outlineColor: Cesium.Color.fromCssColorString('#ffffff').withAlpha(0.55),
          outlineWidth: 0.5,
          // Depth-tested against the globe so far-side markers are hidden.
        },
      },
      { kind: 'point', datum: d },
    );
  }

  function addPulseRing(r: RingDatum, phaseOffsetMs: number): void {
    if (!isGeoValid(r.lat, r.lng)) return;
    const baseKm = 90;
    const period = 1400;
    // NOTE: Cesium's dynamic-ellipse pipeline can internally sample semiMajor
    // and semiMinor at different times, which throws
    // "semiMajorAxis must be greater than or equal to the semiMinorAxis" even
    // when both come from the same callback. So we NEVER animate the axes via
    // CallbackProperty. Instead both axes are plain ConstantProperties that we
    // step together from a single timer (always the same number), and only the
    // ring's alpha is animated via CallbackProperty (safe, color-only).
    const axisMajor = new Cesium.ConstantProperty(baseKm * 1000 * 0.15);
    const axisMinor = new Cesium.ConstantProperty(baseKm * 1000 * 0.15);
    const ellipse = {
      semiMajorAxis: axisMajor,
      semiMinorAxis: axisMinor,
      material: new Cesium.ColorMaterialProperty(
        new Cesium.CallbackProperty(
          () => col(r.color, Math.max(0, 0.9 * (1 - (((Date.now() + phaseOffsetMs) % period) / period)))),
          false,
        ),
      ),
    } as unknown as Cesium.EllipseGraphics;
    const step = (): void => {
      const t = ((Date.now() + phaseOffsetMs) % period) / period;
      // One value for BOTH axes, set together -> semiMajor can never be < semiMinor.
      const axis = baseKm * 1000 * (0.15 + 0.85 * t);
      axisMajor.setValue(axis);
      axisMinor.setValue(axis);
    };
    step();
    const timer = window.setInterval(step, 80);
    ringTimers.push(timer);
    addEntity({ position: Cesium.Cartesian3.fromDegrees(r.lng, r.lat, 0), ellipse }, { kind: 'ring' });
  }

  let nextPinIcon = 0;
  const ringTimers: number[] = [];
  function addPin(p: { id?: string; lat: number; lng: number; color: string }): void {
    if (!isGeoValid(p.lat, p.lng)) return;
    const icon = makePinIcon(p.color);
    addEntity(
      {
        position: Cesium.Cartesian3.fromDegrees(p.lng, p.lat, 0),
        billboard: {
          image: icon.canvas,
          verticalOrigin: Cesium.VerticalOrigin.BOTTOM,
          scale: 1.2,
        },
      },
      { kind: 'pin', id: p.id ?? `pin-${nextPinIcon++}` },
    );
  }
// ---- Line dataset selection (core ACG + local space + advanced overlays) ----
  function repaintLines() {
    for (const l of allLines) {
      if (!visiblePlanets.has(l.planet) || !visibleAngles.has(l.angle)) continue;
      const coords = l.geometry.coordinates; // [lon, lat][]
      pushMainLine(coords, l.color, l.planet, l.angle);
    }
    if (localSpaceVisible) {
      for (const ls of allLocalSpace) {
        if (!visiblePlanets.has(ls.planet)) continue;
        pushOverlayLine(ls.geometry.coordinates, ls.color, ls.planet, 'Local');
      }
    }
    if (transitVisible) {
      // Overlay layers are independent of the natal planet/angle legend.
      for (const l of allTransit) {
        pushOverlayLine(l.geometry.coordinates, l.color, l.planet, l.angle);
      }
    }
    if (progressedVisible) {
      for (const l of allProgressed) {
        pushOverlayLine(l.geometry.coordinates, lightenHex(l.color, 0.45), l.planet, l.angle);
      }
    }
    if (geodeticVisible) {
      for (const l of allGeodetic) {
        pushOverlayLine(l.geometry.coordinates, l.color || '#6ea8ff', l.planet, l.angle);
      }
    }
    if (fixedStarsVisible) {
      for (const l of allFixedStars) {
        pushOverlayLine(l.geometry.coordinates, l.color || '#c9a0ff', l.planet, l.angle);
      }
    }
    if (midpointsVisible) {
      for (const l of allMidpoints) {
        pushOverlayLine(l.geometry.coordinates, l.color || '#5fe3c0', l.planet, l.angle);
      }
    }
    if (compareVisible) {
      // Second person's natal lines, lightened so they read as "theirs".
      for (const l of allCompare) {
        pushOverlayLine(l.geometry.coordinates, lightenHex(l.color || '#ffffff', 0.3), l.planet, l.angle);
      }
    }
    if (solarReturnVisible) {
      for (const l of allSolarReturn) {
        pushOverlayLine(l.geometry.coordinates, lightenHex(l.color || '#ffe066', 0.2), l.planet, l.angle);
      }
    }
    if (lunarReturnVisible) {
      for (const l of allLunarReturn) {
        pushOverlayLine(l.geometry.coordinates, lightenHex(l.color || '#a0d8ff', 0.2), l.planet, l.angle);
      }
    }
  }

  function repaintPoints() {
    for (const s of subPoints) addPoint(s, 8);
    if (birthPoint) addPoint(birthPoint, 10);
    if (paransVisible) {
      for (const p of allParans) {
        addPoint(
          {
            latitude: p.latitude,
            longitude: p.longitude,
            color: '#FFC500',
            paran: true,
            planet_a: p.planet_a,
            circle_a: p.circle_a,
            planet_b: p.planet_b,
            circle_b: p.circle_b,
          },
          9,
        );
      }
    }
    if (crossingsVisible) {
      for (const c of crossings) {
        const color = c.type === 'paran' ? '#ff9500' : '#ff55ff';
        addPoint(
          {
            latitude: c.latitude,
            longitude: c.longitude,
            color,
            paran: c.type === 'paran',
            planet_a: c.planet_a,
            circle_a: c.angle_a,
            planet_b: c.planet_b,
            circle_b: c.angle_b,
            interpretation: c.interpretation,
            crossingType: c.type,
          },
          11,
        );
      }
    }
    // City dots only when zoomed in close (mirrors the original behaviour).
    const cityShow = () => camHeight() <= CITY_HEIGHT;
    for (const c of cityList) {
      if (!isGeoValid(c.latitude, c.longitude)) continue;
      const cShow = () => cityShow();
      addEntity(
        {
          position: Cesium.Cartesian3.fromDegrees(c.longitude, c.latitude, 1200),
          point: {
            pixelSize: 3,
            color: col(c.color || '#ffffff', 0.7),
            // Depth-tested against the globe so far-side city dots are hidden.
            show: new Cesium.CallbackProperty(cShow, false),
          },
        },
        { kind: 'point', datum: c },
      );
    }
  }

  function repaintRings() {
    birthRing.forEach((r, i) => addPulseRing(r, i * 220));
    pinRings.forEach((r, i) => addPulseRing(r, i * 260 + 110));
  }

  function repaintPins() {
    pinItems.forEach((p) => addPin(p));
  }

  function repaint() {
    clearOverlay();
    repaintLines();
    repaintPoints();
    repaintRings();
    repaintPins();
    rebuildLabels();
  }

  // ---- Label overlay (country + city names) ----
  function rebuildLabels() {
    // Custom label entities removed — place labels now come from the Esri
    // tiled reference layer (ensureRefLabels), which is dynamic and matches
    // the night canvas' baked-in labels.
  }
// ---- Input: hover (distinguish line / point / empty globe) + click ----
  const handler = new Cesium.ScreenSpaceEventHandler(viewer.scene.canvas);

  let hoverCb: ((info: HoverInfo | null) => void) | null = null;
  let clickCb: ((info: ClickInfo) => void) | null = null;
  let pinClickCb: ((id: string) => void) | null = null;
  const dispatch = (info: HoverInfo | null) => {
    if (hoverCb) hoverCb(info);
  };

  const geoFromPick = (pos: Cesium.Cartesian2 | undefined): { lat: number; lng: number } | null => {
    if (!pos) return null;
    const cart = viewer.camera.pickEllipsoid(pos, ellipsoid);
    if (!cart) return null;
    const g = Cesium.Cartographic.fromCartesian(cart);
    if (Number.isNaN(g.longitude) || Number.isNaN(g.latitude)) return null;
    return {
      lat: Cesium.Math.toDegrees(g.latitude),
      lng: Cesium.Math.toDegrees(g.longitude),
    };
  };

  // scene.pick throws if given an undefined window position; this wrapper is
  // defensive so a stale/empty cursor position never crashes the render loop.
  const safePick = (pos: Cesium.Cartesian2 | undefined): any => {
    if (!pos) return undefined;
    try {
      return viewer.scene.pick(pos);
    } catch {
      return undefined;
    }
  };

  // MOUSE_MOVE is a MotionEvent: its current cursor position is `endPosition`.
  handler.setInputAction((movement: Cesium.ScreenSpaceEventHandler.MotionEvent) => {
    const pos = movement?.endPosition;
    const picked = safePick(pos);
    const ent = picked && picked.id instanceof Cesium.Entity ? picked.id : null;
    const tag = ent ? tagBy.get(ent) : undefined;

    if (tag && tag.kind === 'line') {
      dispatch({ type: 'line', planet: tag.planet, angle: tag.angle, color: tag.color });
      return;
    }
    if (tag && tag.kind === 'point') {
      dispatch({ type: 'point', point: tag.datum });
      return;
    }
    if (tag && tag.kind === 'pin') {
      viewer.scene.canvas.style.cursor = 'pointer';
      return;
    }

    const geo = geoFromPick(pos);
    if (geo) dispatch({ type: 'globe', lat: geo.lat, lng: geo.lng });
    else dispatch(null);
  }, Cesium.ScreenSpaceEventType.MOUSE_MOVE);

  // LEFT_CLICK is a PositionedEvent: the click position is `position`.
  handler.setInputAction((movement: Cesium.ScreenSpaceEventHandler.PositionedEvent) => {
    if (!pinModeActive) return; // matches original: clicks only fire the Pin tool
    const pos = movement?.position;
    const picked = safePick(pos);
    const ent = picked && picked.id instanceof Cesium.Entity ? picked.id : null;
    const tag = ent ? tagBy.get(ent) : undefined;
    if (tag && tag.kind === 'pin') {
      if (pinClickCb) pinClickCb(tag.id);
      return;
    }
    const geo = geoFromPick(pos);
    if (geo && clickCb) clickCb({ type: 'click', lat: geo.lat, lng: geo.lng });
  }, Cesium.ScreenSpaceEventType.LEFT_CLICK);

  // ---- Camera behaviour ----
  const flyTo = (lat: number, lng: number, height: number, durationMs = 900) => {
    viewer.camera.flyTo({
      destination: Cesium.Cartesian3.fromDegrees(lng, lat, height),
      orientation: {
        heading: 0,
        pitch: -Cesium.Math.PI_OVER_TWO, // look straight down
        roll: 0.0,
      },
      duration: durationMs / 1000,
    });
  };
  const zoom = (factor: number) => {
    const h = clamp(camHeight() * factor, MIN_HEIGHT, MAX_HEIGHT);
    flyTo(lastBirth.lat, lastBirth.lng, h, 300);
  };

  // Notify the UI whenever the camera zoom level changes.
  let zoomChangeCb: ((pct: number) => void) | null = null;
  viewer.camera.changed.addEventListener(() => {
    applyImagery();
    if (zoomChangeCb) zoomChangeCb(zoomPercent());
  });

  // Gentle auto-rotation while enabled.
  viewer.scene.preUpdate.addEventListener(() => {
    if (autoRotate) viewer.camera.rotate(Cesium.Cartesian3.UNIT_Z, -0.00035);
  });

  // Keep the canvas sized with its container.
  window.addEventListener('resize', () => viewer.resize());

  // Initial view (boot() will fly to the birth place on the first draw).
  flyTo(-27.47, 153.026, 3e6, 0);

  // Progressive refinement: start coarse for a fast first paint, then switch to
  // full-quality tiles once the initial view has had time to stream in.
  window.setTimeout(() => {
    scene.globe.maximumScreenSpaceError = 1;
  }, 1200);

  // ---- Public handle (preserves the original GlobeHandle contract) ----
  return {
setData(data: ACGResponse, birth: { lat: number; lng: number }) {
      allLines = data.lines;
      allLocalSpace = data.local_space;
      allParans = data.parans;
      subPoints = data.subplanetary_points.map((s: SubPoint): PointDatum => ({
        planet: s.planet,
        type: s.type,
        latitude: s.latitude,
        longitude: s.longitude,
        color: s.color,
      }));
      birthPoint = {
        birth: true,
        planet: 'Birth place',
        latitude: birth.lat,
        longitude: birth.lng,
        color: '#ffffff',
      };
      birthRing = [{ lat: birth.lat, lng: birth.lng, color: '#ffffff' }];
      lastBirth = { lat: birth.lat, lng: birth.lng };
      visiblePlanets.clear();
      data.lines.forEach((l) => visiblePlanets.add(l.planet));
      repaint();
      flyTo(birth.lat, birth.lng, 3e6, 1000);
    },
    setPlanetVisible(planet: string, visible: boolean) {
      if (visible) visiblePlanets.add(planet);
      else visiblePlanets.delete(planet);
      repaint();
    },
    setAngleVisible(angle: string, visible: boolean) {
      if (visible) visibleAngles.add(angle);
      else visibleAngles.delete(angle);
      repaint();
    },
    setLocalSpaceVisible(on: boolean) {
      localSpaceVisible = on;
      repaint();
    },
    setParansVisible(on: boolean) {
      paransVisible = on;
      repaint();
    },
    setDayMode(day: boolean) {
      applyDayMode(day);
    },
    setBrightness(value: number) {
      applyBrightness(value);
    },
    setContrast(value: number) {
      applyContrast(value);
    },
    setAutoRotate(on: boolean) {
      autoRotate = on;
    },
    focusBirth(lat: number, lng: number) {
      if (!Number.isFinite(lat) || !Number.isFinite(lng)) return;
      flyTo(lat, lng, 3e6, 1000);
    },
    resetView() {
      flyTo(lastBirth.lat, lastBirth.lng, 3e6, 1000);
    },
    setGraticuleVisible(on: boolean) {
      setGraticuleVisible(on);
    },
    getPlanets(): string[] {
      return [...visiblePlanets];
    },
    setHoverHandler(cb: ((info: HoverInfo | null) => void) | null) {
      hoverCb = cb;
    },
    setClickHandler(cb: ((info: ClickInfo) => void) | null) {
      clickCb = cb;
    },
    setPinClickHandler(cb: ((id: string) => void) | null) {
      pinClickCb = cb;
    },
    setPins(pins: { id?: string; lat: number; lng: number; color: string }[]) {
      pinItems = pins;
      pinRings = pins.map((p) => ({ lat: p.lat, lng: p.lng, color: p.color }));
      repaint();
    },
    zoom(factor: number) {
      zoom(factor);
    },
    getZoomPercent() {
      return zoomPercent();
    },
    onZoomChange(cb: ((pct: number) => void) | null) {
      zoomChangeCb = cb;
    },
    preloadTextures(_onProgress?: (frac: number) => void): Promise<void> {
      return (async () => {
        await ensureDayLayer();
        const prevSSE = scene.globe.maximumScreenSpaceError;
        scene.globe.maximumScreenSpaceError = 2;
        viewer.camera.setView({ destination: Cesium.Cartesian3.fromDegrees(0, 0, GLOBE_RADIUS * 6) });
        const onProgress = _onProgress;
        await new Promise<void>((resolve) => {
          let done = false;
          const finish = () => { if (!done) { done = true; resolve(); } };
          const sub = scene.globe.tileLoadProgressEvent.addEventListener((pending: number) => {
            if (pending === 0) { onProgress?.(1); finish(); }
            else { onProgress?.(Math.max(0, 1 - pending / 200)); }
          });
          const interval = window.setInterval(() => viewer.scene.requestRender(), 100);
          const timeout = window.setTimeout(() => { window.clearInterval(interval); try { sub(); } catch {} finish(); }, 90000);
          const check = window.setInterval(() => {
            if (scene.globe.tilesLoaded) {
              window.clearInterval(check); window.clearInterval(interval); window.clearTimeout(timeout);
              try { sub(); } catch {} onProgress?.(1); finish();
            }
          }, 200);
        });
        scene.globe.maximumScreenSpaceError = 1;
        viewer.camera.setView({ destination: Cesium.Cartesian3.fromDegrees(0, 20, GLOBE_RADIUS * 2.5) });
      })();
    },
    setLabels(data: { countries: any[]; cities: any[] }) {
      // Custom label entities removed — labels come from the Esri tiled
      // reference layer. Only the city dot list is still needed here.
      cityList = (data.cities || []).map((c: any) => ({
        ...c,
        type: 'city',
        color: 'rgba(255,255,255,0.7)',
      }));
      repaint();
    },
    setLabelsVisible(on: boolean) {
      refLabelsVisible = on;
      refreshRefLabels();
      viewer.scene.requestRender();
    },
    setCursor(cursor: string) {
      viewer.scene.canvas.style.cursor = cursor;
    },
    setPinMode(on: boolean) {
      pinModeActive = on;
    },
    setCrosshairVisible(on: boolean) {
      const el = document.getElementById('crosshair');
      if (el) el.setAttribute('data-visible', String(on));
    },
    setCrossings(data: { crossings: import('./types').Crossing[] }) {
      crossings = data.crossings || [];
      repaint();
    },
    setCrossingsVisible(on: boolean) {
      crossingsVisible = on;
      repaint();
    },
    setSolarReturnData(data: { lines: ACGLine[] }) {
      allSolarReturn = data.lines || [];
      repaint();
    },
    setSolarReturnVisible(on: boolean) {
      solarReturnVisible = on;
      repaint();
    },
    setLunarReturnData(data: { lines: ACGLine[] }) {
      allLunarReturn = data.lines || [];
      repaint();
    },
    setLunarReturnVisible(on: boolean) {
      lunarReturnVisible = on;
      repaint();
    },
    captureImage(): string {
      // Re-render synchronously so the canvas buffer is current, then read it.
      viewer.scene.requestRender();
      viewer.scene.render();
      return viewer.scene.canvas.toDataURL('image/png');
    },
    setCities(cities: any[]) {
      cityList = cities.map((c: any) => ({
        ...c,
        type: 'city',
        color: 'rgba(255,255,255,0.7)',
      }));
      repaint();
    },
    setTransitData(data: { lines: ACGLine[] }) {
      allTransit = data.lines || [];
      repaint();
    },
    setProgressedData(data: { lines: ACGLine[] }) {
      allProgressed = data.lines || [];
      repaint();
    },
    setGeodeticData(data: { lines: ACGLine[] }) {
      allGeodetic = data.lines || [];
      repaint();
    },
    setFixedStarData(data: { lines: ACGLine[] }) {
      allFixedStars = data.lines || [];
      repaint();
    },
    setMidpointData(data: { lines: ACGLine[] }) {
      allMidpoints = data.lines || [];
      repaint();
    },
    setCompareData(data: { lines: ACGLine[] }) {
      allCompare = data.lines || [];
      repaint();
    },
    setCompareVisible(on: boolean) {
      compareVisible = on;
      repaint();
    },
    setTransitVisible(on: boolean) {
      transitVisible = on;
      repaint();
    },
    setProgressedVisible(on: boolean) {
      progressedVisible = on;
      repaint();
    },
    setGeodeticVisible(on: boolean) {
      geodeticVisible = on;
      repaint();
    },
    setFixedStarsVisible(on: boolean) {
      fixedStarsVisible = on;
      repaint();
    },
    setMidpointsVisible(on: boolean) {
      midpointsVisible = on;
      repaint();
    },
  };
}