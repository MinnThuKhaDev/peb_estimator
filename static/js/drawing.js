/* Schematic (non-engineering) drawing preview: anchor bolt grid + cross section. */

function getFormInput() {
  const num = (id) => parseFloat(document.getElementById(id).value) || 0;
  const txt = (id) => document.getElementById(id).value;
  return {
    name: txt('name'), frame_type: txt('frame_type'),
    width: num('width'), length: num('length'), eave_height: num('eave_height'),
    bay_count: num('bay_count'), slope_rise: num('slope_rise'), slope_run: num('slope_run'),
    wind_speed: num('wind_speed'), live_load: num('live_load'), collateral: num('collateral'),
    seismic_zone: txt('seismic_zone'), occupancy: txt('occupancy'), enclosure: txt('enclosure'),
    has_mezz: document.getElementById('has_mezz').checked, mezz_area: num('mezz_area'), mezz_rate: num('mezz_rate'),
    has_crane: document.getElementById('has_crane').checked, crane_cap: num('crane_cap'), crane_len: num('crane_len'), crane_rate: num('crane_rate'),
    has_canopy: document.getElementById('has_canopy').checked, canopy_area: num('canopy_area'), canopy_rate: num('canopy_rate'),
    pct_bu: num('pct_bu'), pct_dsw: num('pct_dsw'), pct_sp: num('pct_sp'), pct_cf: num('pct_cf'), pct_rs: num('pct_rs'), pct_acc: num('pct_acc')
  };
}

function drawSchematics() {
  const input = getFormInput();
  drawPlan(input);
  drawSection(input);
}

function drawPlan(input) {
  const W = 900, H = 380, marginX = 70, marginY = 60;
  const bays = Math.max(1, Math.round(input.bay_count));
  const usableW = W - 2 * marginX;
  const bayPx = usableW / bays;
  let cols = '';
  for (let i = 0; i <= bays; i++) {
    const x = marginX + i * bayPx;
    cols += `<line x1="${x}" y1="${marginY}" x2="${x}" y2="${H - marginY}" stroke="#9fb3c8" stroke-width="1"/>
      <circle cx="${x}" cy="${marginY}" r="6" fill="#12305c"/><circle cx="${x}" cy="${H - marginY}" r="6" fill="#12305c"/>
      <text x="${x}" y="${marginY - 14}" font-size="11" text-anchor="middle" fill="#12305c">${i + 1}</text>`;
  }
  const spacing = input.bay_count ? (input.length / bays).toFixed(2) : '0';
  const svg = `<svg class="schema" viewBox="0 0 ${W} ${H}">
    <rect x="${marginX}" y="${marginY}" width="${usableW}" height="${H - 2 * marginY}" fill="none" stroke="#12305c" stroke-width="2"/>
    ${cols}
    <line x1="${marginX}" y1="${marginY}" x2="${W - marginX}" y2="${marginY}" stroke="#12305c" stroke-width="2"/>
    <line x1="${marginX}" y1="${H - marginY}" x2="${W - marginX}" y2="${H - marginY}" stroke="#12305c" stroke-width="2"/>
    <text x="${W / 2}" y="${H - 15}" font-size="13" text-anchor="middle" fill="#5b6b80">${bays} bays x ${spacing} m ~ ${input.length} m length | Width ${input.width} m</text>
    <text x="${W / 2}" y="24" font-size="14" text-anchor="middle" fill="#c0392b" font-weight="bold">SCHEMATIC ANCHOR BOLT GRID - NOT FOR CONSTRUCTION</text>
  </svg>`;
  document.getElementById('planSvgWrap').innerHTML = svg;
}

function drawSection(input) {
  const W = 700, H = 420, base = 350, marginX = 90;
  const eaveHeightPx = 200;
  const slope = input.slope_run > 0 ? input.slope_rise / input.slope_run : 0.1;
  const ridgeRise = (input.width / 2) * slope;
  const ridgeRisePx = Math.min(90, ridgeRise * 8);
  const leftX = marginX, rightX = W - marginX, eaveY = base - eaveHeightPx, ridgeY = eaveY - ridgeRisePx, midX = W / 2;
  const svg = `<svg class="schema" viewBox="0 0 ${W} ${H}">
    <text x="${W / 2}" y="24" font-size="14" text-anchor="middle" fill="#c0392b" font-weight="bold">SCHEMATIC CROSS SECTION - NOT FOR CONSTRUCTION</text>
    <line x1="${leftX - 20}" y1="${base}" x2="${rightX + 20}" y2="${base}" stroke="#9fb3c8" stroke-width="2"/>
    <line x1="${leftX}" y1="${base}" x2="${leftX}" y2="${eaveY}" stroke="#12305c" stroke-width="5"/>
    <line x1="${rightX}" y1="${base}" x2="${rightX}" y2="${eaveY}" stroke="#12305c" stroke-width="5"/>
    <polyline points="${leftX},${eaveY} ${midX},${ridgeY} ${rightX},${eaveY}" fill="none" stroke="#d4a017" stroke-width="5"/>
    <text x="${leftX - 15}" y="${(base + eaveY) / 2}" font-size="12" text-anchor="end" fill="#5b6b80">Eave ${input.eave_height} m</text>
    <text x="${midX}" y="${ridgeY - 14}" font-size="12" text-anchor="middle" fill="#5b6b80">Slope ${input.slope_rise}:${input.slope_run}</text>
    <text x="${midX}" y="${base + 30}" font-size="12" text-anchor="middle" fill="#5b6b80">Width ${input.width} m</text>
  </svg>`;
  document.getElementById('sectionSvgWrap').innerHTML = svg;
}
