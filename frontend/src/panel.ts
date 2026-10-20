import type { LocationAnalysis, NearestLine, Paran, RelocationBlock, DomainScores, Crossing, TopCity } from './types';

const $ = (id: string) => document.getElementById(id) as HTMLElement;

function el(tag: string, cls?: string, text?: string): HTMLElement {
  const e = document.createElement(tag);
  if (cls) e.className = cls;
  if (text !== undefined) e.textContent = text;
  return e;
}

function section(title: string, sub?: string): HTMLElement {
  const s = el('div', 'report-section');
  const h = el('h3', 'report-h', title);
  s.appendChild(h);
  if (sub) s.appendChild(el('p', 'report-sub', sub));
  return s;
}

function bullet(text: string, swatch?: string): HTMLElement {
  const li = el('li', 'report-li');
  if (swatch) {
    const sp = el('span', 'swatch');
    sp.style.background = swatch;
    li.appendChild(sp);
  }
  li.appendChild(document.createTextNode(' ' + text));
  return li;
}

function pill(text: string, swatch?: string): HTMLElement {
  const p = el('span', 'pill');
  if (swatch) {
    const sp = el('span', 'swatch');
    sp.style.background = swatch;
    sp.style.boxShadow = 'none';
    p.appendChild(sp);
  }
  p.appendChild(document.createTextNode(text));
  return p;
}

function renderRelocation(block: RelocationBlock): HTMLElement {
  const s = section('Relocation', 'If you lived here, your chart would shift like this.');
  s.appendChild(el('p', 'report-text', block.summary));

  const a = block.angles;
  const grid = el('div', 'report-grid');
  const mk = (label: string, info: { sign: string }) =>
    el('div', 'report-cell', `${label}: ${info.sign}`);
  grid.append(mk('ASC', a.asc), mk('MC', a.mc), mk('DSC', a.dsc), mk('IC', a.ic));
  s.appendChild(grid);

  const notable = block.planets.filter((p) => p.notable);
  if (notable.length) {
    const ul = el('ul', 'report-list');
    notable.forEach((p) =>
      ul.appendChild(
        bullet(`${p.name} — ${p.sign} in house ${p.house}`),
      ),
    );
    s.appendChild(ul);
  }
  return s;
}

function renderNearest(lines: NearestLine[]): HTMLElement {
  const s = section('Lines near you', 'Astrocartography lines passing close to this spot.');
  if (!lines.length) {
    s.appendChild(el('p', 'report-text', 'No major lines within ~1000 km.'));
    return s;
  }
  const ul = el('ul', 'report-list');
  lines.forEach((l) => {
    const li = el('li', 'report-li');
    li.appendChild(pill(`${l.planet} · ${l.angle}`, l.color));
    li.appendChild(document.createTextNode(` ${l.distance_km} km · ${l.strength}`));
    ul.appendChild(li);
  });
  s.appendChild(ul);
  return s;
}

function renderParans(parans: Paran[]): HTMLElement {
  const s = section('Parans', 'Where two planetary lines meet nearby.');
  if (!parans.length) {
    s.appendChild(el('p', 'report-text', 'No nearby parans.'));
    return s;
  }
  const ul = el('ul', 'report-list');
  parans.forEach((p) => {
    const li = el('li', 'report-li');
    li.appendChild(pill(`${p.planet_a} ${p.circle_a} × ${p.planet_b} ${p.circle_b}`));
    li.appendChild(document.createTextNode(` ${p.distance_km} km`));
    ul.appendChild(li);
  });
  s.appendChild(ul);
  return s;
}

function renderHouse(region: LocationAnalysis['house_region']): HTMLElement {
  const s = section('House region', 'Which part of your natal chart this place falls in.');
  s.appendChild(el('p', 'report-text', region.sentence));
  return s;
}

