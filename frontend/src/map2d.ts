import L from 'leaflet';
import 'leaflet/dist/leaflet.css';
import type { ACGResponse, ACGLine, SubPoint } from './types';
import type { ClickInfo } from './globe';

export interface Map2DHandle {
  setData: (data: ACGResponse, birth: { lat: number; lng: number }) => void;
  setPlanetVisible: (planet: string, visible: boolean) => void;
  setAngleVisible: (angle: string, visible: boolean) => void;
  setLocalSpaceVisible: (on: boolean) => void;
  setParansVisible: (on: boolean) => void;
  resetView: () => void;
  focusLocation: (lat: number, lng: number, zoom?: number) => void;
  setClickHandler: (cb: ((info: ClickInfo) => void) | null) => void;
  setPins: (pins: { id?: string; lat: number; lng: number; color: string }[]) => void;
  setPinClickHandler: (cb: ((id: string) => void) | null) => void;
  invalidateSize: () => void;
  destroy: () => void;
  setCursor: (cursor: string) => void;
  setPinMode: (on: boolean) => void;
  setCities: (cities: any[]) => void;
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

export function initMap2D(container: HTMLElement): Map2DHandle {
  // Dark basemap tile layer (CartoDB Dark Matter)
  const map = L.map(container, {
    center: [20, 0],
    zoom: 2,
    minZoom: 2,
    maxZoom: 14,
    worldCopyJump: true,
    doubleClickZoom: false,
  });

  L.tileLayer('https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png', {
    attribution: '&copy; OpenStreetMap &copy; CARTO',
    subdomains: 'abcd',
    maxZoom: 19,
  }).addTo(map);

  const linesGroup = L.layerGroup().addTo(map);
  const subPointsGroup = L.layerGroup().addTo(map);
  const pinsGroup = L.layerGroup().addTo(map);
  const citiesGroup = L.layerGroup().addTo(map);

  let currentData: ACGResponse | null = null;
  let birthPos: { lat: number; lng: number } | null = null;
  let hiddenPlanets = new Set<string>();
  let hiddenAngles = new Set<string>();
  let overlayTransit: ACGLine[] = [];
  let overlayProgressed: ACGLine[] = [];
  let overlayGeodetic: ACGLine[] = [];
  let overlayFixedStars: ACGLine[] = [];
  let overlayMidpoints: ACGLine[] = [];
  let overlayCompare: ACGLine[] = [];
  let overlaySolarReturn: ACGLine[] = [];
  let overlayLunarReturn: ACGLine[] = [];
  let solarReturnVisible = false;
  let lunarReturnVisible = false;
  let crossings2d: import('./types').Crossing[] = [];
  let crossingsVisible = false;
  let transitVisible = false;
  let progressedVisible = false;
  let geodeticVisible = false;
  let fixedStarsVisible = false;
  let midpointsVisible = false;
  let compareVisible = false;
  let clickCallback: ((info: ClickInfo) => void) | null = null;
  let pinClickCb: ((id: string) => void) | null = null;
  let pinModeActive = false;

  map.on('click', (e: L.LeafletMouseEvent) => {
    if (pinModeActive && clickCallback) {
      clickCallback({ type: 'click', lat: e.latlng.lat, lng: e.latlng.lng });
    }
  });

  function render() {
    linesGroup.clearLayers();
    subPointsGroup.clearLayers();
    citiesGroup.clearLayers();

    // --- Advanced overlays --- (drawn independently of the natal chart so
    // they render even before "Draw chart" has produced currentData)
    const drawOverlay = (lines: ACGLine[], opts: { color: string; weight: number; opacity: number; dash?: string }) => {
      // Overlay layers are independent of the natal planet/angle legend.
      lines.forEach((line: ACGLine) => {
        const latLngs: [number, number][] = line.geometry.coordinates.map((c) => [c[1], c[0]]);
        if (!latLngs.length) return;
        L.polyline(latLngs, {
          color: line.color || opts.color,
          weight: opts.weight,
          opacity: opts.opacity,
          dashArray: opts.dash,
          smoothFactor: 1,
        }).addTo(linesGroup);
        // Wide, near-invisible hit area for easy hover.
        L.polyline(latLngs, {
          color: line.color || opts.color,
          weight: 14,
          opacity: 0.01,
          smoothFactor: 1,
          interactive: true,
        }).addTo(linesGroup).bindTooltip(`<b>${line.planet} ${line.angle}</b>`, {
          sticky: true,
          className: 'acg-2d-tooltip',
        });
      });
    };
    if (transitVisible) drawOverlay(overlayTransit, { color: '#ffffff', weight: 1.6, opacity: 0.6, dash: '6 6' });
    if (progressedVisible) drawOverlay(overlayProgressed, { color: '#cfd8ff', weight: 1.4, opacity: 0.5, dash: '2 6' });
    if (geodeticVisible) drawOverlay(overlayGeodetic, { color: '#6ea8ff', weight: 1.4, opacity: 0.5 });
    if (fixedStarsVisible) drawOverlay(overlayFixedStars, { color: '#c9a0ff', weight: 1.6, opacity: 0.65 });
    if (midpointsVisible) drawOverlay(overlayMidpoints, { color: '#5fe3c0', weight: 1.4, opacity: 0.6 });
    if (compareVisible) drawOverlay(overlayCompare, { color: '#ffd9a0', weight: 1.8, opacity: 0.55, dash: '8 6' });
    if (solarReturnVisible) drawOverlay(overlaySolarReturn, { color: '#ffe066', weight: 1.6, opacity: 0.55, dash: '4 4' });
    if (lunarReturnVisible) drawOverlay(overlayLunarReturn, { color: '#a0d8ff', weight: 1.4, opacity: 0.5, dash: '2 4' });

    // Crossing markers (points)
    if (crossingsVisible) {
      crossings2d.forEach((c: import('./types').Crossing) => {
        const color = c.type === 'paran' ? '#ff9500' : '#ff55ff';
        L.circleMarker([c.latitude, c.longitude], {
          radius: 5,
          color,
          fillColor: color,
          fillOpacity: 0.8,
          weight: 1.5,
        }).bindPopup(`<b>${c.planet_a} ${c.angle_a} × ${c.planet_b} ${c.angle_b}</b><br>${c.interpretation}`).addTo(linesGroup);
      });
    }

    if (!currentData) return;

    // 1. Draw ACG Lines
    currentData.lines.forEach((line: ACGLine) => {
      if (hiddenPlanets.has(line.planet) || hiddenAngles.has(line.angle)) return;

      const coords = line.geometry.coordinates; // [lng, lat]
      const latLngs: [number, number][] = coords.map(c => [c[1], c[0]]);

      // Outer glow line
      L.polyline(latLngs, {
        color: line.color,
        weight: 6,
        opacity: 0.35,
        smoothFactor: 1,
      }).addTo(linesGroup);

      // Core line
      const poly = L.polyline(latLngs, {
        color: line.color,
        weight: 2.5,
        opacity: 0.95,
        smoothFactor: 1,
      }).addTo(linesGroup);

      poly.bindTooltip(`<b>${line.planet} ${line.angle}</b>`, {
        sticky: true,
        className: 'acg-2d-tooltip',
      });

      // Wide, near-invisible hit area so the line is easy to hover.
      L.polyline(latLngs, {
        color: line.color,
        weight: 16,
        opacity: 0.01,
        smoothFactor: 1,
        interactive: true,
      }).addTo(linesGroup).bindTooltip(`<b>${line.planet} ${line.angle}</b>`, {
        sticky: true,
        className: 'acg-2d-tooltip',
      });
    });

    // 2. Draw Subplanetary points (Zenith/Nadir)
    currentData.subplanetary_points.forEach((pt: SubPoint) => {
      if (hiddenPlanets.has(pt.planet)) return;

      const marker = L.circleMarker([pt.latitude, pt.longitude], {
        radius: pt.type === 'Zenith' ? 7 : 5,
        color: pt.color,
        fillColor: pt.color,
        fillOpacity: 0.85,
        weight: 2,
      }).addTo(subPointsGroup);

      marker.bindTooltip(`<b>${pt.planet} (${pt.type})</b>`, {
        className: 'acg-2d-tooltip',
      });
    });

    // 3. Draw Birth Place Marker
    if (birthPos) {
      L.circleMarker([birthPos.lat, birthPos.lng], {
        radius: 8,
        color: '#ffffff',
        fillColor: '#6366f1',
        fillOpacity: 1,
        weight: 3,
      }).addTo(subPointsGroup).bindTooltip('<b>Birth Location</b>');
    }
  }

  return {
    setData: (data: ACGResponse, birth: { lat: number; lng: number }) => {
      currentData = data;
      birthPos = birth;
      render();
    },
    setPlanetVisible: (planet: string, visible: boolean) => {
      if (visible) hiddenPlanets.delete(planet);
      else hiddenPlanets.add(planet);
      render();
    },
    setAngleVisible: (angle: string, visible: boolean) => {
      if (visible) hiddenAngles.delete(angle);
      else hiddenAngles.add(angle);
      render();
    },
    setLocalSpaceVisible: () => { /* 2D simple toggle */ },
    setParansVisible: () => { /* 2D simple toggle */ },
    resetView: () => {
      map.setView([20, 0], 2);
    },
    focusLocation: (lat: number, lng: number, zoom: number = 6) => {
      if (!Number.isFinite(lat) || !Number.isFinite(lng)) return;
      map.flyTo([lat, lng], zoom, { duration: 1.5 });
    },
    setClickHandler: (cb) => {
      clickCallback = cb;
    },
      setPins: (pins) => {
        pinsGroup.clearLayers();
        pins.forEach(p => {
          const icon = L.divIcon({
            className: 'city-marker-2d',
            html: `<div style="width:10px;height:10px;border-radius:50%;background:${p.color};box-shadow:0 0 6px ${p.color};"></div>`,
            iconSize: [10, 10],
            iconAnchor: [5, 5],
          });
          const marker = L.marker([p.lat, p.lng], { icon }).addTo(pinsGroup);
          if (p.id != null && pinClickCb) {
            const cb = pinClickCb;
            const pid = p.id;
            marker.on('click', (e: L.LeafletMouseEvent) => {
              L.DomEvent.stopPropagation(e);
              cb(pid);
            });
          }
        });
      },
    setCursor: (cursor: string) => {
      map.getContainer().style.cursor = cursor;
    },
    setPinMode: (on: boolean) => {
      pinModeActive = on;
    },
    setPinClickHandler: (cb: ((id: string) => void) | null) => {
      pinClickCb = cb;
    },
    setCities: (cities) => {
      citiesGroup.clearLayers();
      cities.forEach((c: any) => {
        L.circleMarker([c.lat, c.lng], {
          radius: 3,
          color: 'rgba(255,255,255,0.7)',
          fillColor: 'rgba(255,255,255,0.7)',
          fillOpacity: 0.6,
          weight: 1,
        }).addTo(citiesGroup);
      });
    },
    setTransitData: (data) => { overlayTransit = data.lines || []; render(); },
    setProgressedData: (data) => { overlayProgressed = data.lines || []; render(); },
    setGeodeticData: (data) => { overlayGeodetic = data.lines || []; render(); },
    setFixedStarData: (data) => { overlayFixedStars = data.lines || []; render(); },
    setMidpointData: (data) => { overlayMidpoints = data.lines || []; render(); },
    setCompareData: (data) => { overlayCompare = data.lines || []; render(); },
    setCompareVisible: (on) => { compareVisible = on; render(); },
    setTransitVisible: (on) => { transitVisible = on; render(); },
    setProgressedVisible: (on) => { progressedVisible = on; render(); },
    setGeodeticVisible: (on) => { geodeticVisible = on; render(); },
    setFixedStarsVisible: (on) => { fixedStarsVisible = on; render(); },
    setMidpointsVisible: (on) => { midpointsVisible = on; render(); },
    setSolarReturnData: (data) => { overlaySolarReturn = data.lines || []; render(); },
    setLunarReturnData: (data) => { overlayLunarReturn = data.lines || []; render(); },
    setSolarReturnVisible: (on) => { solarReturnVisible = on; render(); },
    setLunarReturnVisible: (on) => { lunarReturnVisible = on; render(); },
    setCrossings: (data) => { crossings2d = data.crossings || []; render(); },
    setCrossingsVisible: (on) => { crossingsVisible = on; render(); },
    invalidateSize: () => {
      map.invalidateSize();
    },
    destroy: () => {
      map.remove();
    },
  };
}
