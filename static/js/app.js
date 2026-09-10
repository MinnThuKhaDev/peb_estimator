/* ---------- tabs ---------- */
document.querySelectorAll('.nav-item').forEach(btn => {
  btn.addEventListener('click', () => {
    document.querySelectorAll('.nav-item').forEach(b => b.classList.remove('active'));
    document.querySelectorAll('.tab').forEach(t => t.classList.remove('active'));
    btn.classList.add('active');
    document.getElementById('tab-' + btn.dataset.tab).classList.add('active');
    if (btn.dataset.tab === 'drawing') drawSchematics();
  });
});

/* ---------- special-item toggles ---------- */
function bindToggle(cbId, gridId) {
  const cb = document.getElementById(cbId), grid = document.getElementById(gridId);
  cb.addEventListener('change', () => grid.classList.toggle('show', cb.checked));
}
bindToggle('has_mezz', 'mezzGrid');
bindToggle('has_crane', 'craneGrid');
bindToggle('has_canopy', 'canopyGrid');

/* ---------- helpers ---------- */
function fmt(n) { return Math.round(n).toLocaleString(); }

async function api(path, opts) {
  opts = opts || {};
  opts.headers = { ...(opts.headers || {}), ...authHeader() };
  const res = await fetch(path, opts);
  if (res.status === 401) {
    clearSession();
    showLogin(true);
    throw new Error('Session expired — please sign in again.');
  }
  if (!res.ok) {
    let msg = res.statusText;
    try { const j = await res.json(); msg = j.detail || msg; } catch (e) {}
    throw new Error(msg);
  }
  return res.json();
}

/* ---------- DB status / history ---------- */
async function refreshHistory() {
  const el = document.getElementById('dbStatus');
  try {
    const projects = await api('/api/projects');
    window.__projects = projects;
    document.getElementById('histCount').textContent = projects.length;
    el.textContent = 'Local database connected (' + projects.length + ' projects)';
    el.className = 'db-status ok';
    renderHistoryTable(projects);
  } catch (e) {
    el.textContent = 'Could not reach local server: ' + e.message;
    el.className = 'db-status err';
  }
}

function renderHistoryTable(projects) {
  let html = `<table><thead><tr><th>Name</th><th>W x L (m)</th><th>Eave</th><th>Wind</th>
    <th>Live load</th><th>Enclosure</th><th>Total wt (kg)</th><th>kg/m^2</th><th></th></tr></thead><tbody>`;
  projects.forEach(p => {
    const kgm2 = (p.total_weight / (p.width * p.length)).toFixed(2);
    html += `<tr><td>${p.name}</td><td>${p.width}x${p.length}</td><td>${p.eave_height}</td><td>${p.wind_speed}</td>
      <td>${p.live_load}</td><td><span class="pill ${p.enclosure === 'Open' ? 'open' : 'enc'}">${p.enclosure}</span></td>
      <td>${fmt(p.total_weight)}</td><td>${kgm2}</td>
      <td><button class="btn link" onclick="removeHistory(${p.id})">remove</button></td></tr>`;
  });
  html += '</tbody></table>';
  document.getElementById('historyTableWrap').innerHTML = html;
}

async function removeHistory(id) {
  await api('/api/projects/' + id, { method: 'DELETE' });
  refreshHistory();
}

async function saveCurrentAsHistory() {
  const input = getFormInput();
  const actual = prompt('Enter the ACTUAL total steel weight (kg) for this project, so the tool can learn from it:');
  const w = parseFloat(actual);
  if (!w || w <= 0) { alert('No valid weight entered - not saved.'); return; }
  await api('/api/projects', {
    method: 'POST', headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      name: input.name || 'Project', width: input.width, length: input.length,
      eave_height: input.eave_height, wind_speed: input.wind_speed, live_load: input.live_load,
      seismic_zone: input.seismic_zone, occupancy: input.occupancy, enclosure: input.enclosure,
      frame_type: input.frame_type, total_weight: w
    })
  });
  await refreshHistory();
  alert('Saved to the local database. Future estimates will factor this project in.');
}

/* ---------- estimate ---------- */
let lastResult = null;

async function runEstimate() {
  const input = getFormInput();
  try {
    const r = await api('/api/estimate', {
      method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(input)
    });
    lastResult = { input, ...r };
    renderResults(lastResult);
    document.getElementById('csvBtn').style.display = 'inline-block';
    document.getElementById('saveHistBtn').style.display = 'inline-block';
  } catch (e) {
    document.getElementById('resultsBox').innerHTML = `<p class="note" style="color:#c0392b">Estimate failed: ${e.message}</p>`;
  }
}