const DOMAIN_META: { key: keyof DomainScores; label: string; emoji: string }[] = [
  { key: 'Love', label: 'Love', emoji: '❤️' },
  { key: 'Career', label: 'Career', emoji: '💼' },
  { key: 'Home', label: 'Home', emoji: '🏠' },
  { key: 'Growth', label: 'Growth', emoji: '🚀' },
  { key: 'Peace', label: 'Peace', emoji: '🧘' },
];

function starGlyph(filled: number): string {
  // filled: 0 empty, 0.5 half, 1 full
  if (filled >= 1) return '★';
  if (filled >= 0.5) return '⯨';
  return '☆';
}

function renderScoreCard(scores: DomainScores): HTMLElement {
  const s = section('Domain scores', 'How this place rates across five life areas (0–5).');
  const grid = el('div', 'score-card-grid');
  for (const d of DOMAIN_META) {
    const val = scores[d.key] ?? 0;
    const row = el('div', 'score-card-row');
    row.appendChild(el('span', 'score-card-label', `${d.emoji} ${d.label}`));
    const stars = el('span', 'score-stars');
    let rem = val;
    for (let i = 0; i < 5; i++) {
      const fill = rem >= 1 ? 1 : rem >= 0.5 ? 0.5 : 0;
      const g = el('span', 'score-star');
      g.textContent = starGlyph(fill);
      if (fill >= 1) g.classList.add('full');
      else if (fill >= 0.5) g.classList.add('half');
      stars.appendChild(g);
      rem = Math.max(0, rem - 1);
    }
    row.appendChild(stars);
    row.appendChild(el('span', 'score-val', String(val)));
    grid.appendChild(row);
  }
  s.appendChild(grid);
  return s;
}

export function renderReport(
  data: LocationAnalysis,
  pinned = false,
  onDeletePin?: () => void,
): void {
  const root = $('report');
  root.innerHTML = '';
  root.classList.toggle('pinned', pinned);
  const head = el('div', 'report-head');
  head.appendChild(el('h2', 'report-title', pinned ? 'Location analysis' : 'Preview'));
  if (pinned) {
    head.appendChild(el('span', 'report-pin', 'pinned'));
    if (onDeletePin) {
      const del = el('button', 'report-del', '✕');
      del.title = 'Delete pin';
      del.addEventListener('click', onDeletePin);
      head.appendChild(del);
    }
  }
  root.appendChild(head);
  root.appendChild(
    el(
      'p',
      'report-coords',
      `${data.location.latitude.toFixed(2)}, ${data.location.longitude.toFixed(2)}`,
    ),
  );

  // Domain score card always shows at the top of the report.
  root.appendChild(renderScoreCard(data.domain_scores));

  // Relocation only matters once a spot is pinned (a real relocated chart).
  if (pinned) root.appendChild(renderRelocation(data.relocation));
  root.appendChild(renderNearest(data.nearest_acg));
  root.appendChild(renderHouse(data.house_region));
  root.appendChild(renderParans(data.parans));
  if (data.crossings && data.crossings.length) {
    root.appendChild(renderCrossings(data.crossings));
  }

  const why = section('Why it matters', 'Plain-English read on this place.');
  why.appendChild(el('p', 'report-text', data.interpretations.overall));
  if (data.interpretations.nearest_acg.length) {
    const ul = el('ul', 'report-list');
    data.interpretations.nearest_acg.forEach((t) => ul.appendChild(bullet(t)));
    why.appendChild(ul);
  }
  if (data.interpretations.parans.length) {
    const ul = el('ul', 'report-list');
    data.interpretations.parans.forEach((t) => ul.appendChild(bullet(t)));
    why.appendChild(ul);
  }
  root.appendChild(why);
}

