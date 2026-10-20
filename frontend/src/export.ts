/**
 * Export & share helpers for the astrocartography frontend.
 *
 * - GeoJSON / KML conversion of ACG line payloads (client-side, no deps)
 * - File download plumbing (data URLs + Blob saves)
 * - Share-link encode/restore via the URL hash
 *
 * State shape (kept intentionally flat and future-proof):
 *   { b: { datetime, latitude, longitude }, w?: weights, g?: goalFocus }
 */

import type { ACGLine } from './types';

export interface ShareState {
  b?: { datetime: string; latitude: number; longitude: number };
  w?: Record<string, number>;
  g?: string;
}

// ---- Generic download plumbing -------------------------------------------

export function downloadBlob(blob: Blob, filename: string): void {
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = filename;
  document.body.appendChild(a);
  a.click();
  a.remove();
  setTimeout(() => URL.revokeObjectURL(url), 1000);
}

export function downloadText(text: string, filename: string, mime: string): void {
  downloadBlob(new Blob([text], { type: mime }), filename);
}

export function downloadDataURL(dataUrl: string, filename: string): void {
  const a = document.createElement('a');
  a.href = dataUrl;
  a.download = filename;
  document.body.appendChild(a);
  a.click();
  a.remove();
}

// ---- GeoJSON / KML conversion ---------------------------------------------

export function acgToGeoJSON(
  lines: ACGLine[],
  meta: Record<string, unknown> = {},
): string {
  const features = lines.map((line) => ({
    type: 'Feature',
    geometry: {
      type: 'LineString',
      coordinates: line.geometry?.coordinates ?? [],
    },
    properties: {
      planet: line.planet,
      angle: line.angle,
      color: line.color,
    },
  }));
  return JSON.stringify(
    { type: 'FeatureCollection', features, properties: meta },
    null,
    2,
  );
}

function escapeXml(s: string): string {
  return s
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;');
}

export function acgToKML(
  lines: ACGLine[],
  meta: Record<string, unknown> = {},
): string {
  const placemarks = lines
    .map((line) => {
      const coords = (line.geometry?.coordinates ?? [])
        .map(([lon, lat]) => `${lon},${lat},0`)
        .join(' ');
      const styleId = `style-${escapeXml(line.planet)}`;
      const name = `${line.planet} ${line.angle}`;
      const color = (line.color || '#ffaa00').replace('#', '');
      // KML AABBGGRR
      const kmlColor = `${color.slice(4, 6)}${color.slice(2, 4)}${color.slice(0, 2)}ff`;
      return `
  <Style id="${styleId}">
    <LineStyle><color>${kmlColor}</color><width>3</width></LineStyle>
  </Style>
  <Placemark>
    <name>${escapeXml(name)}</name>
    <styleUrl>#${styleId}</styleUrl>
    <LineString><tessellate>1</tessellate><coordinates>${coords}</coordinates></LineString>
  </Placemark>`;
    })
    .join('\n');
  return `<?xml version="1.0" encoding="UTF-8"?>
<kml xmlns="http://www.opengis.net/kml/2.2">
<Document>
  <name>${escapeXml(String(meta.title ?? 'Astrocartography lines'))}</name>${placemarks}
</Document>
</kml>`;
}

// ---- Share links ------------------------------------------------------------

export function encodeShareState(state: ShareState): string {
  const json = JSON.stringify(state);
  // btoa needs latin-1: escape unicode first.
  return btoa(unescape(encodeURIComponent(json)));
}

export function decodeShareState(hash: string): ShareState | null {
  if (!hash) return null;
  try {
    const raw = hash.startsWith('#') ? hash.slice(1) : hash;
    if (!raw) return null;
    const json = decodeURIComponent(escape(atob(raw)));
    const state = JSON.parse(json) as ShareState;
    if (!state.b || !state.b.datetime) return null;
    return state;
  } catch {
    return null;
  }
}

export function buildShareUrl(state: ShareState): string {
  return `${location.origin}${location.pathname}#s=${encodeShareState(state)}`;
}

export async function copyToClipboard(text: string): Promise<boolean> {
  try {
    await navigator.clipboard.writeText(text);
    return true;
  } catch {
    return false;
  }
}