function renderResults(r) {
  let html = `<div class="result-summary">
    <div class="stat"><div class="v">${r.area.toFixed(1)} m^2</div><div class="l">Building area</div></div>
    <div class="stat"><div class="v">${r.kgm2.toFixed(2)} kg/m^2</div><div class="l">Predicted base rate</div></div>
    <div class="stat"><div class="v">${fmt(r.grand_total)} kg</div><div class="l">Estimated total weight</div></div>
    <div class="stat"><div class="v">${r.overall_kgm2.toFixed(2)} kg/m^2</div><div class="l">Overall weight/m^2</div></div>
    <div class="stat"><div class="v">${r.historical_count}</div><div class="l">Projects used</div></div>
  </div>
  <table><thead><tr><th>Item</th><th>Est. Weight (kg)</th><th>% of total</th></tr></thead><tbody>
  <tr><td colspan="3"><span class="pill part">PART 1 - MAIN MATERIAL</span></td></tr>`;
  Object.entries(r.part1).forEach(([k, v]) => {
    html += `<tr><td>${k}</td><td>${fmt(v)}</td><td>${(v / r.grand_total * 100).toFixed(1)}%</td></tr>`;
  });
  html += `<tr class="total-row"><td>Subtotal Part 1</td><td>${fmt(r.part1_total)}</td><td>${(r.part1_total / r.grand_total * 100).toFixed(1)}%</td></tr>`;

  html += `<tr><td colspan="3"><span class="pill part">PART 2 - SPECIAL STRUCTURE</span></td></tr>`;
  const p2keys = Object.keys(r.part2);
  if (p2keys.length === 0) { html += `<tr><td colspan="3" style="color:var(--muted)">None selected</td></tr>`; }
  Object.entries(r.part2).forEach(([k, v]) => {
    html += `<tr><td>${k}</td><td>${fmt(v)}</td><td>${(v / r.grand_total * 100).toFixed(1)}%</td></tr>`;
  });
  if (p2keys.length > 0) {
    html += `<tr class="total-row"><td>Subtotal Part 2</td><td>${fmt(r.part2_total)}</td><td>${(r.part2_total / r.grand_total * 100).toFixed(1)}%</td></tr>`;
  }

  html += `<tr><td colspan="3"><span class="pill part">PART 3 - ACCESSORIES</span></td></tr>
  <tr><td>Bolts, trims, gutters, insulation, misc.</td><td>${fmt(r.part3_total)}</td><td>${(r.part3_total / r.grand_total * 100).toFixed(1)}%</td></tr>
  <tr class="total-row"><td>TOTAL ESTIMATED WEIGHT</td><td>${fmt(r.grand_total)}</td><td>100%</td></tr>
  </tbody></table>`;

  document.getElementById('resultsBox').innerHTML = html;
}

function downloadCSV() {
  if (!lastResult) return;
  const r = lastResult;
  let rows = [
    ['ESTIMATE (preliminary, non-certified)'],
    ['Project', r.input.name], ['Frame type', r.input.frame_type],
    ['Width (m)', r.input.width], ['Length (m)', r.input.length], ['Eave height (m)', r.input.eave_height],
    ['Area (m2)', r.area.toFixed(2)], ['Wind speed (km/h)', r.input.wind_speed], ['Live load (kN/m2)', r.input.live_load],
    ['Seismic', r.input.seismic_zone], ['Occupancy', r.input.occupancy], ['Enclosure', r.input.enclosure],
    [], ['Item', 'Weight (kg)'], ['PART 1 - MAIN MATERIAL', '']
  ];
  Object.entries(r.part1).forEach(([k, v]) => rows.push([k, Math.round(v)]));
  rows.push(['Subtotal Part 1', Math.round(r.part1_total)]);
  rows.push(['PART 2 - SPECIAL STRUCTURE', '']);
  Object.entries(r.part2).forEach(([k, v]) => rows.push([k, Math.round(v)]));
  rows.push(['Subtotal Part 2', Math.round(r.part2_total)]);
  rows.push(['PART 3 - ACCESSORIES', '']);
  rows.push(['Bolts/trims/gutters/insulation/misc.', Math.round(r.part3_total)]);
  rows.push(['TOTAL ESTIMATED WEIGHT (kg)', Math.round(r.grand_total)]);
  rows.push(['Overall weight per m2', r.overall_kgm2.toFixed(2)]);

  const csv = rows.map(row => row.map(c => `"${String(c).replace(/"/g, '""')}"`).join(',')).join('\n');
  const blob = new Blob([csv], { type: 'text/csv' });
  const a = document.createElement('a');
  a.href = URL.createObjectURL(blob);
  a.download = (r.input.name || 'estimate').replace(/[^a-z0-9]+/gi, '_') + '_estimate.csv';
  a.click();
}