export function renderHoverPreview(planet: string, angle: string, color: string): void {
  const root = $('report');
  root.innerHTML = '';

  const dot = el('span', 'swatch line-swatch');
  dot.style.background = color;

  const header = el('div', 'hover-line-header');
  header.appendChild(dot);
  header.appendChild(el('span', 'hover-line-name', `${planet} · ${angle}`));
  root.appendChild(header);

  root.appendChild(el('p', 'hover-line-topic', topicFor(planet, angle)));
  root.appendChild(
    el(
      'p',
      'report-hint',
      '✦ Double-click anywhere on this line to get the full location analysis.',
    ),
  );
}

function topicFor(planet: string, angle: string): string {
  const themes: Record<string, string> = {
    MC: 'career, reputation and public life',
    IC: 'home, roots and family',
    ASC: 'how you present yourself and are seen',
    DSC: 'relationships and partnerships',
  };
  const planets: Record<string, string> = {
    Sun: 'your core identity and vitality',
    Moon: 'emotion and home life',
    Mercury: 'communication and learning',
    Venus: 'love, beauty and values',
    Mars: 'drive and desire',
    Jupiter: 'growth and good fortune',
    Saturn: 'discipline and structure',
    Uranus: 'freedom and change',
    Neptune: 'imagination and spirituality',
    Pluto: 'power and transformation',
    Chiron: 'healing',
    'True Node': 'life direction',
  };
  return `${planets[planet] ?? planet.toLowerCase()} through ${themes[angle] ?? angle.toLowerCase()}`;
}

export function clearReport(): void {
  const root = $('report');
  if (root) {
    root.innerHTML = '';
    root.classList.remove('pinned');
    root.appendChild(
      el('p', 'report-empty', 'Hover an astrocartography line to see its meaning. Activate the 📌 Pin tool, then single-click anywhere on the map to pin a full analysis.'),
    );
  }
}

// ─────────────────────────────────────────────────────────────────────────────
//  BEST CITIES PANEL
// ─────────────────────────────────────────────────────────────────────────────

export const GOAL_META: Record<string, { label: string; emoji: string; color: string }> = {
  all:    { label: 'All',    emoji: '🌐', color: '#e9c46a' },
  love:   { label: 'Love',   emoji: '❤️',  color: '#f43f5e' },
  career: { label: 'Career', emoji: '💼', color: '#3b82f6' },
  wealth: { label: 'Wealth', emoji: '💰', color: '#f59e0b' },
  peace:  { label: 'Peace',  emoji: '🧘', color: '#a855f7' },
  growth: { label: 'Growth', emoji: '🚀', color: '#10b981' },
};

const RANK_MEDALS = ['🥇', '🥈', '🥉'];

/** Animated SVG score ring */
function scoreRing(score: number, color: string): SVGSVGElement {
  const R = 22; const CX = 28; const CY = 28;
  const circum = 2 * Math.PI * R;
  const dash = (score / 99) * circum;
  const ns = 'http://www.w3.org/2000/svg';

  const svg = document.createElementNS(ns, 'svg') as SVGSVGElement;
  svg.setAttribute('viewBox', '0 0 56 56');
  svg.setAttribute('width', '56');
  svg.setAttribute('height', '56');
  svg.classList.add('score-ring');

  const track = document.createElementNS(ns, 'circle');
  track.setAttribute('cx', String(CX)); track.setAttribute('cy', String(CY));
  track.setAttribute('r', String(R));
  track.setAttribute('fill', 'none');
  track.setAttribute('stroke', 'rgba(255,255,255,0.08)');
  track.setAttribute('stroke-width', '4');
  svg.appendChild(track);

  const arc = document.createElementNS(ns, 'circle');
  arc.setAttribute('cx', String(CX)); arc.setAttribute('cy', String(CY));
  arc.setAttribute('r', String(R));
  arc.setAttribute('fill', 'none');
  arc.setAttribute('stroke', color);
  arc.setAttribute('stroke-width', '4');
  arc.setAttribute('stroke-linecap', 'round');
  arc.setAttribute('stroke-dasharray', `${circum}`);
  arc.setAttribute('stroke-dashoffset', String(circum));
  arc.setAttribute('transform', `rotate(-90 ${CX} ${CY})`);
  arc.style.transition = 'stroke-dashoffset 1s cubic-bezier(0.22,0.61,0.36,1)';
  svg.appendChild(arc);

  const txt = document.createElementNS(ns, 'text');
  txt.setAttribute('x', String(CX)); txt.setAttribute('y', String(CY + 5));
  txt.setAttribute('text-anchor', 'middle');
  txt.setAttribute('fill', '#fff');
  txt.setAttribute('font-size', '13');
  txt.setAttribute('font-weight', '700');
  txt.setAttribute('font-family', 'Plus Jakarta Sans, sans-serif');
  txt.textContent = String(score);
  svg.appendChild(txt);

  requestAnimationFrame(() => {
    arc.setAttribute('stroke-dashoffset', String(circum - dash));
  });

  return svg;
}

/** Horizontal category bar */
function categoryBar(emoji: string, label: string, score: number, color: string): HTMLElement {
  const row = el('div', 'city-cat-row');

  const lbl = el('span', 'city-cat-label');
  lbl.textContent = `${emoji} ${label}`;
  row.appendChild(lbl);

  const track = el('div', 'city-cat-track');
  const fill = el('div', 'city-cat-fill');
  fill.style.background = color;
  fill.style.width = '0%';
  fill.style.transition = 'width 0.9s cubic-bezier(0.22,0.61,0.36,1)';
  track.appendChild(fill);
  row.appendChild(track);

  const val = el('span', 'city-cat-val');
  val.textContent = `${score}`;
  row.appendChild(val);

  requestAnimationFrame(() => {
    fill.style.width = `${score}%`;
  });

  return row;
}

/** Ordinal suffix helper: 1st, 2nd, 3rd, 11th … */
function ordinalSuffix(n: number): string {
  const teen = n % 100;
  if (teen >= 10 && teen <= 20) return `${n}th`;
  return `${n}${({ 1: 'st', 2: 'nd', 3: 'rd' } as Record<number, string>)[n % 10] ?? 'th'}`;
}

export function renderTopCitiesCards(
  cities: import('./types').TopCity[],
  onSelectCity: (city: import('./types').TopCity) => void,
  activeGoal = 'all',
): void {
  const container = $('top-cities-list');
  if (!container) return;
  container.innerHTML = '';

  if (!cities.length) {
    const empty = el('div', 'cities-empty');
    empty.innerHTML = `
      <div class="cities-empty-icon">🌍</div>
      <p class="cities-empty-title">No recommendations yet</p>
      <p class="cities-empty-sub">Draw your birth chart first — your personalised top cities will appear here.</p>
    `;
    container.appendChild(empty);
    return;
  }

  const goalMeta = GOAL_META[activeGoal] ?? GOAL_META['all'];

  // Result count header
  const countRow = el('div', 'cities-count-row');
  const countSpan = el('span', 'cities-count');
  countSpan.textContent = `${cities.length} cities ranked`;
  const focusTag = el('span', 'cities-focus-tag');
  focusTag.textContent = `${goalMeta.emoji} ${goalMeta.label} focus`;
  focusTag.style.borderColor = goalMeta.color;
  focusTag.style.color = goalMeta.color;
  countRow.appendChild(countSpan);
  countRow.appendChild(focusTag);
  container.appendChild(countRow);

  cities.forEach((city, index) => {
    const card = el('div', 'city-card');
    if (index < 3) card.classList.add(`city-card--top${index + 1}`);

    // Header: rank + name + ring
    const headerRow = el('div', 'city-card-top');

    const rankBadge = el('div', 'city-rank-badge');
    rankBadge.textContent = index < 3 ? RANK_MEDALS[index] : `#${index + 1}`;
    headerRow.appendChild(rankBadge);

    const nameBlock = el('div', 'city-name-block');
    nameBlock.appendChild(el('div', 'city-name', city.name));
    nameBlock.appendChild(el('div', 'city-country', `${city.country} · ${city.region}`));
    headerRow.appendChild(nameBlock);

    headerRow.appendChild(scoreRing(city.overall_score, goalMeta.color));
    card.appendChild(headerRow);

    // Summary
    if (city.summary) {
      card.appendChild(el('p', 'city-summary', city.summary));
    }

    // Category bars
    const bars = el('div', 'city-cat-bars');
    bars.appendChild(categoryBar('❤️', 'Love',   city.scores.love,   '#f43f5e'));
    bars.appendChild(categoryBar('💼', 'Career', city.scores.career, '#3b82f6'));
    bars.appendChild(categoryBar('🚀', 'Growth', city.scores.growth, '#10b981'));
    bars.appendChild(categoryBar('🧘', 'Peace',  city.scores.peace,  '#a855f7'));
    card.appendChild(bars);

    // Influence pills
    if (city.primary_influences.length) {
      const infsRow = el('div', 'city-influences');
      city.primary_influences.slice(0, 3).forEach((inf) => {
        const tag = el('span', 'city-inf-pill');
        const dot = el('span', 'city-inf-dot');
        dot.style.background = inf.color;
        dot.style.boxShadow = `0 0 6px ${inf.color}`;
        tag.appendChild(dot);
        tag.appendChild(document.createTextNode(`${inf.planet} ${inf.angle} · ${inf.distance_km} km`));
        infsRow.appendChild(tag);
      });
      card.appendChild(infsRow);
    }

    // Score breakdown: where the points came from (ACG lines / houses / parans)
    if (city.score_breakdown) {
      const bd = city.score_breakdown;
      const total = Math.max(1, bd.acg + bd.houses + bd.parans);
      const parts: [string, number, string][] = [
        ['Lines', bd.acg, '#f59e0b'],
        ['Houses', bd.houses, '#3b82f6'],
        ['Parans', bd.parans, '#a855f7'],
      ];
      const bdRow = el('div', 'city-breakdown');
      const bdLabel = el('span', 'city-breakdown-label', 'Score mix');
      bdRow.appendChild(bdLabel);
      const bdBar = el('div', 'city-breakdown-bar');
      parts.forEach(([label, value, color]) => {
        if (value <= 0) return;
        const seg = document.createElement('div');
        seg.className = 'city-breakdown-seg';
        seg.style.width = `${Math.round((value / total) * 100)}%`;
        seg.style.background = color;
        seg.title = `${label}: ${value.toFixed(1)} pts`;
        bdBar.appendChild(seg);
      });
      bdRow.appendChild(bdBar);
      const bdLegend = el('span', 'city-breakdown-legend');
      bdLegend.textContent = parts
        .filter(([, v]) => v > 0)
        .map(([label, v]) => `${label} ${v.toFixed(1)}`)
        .join(' · ');
      bdRow.appendChild(bdLegend);
      card.appendChild(bdRow);

      // Notable relocated house placements (top 2)
      if (city.house_placements?.length) {
        const hpRow = el('div', 'city-houses');
        city.house_placements.slice(0, 2).forEach((hp) => {
          const tag = el('span', 'city-hp-pill');
          tag.textContent = `${hp.planet} → ${ordinalSuffix(hp.house)} house (${hp.domain})`;
          hpRow.appendChild(tag);
        });
        card.appendChild(hpRow);
      }
    }

    // CTA
    const btn = el('button', 'city-fly-btn');
    btn.innerHTML = `<span class="fly-icon">✈</span> Fly to City &amp; Inspect`;
    btn.addEventListener('click', () => onSelectCity(city));
    card.appendChild(btn);

    container.appendChild(card);
  });
}