/* ---------- offline file parse (no AI) ---------- */
async function parseOffline() {
  const fileInput = document.getElementById('offlineFile');
  const statusEl = document.getElementById('offlineStatus');
  if (!fileInput.files[0]) { alert('Choose a file first.'); return; }
  statusEl.textContent = 'Scanning file...';
  const fd = new FormData();
  fd.append('file', fileInput.files[0]);
  try {
    const r = await api('/api/upload-parse', { method: 'POST', body: fd });
    const f = r.fields || {};
    const map = { width: 'width', length: 'length', eave_height: 'eave_height', wind_speed: 'wind_speed', live_load: 'live_load', seismic_zone: 'seismic_zone', enclosure: 'enclosure', frame_type: 'frame_type' };
    let applied = [];
    Object.entries(map).forEach(([k, id]) => {
      if (f[k] !== undefined && f[k] !== null) {
        document.getElementById(id).value = f[k];
        applied.push(k);
      }
    });
    statusEl.textContent = applied.length
      ? 'Auto-filled: ' + applied.join(', ') + '. Please review all fields.'
      : 'Could not confidently detect any fields in this file - enter values manually, or try the AI Assistant tab.';
  } catch (e) {
    statusEl.textContent = 'Could not read file: ' + e.message;
  }
}

/* ---------- AI assistant ---------- */
let lastAIExtract = null;

async function sendToAI() {
  const fileInput = document.getElementById('aiFile');
  const note = document.getElementById('aiNote').value;
  const statusEl = document.getElementById('aiStatus');
  const outEl = document.getElementById('aiOutput');
  if (!fileInput.files[0]) { alert('Choose a file first.'); return; }

  statusEl.textContent = 'Contacting AI... this can take up to a minute for large files.';
  outEl.innerHTML = '';
  const fd = new FormData();
  fd.append('file', fileInput.files[0]);
  if (note) fd.append('note', note);

  try {
    const r = await api('/api/ai-extract', { method: 'POST', body: fd });
    statusEl.textContent = '';
    lastAIExtract = r.fields;
    outEl.innerHTML = `
      <div class="banner" style="margin:0 0 12px">DRAFT OUTPUT - for your engineer's review only. Not for construction.</div>
      ${r.fields ? '<button class="btn primary" onclick="applyAIResult()">Apply extracted values to Estimate form &rarr;</button>' : '<p class="note">Could not parse a clean parameter set - read the notes below and enter values manually.</p>'}
      <div class="card" style="margin-top:12px;white-space:pre-wrap;font-size:13px">${(r.notes || '').replace(/</g, '&lt;')}</div>
    `;
  } catch (e) {
    statusEl.textContent = 'AI request failed: ' + e.message;
  }
}

function applyAIResult() {
  if (!lastAIExtract) { alert('Nothing to apply.'); return; }
  const direct = ['width', 'length', 'eave_height', 'bay_count', 'slope_rise', 'slope_run', 'wind_speed', 'live_load',
    'seismic_zone', 'occupancy', 'frame_type', 'mezz_area', 'crane_cap', 'crane_len', 'canopy_area'];
  direct.forEach(id => {
    if (lastAIExtract[id] !== undefined && lastAIExtract[id] !== null) {
      const el = document.getElementById(id);
      if (el) el.value = lastAIExtract[id];
    }
  });
  if (lastAIExtract.enclosure) {
    const e = String(lastAIExtract.enclosure).toLowerCase();
    const s = e.includes('open') ? 'Open' : e.includes('partial') ? 'Partially Enclosed' : 'Enclosed';
    document.getElementById('enclosure').value = s;
  }
  if (lastAIExtract.has_mezz) { document.getElementById('has_mezz').checked = true; document.getElementById('mezzGrid').classList.add('show'); }
  if (lastAIExtract.has_crane) { document.getElementById('has_crane').checked = true; document.getElementById('craneGrid').classList.add('show'); }
  if (lastAIExtract.has_canopy) { document.getElementById('has_canopy').checked = true; document.getElementById('canopyGrid').classList.add('show'); }

  document.querySelectorAll('.nav-item').forEach(b => b.classList.remove('active'));
  document.querySelectorAll('.tab').forEach(t => t.classList.remove('active'));
  document.querySelector('.nav-item[data-tab="estimate"]').classList.add('active');
  document.getElementById('tab-estimate').classList.add('active');
  runEstimate();
  alert('Applied. This is still a DRAFT - review every field before treating it as a real estimate.');
}

/* ---------- init ---------- */
// refreshHistory() is called from auth.js's afterLogin() once a session
// exists, so the app never queries the API before the user is signed in.
drawSchematics();