/** Render shimmer skeleton while loading */
export function renderCitiesSkeleton(): void {
  const container = $('top-cities-list');
  if (!container) return;
  container.innerHTML = '';
  for (let i = 0; i < 5; i++) {
    const sk = el('div', 'city-skeleton');
    sk.innerHTML = `
      <div class="sk-row">
        <div class="sk-box sk-rank"></div>
        <div class="sk-lines">
          <div class="sk-box sk-name"></div>
          <div class="sk-box sk-country"></div>
        </div>
        <div class="sk-box sk-ring"></div>
      </div>
      <div class="sk-box sk-summary"></div>
      <div class="sk-bars">
        <div class="sk-box sk-bar"></div>
        <div class="sk-box sk-bar"></div>
        <div class="sk-box sk-bar"></div>
        <div class="sk-box sk-bar"></div>
      </div>
    `;
    container.appendChild(sk);
  }
}

// ---- Power places (crossings) -----------------------------------------------

export function renderCrossings(crossings: Crossing[]): HTMLElement {
  const s = section(
    'Power places',
    'Where two planetary energies intersect — historically significant spots.',
  );
  if (!crossings.length) {
    s.appendChild(el('p', 'report-text', 'No crossings found for this location.'));
    return s;
  }
  const ul = el('ul', 'report-list');
  crossings.forEach((c) => {
    const li = el('li', 'report-li');
    if (c.color_a || c.color_b) {
      const dot = el('span', 'swatch');
      dot.style.background = `linear-gradient(45deg, ${c.color_a || '#fff'} 40%, ${c.color_b || '#fff'} 60%)`;
      li.appendChild(dot);
    } else {
      li.appendChild(el('span', 'swatch'));
    }
    li.appendChild(document.createTextNode(` ${c.planet_a} ${c.angle_a} × ${c.planet_b} ${c.angle_b}`));
    if (c.interpretation) {
      const t = el('span', 'crossing-interp');
      t.textContent = c.interpretation;
      li.appendChild(t);
    }
    ul.appendChild(li);
  });
  s.appendChild(ul);
  return s;
}

// ---- Travel timing (electional) -------------------------------------------

export function scoreColor(score: number): string {
  if (score >= 75) return '#22c55e';
  if (score >= 60) return '#84cc16';
  if (score >= 50) return '#facc15';
  if (score >= 35) return '#f97316';
  return '#ef4444';
}

/** Render shimmer skeleton while travel timing loads. */
export function renderTravelSkeleton(): void {
  const container = $('travelTimingList');
  if (!container) return;
  container.innerHTML = '';
  for (let i = 0; i < 7; i++) {
    const sk = el('div', 'travel-skeleton');
    sk.innerHTML = `
      <div class="sk-box sk-day"></div>
      <div class="sk-box sk-score-bar"></div>
    `;
    container.appendChild(sk);
  }
}

/** Render the travel timing day list with scores and influences. */
export function renderTravelDays(
  days: import('./types').TravelDay[],
  pin: { name?: string; lat: number; lng: number },
): void {
  const container = $('travelTimingList');
  if (!container) return;
  container.innerHTML = '';

  if (!days.length) {
    const empty = el('div', 'report-empty');
    empty.textContent = 'No travel days to show.';
    container.appendChild(empty);
    return;
  }

  const header = el('div', 'travel-summary');
  header.innerHTML = `
    <div class="travel-summary-title">📅 Travel Window</div>
    <div class="travel-summary-sub">
      Destination: ${pin.name || `${pin.lat.toFixed(1)}, ${pin.lng.toFixed(1)}`} · ${days.length} days analysed
    </div>
  `;
  container.appendChild(header);

  // Best day highlight
  const best = days.reduce((a, b) => (b.score > a.score ? b : a), days[0]);
  const bestCard = el('div', 'travel-best-day');
  bestCard.innerHTML = `
    <div class="travel-best-label">✨ Best day</div>
    <div class="travel-best-date">${best.date}</div>
    <div class="travel-best-score" style="background:${scoreColor(best.score)}">${best.score.toFixed(0)}</div>
  `;
  if (best.influences?.length) {
    const inf = el('div', 'travel-best-inf');
    best.influences.forEach((i) => inf.appendChild(el('div', 'travel-inf-line', i)));
    bestCard.appendChild(inf);
  }
  container.appendChild(bestCard);

  // Score strip
  const strip = el('div', 'travel-strip');
  days.forEach((d) => {
    const cell = el('div', 'travel-cell');
    cell.style.background = scoreColor(d.score);
    cell.title = `${d.date}: ${d.score.toFixed(0)}/100`;
    cell.dataset.date = d.date;
    cell.dataset.score = String(d.score);
    if (d.influences?.length) {
      const tooltip = el('div', 'travel-cell-tooltip');
      tooltip.appendChild(el('div', 'travel-cell-date', d.date));
      d.influences.forEach((i) => tooltip.appendChild(el('div', 'travel-cell-inf', i)));
      cell.appendChild(tooltip);
    }
    strip.appendChild(cell);
  });
  container.appendChild(strip);

  // Detail list
  const list = el('div', 'travel-list');
  days.forEach((d) => {
    const row = el('div', 'travel-row');
    row.innerHTML = `
      <div class="travel-date">${d.date}</div>
      <div class="travel-score-wrap">
        <div class="travel-score" style="background:${scoreColor(d.score)}">${d.score.toFixed(0)}</div>
      </div>
    `;
    if (d.influences?.length) {
      const inf = el('div', 'travel-influences');
      d.influences.forEach((i) => inf.appendChild(el('div', 'travel-inf-line', i)));
      row.appendChild(inf);
    }
    list.appendChild(row);
  });
  container.appendChild(list);
}

/** Generate clean, structured HTML for full print/PDF export. */
export function buildFullPrintReportHTML(options: {
  birthName: string;
  birth: { datetime: string; latitude: number; longitude: number };
  mapImgDataUrl: string;
  topCities?: TopCity[];
  lastAnalysis?: LocationAnalysis | null;
}): string {
  const { birthName, birth, mapImgDataUrl, topCities, lastAnalysis } = options;
  const name = birthName.trim() || 'Birth Chart';
  const genDate = new Date().toLocaleDateString(undefined, { year: 'numeric', month: 'long', day: 'numeric' });
  
  const m = birth.datetime.match(/^(\d{4}-\d{2}-\d{2})T(\d{2}:\d{2})/);
  const dateStr = m ? `${m[1]} at ${m[2]} UTC` : birth.datetime;
  const latStr = `${Math.abs(birth.latitude).toFixed(2)}°${birth.latitude >= 0 ? 'N' : 'S'}`;
  const lngStr = `${Math.abs(birth.longitude).toFixed(2)}°${birth.longitude >= 0 ? 'E' : 'W'}`;

  let topCitiesRows = '';
  if (topCities && topCities.length) {
    topCitiesRows = topCities.slice(0, 10).map((c, idx) => {
      const infs = (c.primary_influences || [])
        .map((i) => `${i.planet} ${i.angle} (${i.distance_km} km)`)
        .join(', ');
      return `
        <tr>
          <td><b>#${idx + 1} ${c.name}</b></td>
          <td>${c.country}</td>
          <td><span class="print-score-badge">${c.overall_score}</span></td>
          <td>${c.scores?.love ?? '—'}</td>
          <td>${c.scores?.career ?? '—'}</td>
          <td>${c.scores?.peace ?? '—'}</td>
          <td>${c.scores?.growth ?? '—'}</td>
          <td>${infs || 'Harmonious ambient energy'}</td>
        </tr>
      `;
    }).join('');
  }

  let locationIntelHTML = '';
  if (lastAnalysis) {
    const loc = lastAnalysis.location;
    const rel = lastAnalysis.relocation;
    const interp = lastAnalysis.interpretations;

    const relocAngles = rel?.angles
      ? `ASC: ${rel.angles.asc.sign} | MC: ${rel.angles.mc.sign} | DSC: ${rel.angles.dsc.sign} | IC: ${rel.angles.ic.sign}`
      : 'Standard relocated cusps';

    const acgLines = (lastAnalysis.nearest_acg || [])
      .map((l) => `<li><b>${l.planet} ${l.angle}</b> — ${l.distance_km} km (${l.strength})</li>`)
      .join('');

    locationIntelHTML = `
      <div class="print-section">
        <h3 class="print-section-title">📍 Pinned Location Intel (${loc.latitude.toFixed(2)}°, ${loc.longitude.toFixed(2)}°)</h3>
        <div style="font-size: 11px; margin-bottom: 8px;"><b>Relocated Angles:</b> ${relocAngles}</div>
        ${interp?.overall ? `<p style="font-size: 11px; line-height: 1.4; background: #f8fafc; padding: 8px; border-radius: 6px; border: 1px solid #e2e8f0; margin-bottom: 10px;">${interp.overall}</p>` : ''}
        ${acgLines ? `<div style="font-size: 11px;"><b>Proximity Lines:</b><ul>${acgLines}</ul></div>` : ''}
      </div>
    `;
  }

  return `
    <div class="print-header">
      <div class="print-brand">✶ ASTROCARTOGRAPHY RELOCATION REPORT</div>
      <h1 class="print-title">${name}'s Astrocartography Profile</h1>
      <div class="print-meta-grid">
        <div><b>Birth Moment:</b> ${dateStr}</div>
        <div><b>Birth Coords:</b> ${latStr}, ${lngStr}</div>
        <div><b>Report Date:</b> ${genDate}</div>
      </div>
    </div>

    ${mapImgDataUrl ? `
    <div class="print-section">
      <h3 class="print-section-title">🗺️ Global Planetary Line Map</h3>
      <div class="print-map-wrapper">
        <img src="${mapImgDataUrl}" class="print-map-img" alt="Astrocartography Globe Map" />
      </div>
    </div>
    ` : ''}

    ${topCitiesRows ? `
    <div class="print-section">
      <h3 class="print-section-title">✦ Top 10 Recommended Locations</h3>
      <table class="print-table">
        <thead>
          <tr>
            <th>City</th>
            <th>Country</th>
            <th>Score</th>
            <th>Love</th>
            <th>Career</th>
            <th>Peace</th>
            <th>Growth</th>
            <th>Key Line Influences</th>
          </tr>
        </thead>
        <tbody>
          ${topCitiesRows}
        </tbody>
      </table>
    </div>
    ` : ''}

    ${locationIntelHTML}

    <div class="print-section">
      <h3 class="print-section-title">📖 Astrocartography Angle & Planet Guide</h3>
      <div class="print-guide-grid">
        <div class="print-guide-box">
          <h4>Four Cardinal Angles</h4>
          <p><b>MC (Midheaven):</b> Career, reputation, public achievement & outer purpose.<br>
             <b>IC (Imum Coeli):</b> Home, roots, family, emotional foundation & inner peace.<br>
             <b>ASC (Ascendant):</b> Personal identity, vitality, self-expression & physical presence.<br>
             <b>DSC (Descendant):</b> One-on-one relationships, partnerships, marriage & attraction.</p>
        </div>
        <div class="print-guide-box">
          <h4>Planetary Archetypes</h4>
          <p><b>Benefics (Sun, Venus, Jupiter):</b> Growth, harmony, abundance, joy & social magnetism.<br>
             <b>Intellectual (Mercury, Moon):</b> Learning, communication, intuition & emotional roots.<br>
             <b>Transformational (Mars, Saturn, Uranus, Pluto):</b> Drive, discipline, sudden shifts & deep rebirth.</p>
        </div>
      </div>
    </div>
  `;
}

