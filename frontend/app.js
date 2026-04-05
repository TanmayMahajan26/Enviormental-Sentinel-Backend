/**
 * EcoSentinel — Premium Dashboard Application
 * Dynamic gauges, area charts, glassmorphic zone intelligence
 */

// ═══════════════════════════════════════════════════
// UTILITIES
// ═══════════════════════════════════════════════════

async function fetchJSON(url) {
  const r = await fetch(url, { signal: AbortSignal.timeout(15000) });
  if (!r.ok) throw new Error(`${r.status} ${r.statusText}`);
  return r.json();
}
async function postJSON(url, data) {
  const r = await fetch(url, { method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify(data), signal:AbortSignal.timeout(30000) });
  if (!r.ok) throw new Error(`${r.status} ${r.statusText}`);
  return r.json();
}
function $(id) { return document.getElementById(id); }
function html(el, h) { if (typeof el === 'string') el = $(el); if (el) el.innerHTML = h; }
function formatTime(ts) {
  if (!ts) return '';
  try { const d = new Date(ts), diff = (Date.now()-d.getTime())/3600000;
    if (diff < 0.017) return 'Just now'; if (diff < 1) return Math.round(diff*60)+'m ago';
    if (diff < 24) return Math.round(diff)+'h ago'; return Math.round(diff/24)+'d ago';
  } catch(_) { return ts; }
}
function sevColor(s) { return s==='critical'?'#ef4444':s==='high'?'#f97316':s==='medium'?'#eab308':'#22c55e'; }
function sevClass(s) { return s==='critical'?'critical':s==='high'?'high':s==='medium'?'medium':'low'; }
function riskColor(score) { return score>0.7?'#ef4444':score>0.4?'#f97316':score>0.2?'#eab308':'#22c55e'; }
function riskGrad(score) { return score>0.7?'linear-gradient(90deg,#dc2626,#ef4444)':score>0.4?'linear-gradient(90deg,#ea580c,#f97316)':score>0.2?'linear-gradient(90deg,#ca8a04,#eab308)':'linear-gradient(90deg,#16a34a,#22c55e)'; }
function riskLabel(score) { return score>0.7?'CRITICAL':score>0.4?'HIGH':score>0.2?'MEDIUM':'NORMAL'; }
function toast(msg, type='info') {
  const c = $('toast-container'), t = document.createElement('div');
  t.className = 'toast '+type; t.textContent = msg; c.appendChild(t);
  setTimeout(() => { t.style.opacity='0'; setTimeout(()=>t.remove(),300); }, 3500);
}

// ═══════════════════════════════════════════════════
// SVG GAUGE BUILDER — Circular ring meters
// ═══════════════════════════════════════════════════

function buildGauge(value, max, label, unit, color, size=110) {
  const pct = Math.min(value / max, 1);
  const r = (size - 16) / 2;
  const circ = 2 * Math.PI * r;
  const dash = circ * pct;
  const gap = circ - dash;
  const gradId = 'g-' + label.replace(/\s/g,'');
  return `<div class="gauge-ring" style="width:${size}px;height:${size}px;">
    <svg viewBox="0 0 ${size} ${size}">
      <defs>
        <linearGradient id="${gradId}" x1="0%" y1="0%" x2="100%" y2="100%">
          <stop offset="0%" stop-color="${color}" stop-opacity="0.7"/>
          <stop offset="100%" stop-color="${color}"/>
        </linearGradient>
      </defs>
      <circle class="gauge-bg" cx="${size/2}" cy="${size/2}" r="${r}"/>
      <circle class="gauge-fill" cx="${size/2}" cy="${size/2}" r="${r}"
        stroke="url(#${gradId})" stroke-dasharray="${dash} ${gap}"
        style="filter:drop-shadow(0 0 6px ${color}40);"/>
    </svg>
    <div class="gauge-label">
      <span class="gauge-value" style="color:${color}">${typeof value==='number'?value.toFixed(value<10?1:0):value}</span>
      <span class="gauge-name">${label}${unit?' '+unit:''}</span>
    </div>
  </div>`;
}

// ═══════════════════════════════════════════════════
// SVG AREA CHART — Gradient-filled trend visualization
// ═══════════════════════════════════════════════════

function buildAreaChart(datasets, width=800, height=160) {
  const pad = { top:10, right:10, bottom:28, left:40 };
  const w = width - pad.left - pad.right;
  const h = height - pad.top - pad.bottom;

  let allVals = [];
  datasets.forEach(ds => ds.data.forEach(v => allVals.push(v)));
  const minY = Math.min(...allVals) * 0.95;
  const maxY = Math.max(...allVals) * 1.05;
  const range = maxY - minY || 1;

  function toX(i, len) { return pad.left + (i / (len - 1)) * w; }
  function toY(v) { return pad.top + h - ((v - minY) / range) * h; }

  let svg = `<svg viewBox="0 0 ${width} ${height}" preserveAspectRatio="none" style="height:${height}px;">`;

  // Grid lines
  for (let i = 0; i <= 4; i++) {
    const y = pad.top + (h / 4) * i;
    const val = maxY - (range / 4) * i;
    svg += `<line x1="${pad.left}" y1="${y}" x2="${width-pad.right}" y2="${y}" stroke="rgba(255,255,255,0.04)" stroke-width="1"/>`;
    svg += `<text x="${pad.left-6}" y="${y+3}" fill="rgba(255,255,255,0.18)" font-size="9" font-family="'JetBrains Mono'" text-anchor="end">${val.toFixed(1)}</text>`;
  }

  // Render each dataset
  datasets.forEach((ds, di) => {
    const n = ds.data.length;
    if (n < 2) return;
    const gradId = `area-grad-${di}`;

    // Build smooth path
    let linePts = [];
    for (let i = 0; i < n; i++) linePts.push(`${toX(i,n).toFixed(1)},${toY(ds.data[i]).toFixed(1)}`);
    const lineD = 'M' + linePts.join(' L');
    const areaD = lineD + ` L${toX(n-1,n).toFixed(1)},${pad.top+h} L${toX(0,n).toFixed(1)},${pad.top+h} Z`;

    svg += `<defs><linearGradient id="${gradId}" x1="0" y1="0" x2="0" y2="1">
      <stop offset="0%" stop-color="${ds.color}" stop-opacity="0.25"/>
      <stop offset="100%" stop-color="${ds.color}" stop-opacity="0.02"/>
    </linearGradient></defs>`;
    svg += `<path d="${areaD}" fill="url(#${gradId})"/>`;
    svg += `<path d="${lineD}" fill="none" stroke="${ds.color}" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" style="filter:drop-shadow(0 0 4px ${ds.color}40)"/>`;

    // Data points
    for (let i = 0; i < n; i++) {
      if (i % Math.max(1, Math.floor(n/8)) === 0 || i === n-1) {
        svg += `<circle cx="${toX(i,n).toFixed(1)}" cy="${toY(ds.data[i]).toFixed(1)}" r="3" fill="${ds.color}" stroke="${ds.color}" stroke-width="1" stroke-opacity="0.3"/>`;
      }
    }
  });

  // X-axis labels
  const labels = datasets[0]?.labels || [];
  const step = Math.max(1, Math.floor(labels.length / 6));
  labels.forEach((lbl, i) => {
    if (i % step === 0 || i === labels.length - 1) {
      svg += `<text x="${toX(i,labels.length).toFixed(1)}" y="${height-4}" fill="rgba(255,255,255,0.2)" font-size="8" font-family="'JetBrains Mono'" text-anchor="middle">${lbl}</text>`;
    }
  });

  svg += '</svg>';
  return svg;
}

// ═══════════════════════════════════════════════════
// STATE
// ═══════════════════════════════════════════════════
let state = { zones: [], alerts: [], health: null, currentZone: null };

// ═══════════════════════════════════════════════════
// NAVIGATION
// ═══════════════════════════════════════════════════

function switchTab(tab) {
  document.querySelectorAll('.page').forEach(p => p.classList.remove('active'));
  const page = $('page-'+tab);
  if (page) page.classList.add('active');
  document.querySelectorAll('.nav-tab').forEach(t => {
    t.classList.toggle('active', t.dataset.tab === tab);
  });
  if (tab === 'dashboard') loadDashboard();
  else if (tab === 'alerts') loadAlerts();
  else if (tab === 'incidents') loadIncidents();
  else if (tab === 'simulation') loadSimSetup();
  else if (tab === 'logs') loadLogs();
  if (window.lucide) lucide.createIcons();
}

function showZoneDetail(zoneId) {
  document.querySelectorAll('.page').forEach(p => p.classList.remove('active'));
  $('page-zone-detail').classList.add('active');
  document.querySelectorAll('.nav-tab').forEach(t => t.classList.remove('active'));
  loadZoneDetail(zoneId);
}

// ═══════════════════════════════════════════════════
// DASHBOARD — with gauges and charts
// ═══════════════════════════════════════════════════

async function loadDashboard() {
  // System health
  try {
    const h = await fetchJSON('/api/system/health');
    state.health = h;
    const dot = document.querySelector('#nav-status .status-dot');
    const txt = document.querySelector('#nav-status .status-text');
    if (dot) { dot.classList.remove('offline'); }
    if (txt) { const s=h.uptime_seconds; txt.textContent = s<60?'Online — just started':s<3600?`Online — ${Math.floor(s/60)}m`:`Online — ${Math.floor(s/3600)}h`; }

    html('stats-row', `
      <div class="stat-card"><div class="stat-val">${h.total_zones}</div><div class="stat-lbl">Zones</div></div>
      <div class="stat-card"><div class="stat-val">${(h.total_readings/1000).toFixed(1)}k</div><div class="stat-lbl">Readings</div></div>
      <div class="stat-card"><div class="stat-val">${h.total_anomalies_detected}</div><div class="stat-lbl">Anomalies</div></div>
      <div class="stat-card"><div class="stat-val">${h.total_alerts_generated}</div><div class="stat-lbl">Alerts</div></div>
      <div class="stat-card"><div class="stat-val">${(h.model_accuracy*100).toFixed(0)}%</div><div class="stat-lbl">Accuracy</div></div>
      <div class="stat-card"><div class="stat-val">${h.uptime_seconds<3600?Math.floor(h.uptime_seconds/60)+'m':Math.floor(h.uptime_seconds/3600)+'h'}</div><div class="stat-lbl">Uptime</div></div>
    `);

    // Build system gauges
    const accuracy = h.model_accuracy * 100;
    const anomRate = h.total_anomalies_detected > 0 ? Math.min((h.total_anomalies_detected / h.total_readings) * 1000, 100) : 0;
    const alertRate = h.total_alerts_generated > 0 ? Math.min(h.total_alerts_generated * 5, 100) : 0;
    html('system-gauges',
      buildGauge(accuracy, 100, 'Model Accuracy', '%', '#2dd4bf') +
      buildGauge(h.total_zones, 8, 'Active Zones', '', '#e8c95a') +
      buildGauge(h.total_anomalies_detected, Math.max(h.total_anomalies_detected, 50), 'Anomalies', '', anomRate > 60 ? '#ef4444' : '#f97316') +
      buildGauge(h.total_alerts_generated, Math.max(h.total_alerts_generated, 20), 'Alerts', '', alertRate > 60 ? '#ef4444' : '#eab308') +
      buildGauge(parseFloat((h.total_readings/1000).toFixed(1)), 20, 'Data Points', 'k', '#3b82f6') +
      buildGauge(h.uptime_seconds < 3600 ? Math.floor(h.uptime_seconds/60) : Math.floor(h.uptime_seconds/3600), h.uptime_seconds < 3600 ? 60 : 24, 'Uptime', h.uptime_seconds < 3600 ? 'm' : 'h', '#a78bfa')
    );

  } catch(e) {
    const dot = document.querySelector('#nav-status .status-dot');
    if (dot) dot.classList.add('offline');
    document.querySelector('#nav-status .status-text').textContent = 'Offline';
    html('stats-row','<div class="error-msg">Backend offline — start with: python main.py</div>');
    html('system-gauges','');
  }

  // Zones
  try {
    const zones = await fetchJSON('/api/zones');
    state.zones = zones;
    if (!zones.length) { html('zone-grid','<div class="empty">No zones found</div>'); }
    else {
      html('zone-grid', zones.map(z => {
        const score = z.anomaly_score || 0;
        const label = riskLabel(score);
        const col = riskColor(score);
        const pct = Math.min(score * 100, 100);
        return `<div class="zone-card" onclick="showZoneDetail('${z.id}')">
          <div class="zc-top"><h3>${z.name}</h3><span class="badge ${sevClass(label.toLowerCase())}">${label}</span></div>
          <div class="zc-region"><i data-lucide="map-pin" style="width:12px;height:12px"></i>${z.region} · ${z.lat.toFixed(2)}°N, ${z.lng.toFixed(2)}°E</div>
          <div class="zc-signals">
            <div class="zc-sig"><div class="zc-sig-label">Sensitivity</div><div class="zc-sig-val">${z.current_sensitivity.toFixed(2)}</div></div>
            <div class="zc-sig"><div class="zc-sig-label">Alerts 24h</div><div class="zc-sig-val">${z.alert_count_24h}</div></div>
            <div class="zc-sig"><div class="zc-sig-label">Anomaly</div><div class="zc-sig-val" style="color:${col}">${score.toFixed(3)}</div></div>
          </div>
          <div class="zc-risk"><div class="zc-bar"><div class="zc-bar-fill" style="width:${pct}%;background:${riskGrad(score)}"></div></div><span class="zc-score" style="color:${col}">${score.toFixed(2)}</span></div>
        </div>`;
      }).join(''));
    }

    // Load readings for the highest-risk zone to populate chart
    loadTrendChart(zones);

  } catch(e) { html('zone-grid','<div class="error-msg">Failed to load zones: '+e.message+'</div>'); }

  // Alerts
  try {
    const data = await fetchJSON('/api/alerts?limit=5');
    state.alerts = data.alerts || [];
    if (!state.alerts.length) { html('dash-alerts','<div class="empty">No active alerts</div>'); }
    else { html('dash-alerts', state.alerts.map(a => alertItemHTML(a, false)).join('')); }
  } catch(e) { html('dash-alerts','<div class="error-msg">Failed: '+e.message+'</div>'); }

  // Briefing
  try {
    const b = await fetchJSON('/api/briefing');
    html('dash-briefing', `<div class="briefing-box">
      <div class="briefing-text">${b.summary}</div>
      <div class="briefing-meta">
        <span>Confidence: ${(b.system_confidence*100).toFixed(0)}%</span>
        <span>Zones needing attention: ${(b.zones_requiring_attention||[]).join(', ')||'None'}</span>
      </div></div>`);
  } catch(e) { html('dash-briefing','<div class="error-msg">Briefing unavailable: '+e.message+'</div>'); }

  if (window.lucide) lucide.createIcons();
}

// ═══════════════════════════════════════════════════
// TREND CHART — Area chart for highest risk zone
// ═══════════════════════════════════════════════════

async function loadTrendChart(zones) {
  if (!zones || !zones.length) return;
  // Find highest risk zone
  const topZone = zones.reduce((a, b) => (a.anomaly_score || 0) > (b.anomaly_score || 0) ? a : b);
  try {
    const data = await fetchJSON(`/api/zones/${topZone.id}/readings?limit=24`);
    if (!data.readings || data.readings.length < 2) {
      html('trend-chart', '<div class="empty" style="padding:20px">Not enough data for chart</div>');
      return;
    }
    const readings = data.readings;
    const labels = readings.map((r, i) => {
      try { const d = new Date(r.timestamp); return d.getHours() + ':00'; } catch(_) { return i+''; }
    });

    const chart = buildAreaChart([
      { label: 'SST', data: readings.map(r => r.sst || 0), color: '#e8c95a', labels },
      { label: 'Chlorophyll', data: readings.map(r => r.chlorophyll || 0), color: '#2dd4bf', labels },
      { label: 'Wind', data: readings.map(r => r.wind_speed || 0), color: '#3b82f6', labels },
    ], 800, 170);

    html('trend-chart', chart);

    // Update title
    const titleEl = document.querySelector('#trend-chart-panel .chart-title');
    if (titleEl) titleEl.innerHTML = `<i data-lucide="trending-up" style="width:16px;height:16px;color:var(--gold2)"></i> Signal Trend — ${topZone.name} (24h)`;

  } catch(e) {
    html('trend-chart', '<div class="empty" style="padding:20px">Chart unavailable</div>');
  }
}

function alertItemHTML(a, showFeedback=true) {
  const sev = a.severity || 'medium';
  return `<div class="alert-item">
    <div class="alert-sev-bar ${sevClass(sev)}"></div>
    <div class="alert-body">
      <div class="alert-title">${a.title||a.description||'Alert'}</div>
      <div class="alert-meta">
        <span class="badge ${sevClass(sev)}">${sev}</span>
        <span>Priority: <strong class="mono">${(a.priority_score||0).toFixed(3)}</strong></span>
        <span>${a.zone_name||a.zone_id||''}</span>
        <span>${formatTime(a.timestamp)}</span>
        <span>Signals: ${(a.signals_involved||[]).join(', ')}</span>
      </div>
      ${showFeedback && !a.feedback ? `<div class="alert-actions">
        <button class="btn-fb" onclick="submitFeedback(${a.id},'validated')">✓ Validated</button>
        <button class="btn-fb" onclick="submitFeedback(${a.id},'false_positive')">✗ False Positive</button>
      </div>` : a.feedback ? `<div style="font-size:.7rem;color:var(--text3);margin-top:6px">Feedback: ${a.feedback}</div>` : ''}
    </div></div>`;
}

// ═══════════════════════════════════════════════════
// ALERTS PAGE
// ═══════════════════════════════════════════════════

async function loadAlerts() {
  html('alerts-list','<div class="loader">Loading alerts…</div>');
  try {
    const data = await fetchJSON('/api/alerts?limit=50&include_suppressed=true');
    const alerts = data.alerts || [];
    if (!alerts.length) { html('alerts-list','<div class="empty">No alerts generated yet</div>'); return; }
    html('alerts-list', `<div style="margin-bottom:12px;font-size:.8rem;color:var(--text2)">
      Total: ${data.total} | Active: ${data.active_alerts} | Suppressed: ${data.suppressed_alerts}</div>`
      + alerts.map(a => alertItemHTML(a, true)).join(''));
  } catch(e) { html('alerts-list','<div class="error-msg">'+e.message+'</div>'); }
  if (window.lucide) lucide.createIcons();
}

async function submitFeedback(alertId, feedback) {
  try {
    const r = await postJSON(`/api/alerts/${alertId}/feedback`, { feedback, notes:'' });
    toast(`Feedback submitted! Sensitivity: ${r.zone_sensitivity_before.toFixed(2)} → ${r.zone_sensitivity_after.toFixed(2)}`, 'success');
    loadAlerts();
  } catch(e) { toast('Feedback failed: '+e.message, 'error'); }
}

// ═══════════════════════════════════════════════════
// ZONE DETAIL — with gauges and charts
// ═══════════════════════════════════════════════════

async function loadZoneDetail(zoneId) {
  state.currentZone = zoneId;
  html('zone-detail-content','<div class="loader">Loading zone intelligence…</div>');

  let zone, readings, rootcause, cascade, impact, ttr, memory, forecast;
  try { zone = await fetchJSON(`/api/zones/${zoneId}`); } catch(e) { zone = null; }
  if (!zone) { html('zone-detail-content','<div class="error-msg">Zone not found</div>'); return; }

  const results = await Promise.allSettled([
    fetchJSON(`/api/zones/${zoneId}/readings?limit=24`),
    fetchJSON(`/api/rootcause/${zoneId}`),
    fetchJSON(`/api/cascade?source_zone=${zoneId}`),
    fetchJSON(`/api/impact/${zoneId}?severity=0.5&duration_days=7`),
    fetchJSON(`/api/time-to-risk/${zoneId}`),
    fetchJSON(`/api/memory/${zoneId}`),
    fetchJSON(`/api/forecast/${zoneId}?signal=sst&horizon=48`),
  ]);
  readings = results[0].status==='fulfilled' ? results[0].value : null;
  rootcause = results[1].status==='fulfilled' ? results[1].value : null;
  cascade = results[2].status==='fulfilled' ? results[2].value : null;
  impact = results[3].status==='fulfilled' ? results[3].value : null;
  ttr = results[4].status==='fulfilled' ? results[4].value : null;
  memory = results[5].status==='fulfilled' ? results[5].value : null;
  forecast = results[6].status==='fulfilled' ? results[6].value : null;

  let out = `<div class="zd-header"><h1>${zone.name}</h1><span class="badge ${sevClass(riskLabel(zone.anomaly_score).toLowerCase())}">${riskLabel(zone.anomaly_score)}</span><span class="zd-region">${zone.region} · ${zone.lat.toFixed(2)}°N, ${zone.lng.toFixed(2)}°E</span></div>`;

  // Signal gauges for this zone
  if (readings && readings.readings && readings.readings.length) {
    const latest = readings.readings[readings.readings.length-1];
    out += `<div class="chart-panel mb-16"><div class="chart-header"><div class="chart-title"><i data-lucide="gauge" style="width:16px;height:16px;color:var(--teal)"></i> Current Readings</div></div>
      <div class="gauge-container">
        ${buildGauge(latest.sst||0, 35, 'SST', '°C', '#e8c95a')}
        ${buildGauge(latest.chlorophyll||0, 10, 'Chl-a', 'mg/m³', '#2dd4bf')}
        ${buildGauge(latest.wind_speed||0, 20, 'Wind', 'm/s', '#3b82f6')}
        ${buildGauge(latest.ph||0, 9, 'pH', '', '#a78bfa')}
        ${buildGauge(latest.turbidity||0, 15, 'Turbidity', 'NTU', '#f97316')}
      </div>
    </div>`;

    // Area chart for this zone
    const labels = readings.readings.map((r, i) => {
      try { const d = new Date(r.timestamp); return d.getHours() + ':00'; } catch(_) { return i+''; }
    });
    out += `<div class="chart-panel mb-16"><div class="chart-header"><div class="chart-title"><i data-lucide="trending-up" style="width:16px;height:16px;color:var(--gold2)"></i> 24h Signal Trends</div></div>
      <div class="chart-body">${buildAreaChart([
        { label:'SST', data: readings.readings.map(r=>r.sst||0), color:'#e8c95a', labels },
        { label:'Chl-a', data: readings.readings.map(r=>r.chlorophyll||0), color:'#2dd4bf', labels },
        { label:'Wind', data: readings.readings.map(r=>r.wind_speed||0), color:'#3b82f6', labels },
      ], 800, 170)}</div>
    </div>`;
  }

  out += '<div class="zd-grid">';

  // Root Cause
  if (rootcause && rootcause.root_causes) {
    out += `<div class="zd-section"><h3>🔍 Root Cause Analysis</h3>`;
    rootcause.root_causes.forEach(rc => {
      const pct = (rc.confidence*100).toFixed(0);
      out += `<div class="rc-bar-row"><div class="rc-bar-head"><span>${rc.cause}</span><span style="color:var(--teal);font-weight:800">${pct}%</span></div>
        <div class="rc-bar"><div class="rc-bar-fill" style="width:${pct}%;background:linear-gradient(90deg,rgba(45,212,191,0.3),var(--teal))"></div></div>
        <div style="font-size:.7rem;color:var(--text3);margin-top:3px">${rc.mechanism}</div></div>`;
    });
    out += '</div>';
  }

  // Cascade
  if (cascade && cascade.predictions && cascade.predictions.length) {
    out += `<div class="zd-section"><h3>🔗 Cascade Predictions</h3>`;
    cascade.predictions.forEach(p => {
      out += `<div class="cascade-item"><div><div class="ci-target">→ ${p.target_zone_name}</div><div class="ci-eta">${p.propagation_days_min}-${p.propagation_days_max} days · ${p.mechanism}</div></div><div class="ci-prob" style="color:${riskColor(p.cascade_probability)}">${(p.cascade_probability*100).toFixed(0)}%</div></div>`;
    });
    out += '</div>';
  }

  // Economic Impact with donut
  if (impact && impact.economic_impact) {
    const ei = impact.economic_impact;
    out += `<div class="zd-section"><h3>💰 Economic Impact</h3>
      <div class="impact-row">
        <div class="impact-item"><div class="ii-val">₹${ei.fishing_impact_crore?.toFixed(1)||0}</div><div class="ii-lbl">Fishing (Cr)</div></div>
        <div class="impact-item"><div class="ii-val">₹${ei.shipping_impact_crore?.toFixed(1)||0}</div><div class="ii-lbl">Shipping (Cr)</div></div>
        <div class="impact-item"><div class="ii-val">₹${ei.tourism_impact_crore?.toFixed(1)||0}</div><div class="ii-lbl">Tourism (Cr)</div></div>
      </div>
      <div class="impact-summary">${impact.impact_summary||''}</div>
    </div>`;
  }

  // Time to Risk
  if (ttr && ttr.warnings && ttr.warnings.length) {
    out += `<div class="zd-section"><h3>⏰ Time-to-Risk Early Warning</h3>`;
    ttr.warnings.forEach(w => {
      out += `<div class="ttr-item"><div class="ttr-signal">${w.signal.toUpperCase()} — ${w.trend}</div>
        <div class="ttr-text">Current: ${w.current_value.toFixed(2)} | Baseline: ${w.baseline.toFixed(2)} | Rate: ${w.rate_per_day.toFixed(3)}/day</div>
        ${w.human_readable?`<div style="font-size:.78rem;color:var(--high);margin-top:4px">${w.human_readable}</div>`:''}
      </div>`;
    });
    out += '</div>';
  }

  // Forecast chart
  if (forecast && forecast.forecast && forecast.forecast.length) {
    const fLabels = forecast.forecast.slice(0,12).map(f => formatTime(f.timestamp));
    const fData = forecast.forecast.slice(0,12).map(f => f.predicted_value);
    const fUpper = forecast.forecast.slice(0,12).map(f => f.upper_bound);
    const fLower = forecast.forecast.slice(0,12).map(f => f.lower_bound);
    out += `<div class="zd-section"><h3>📈 SST Forecast (${forecast.forecast_horizon_hours}h)</h3>
      <div class="chart-body" style="margin-bottom:12px">${buildAreaChart([
        { label:'Upper 95%', data:fUpper, color:'rgba(239,68,68,0.5)', labels:fLabels },
        { label:'Predicted', data:fData, color:'#e8c95a', labels:fLabels },
        { label:'Lower 95%', data:fLower, color:'rgba(34,197,94,0.4)', labels:fLabels },
      ], 600, 140)}</div>
    </div>`;
  }

  // Pattern Memory
  if (memory && memory.similar_events && memory.similar_events.length) {
    out += `<div class="zd-section"><h3>🧠 Pattern Memory</h3><div style="font-size:.82rem;color:var(--text2);margin-bottom:12px">${memory.insight||''}</div>`;
    memory.similar_events.forEach(ev => {
      out += `<div class="cascade-item"><div><div class="ci-target">${ev.days_ago}d ago — ${ev.outcome}</div><div class="ci-eta">${ev.signals_in_common.join(', ')} · ${ev.num_anomalies} anomalies</div></div><div class="ci-prob" style="color:var(--teal)">${(ev.similarity_score*100).toFixed(0)}%</div></div>`;
    });
    out += '</div>';
  }

  out += '</div>';
  html('zone-detail-content', out);
  if (window.lucide) lucide.createIcons();
}

// ═══════════════════════════════════════════════════
// INCIDENTS
// ═══════════════════════════════════════════════════

async function loadIncidents() {
  try {
    const data = await fetchJSON('/api/alerts?limit=20');
    const alerts = data.alerts || [];
    if (!alerts.length) { html('incidents-controls','<div class="empty">No alerts to generate reports for</div>'); return; }
    html('incidents-controls', `<div class="inc-select"><label style="font-size:.8rem;color:var(--text2);margin-bottom:6px;display:block">Select an alert to generate incident report:</label>
      <select id="inc-alert-select" onchange="loadIncidentReport(this.value)">
        <option value="">— Select Alert —</option>
        ${alerts.map(a => `<option value="${a.id}">[${a.severity.toUpperCase()}] ${a.title} — ${a.zone_name}</option>`).join('')}
      </select></div>`);
    html('incident-report','');
  } catch(e) { html('incidents-controls','<div class="error-msg">'+e.message+'</div>'); }
}

async function loadIncidentReport(alertId) {
  if (!alertId) { html('incident-report',''); return; }
  html('incident-report','<div class="loader">Generating incident report…</div>');
  try {
    const r = await fetchJSON(`/api/incident/${alertId}`);
    let h = `<div class="ir-report">
      <div><span class="ir-id">${r.report_id}</span><span class="ir-class badge ${sevClass(r.classification.toLowerCase())}">${r.classification}</span></div>
      <div class="ir-time">Generated: ${r.generated_at}</div>`;

    if (r.header) {
      h += `<div class="ir-section"><h4>Report Header</h4>`;
      Object.entries(r.header).forEach(([k,v]) => { h += `<div style="font-size:.8rem;margin-bottom:4px"><span style="color:var(--text3)">${k}:</span> <strong>${v}</strong></div>`; });
      h += '</div>';
    }

    if (r.scoring_breakdown) {
      h += `<div class="ir-section"><h4>Scoring Breakdown</h4><div class="sim-kv">`;
      Object.entries(r.scoring_breakdown).forEach(([k,v]) => { h += `<div class="sim-kv-item"><span class="kv-key">${k}</span><span class="kv-val">${typeof v==='number'?v.toFixed(3):v}</span></div>`; });
      h += '</div></div>';
    }

    if (r.timeline && r.timeline.length) {
      h += `<div class="ir-section"><h4>Event Timeline</h4><div class="ir-timeline">`;
      r.timeline.forEach(t => { h += `<div class="ir-tl-item"><strong>${t.time||t.timestamp||''}</strong> — ${t.event||t.description||JSON.stringify(t)}</div>`; });
      h += '</div></div>';
    }

    if (r.economic_impact) {
      h += `<div class="ir-section"><h4>Economic Impact</h4><div class="sim-kv">`;
      Object.entries(r.economic_impact).forEach(([k,v]) => { h += `<div class="sim-kv-item"><span class="kv-key">${k}</span><span class="kv-val">${typeof v==='number'?'₹'+v.toFixed(2)+' Cr':v}</span></div>`; });
      h += '</div></div>';
    }

    if (r.recommended_actions && r.recommended_actions.length) {
      h += `<div class="ir-section"><h4>Recommended Actions</h4><ul>${r.recommended_actions.map(a => `<li>${a}</li>`).join('')}</ul></div>`;
    }

    if (r.impact_summary) {
      h += `<div class="ir-section"><h4>Impact Summary</h4><div class="impact-summary">${r.impact_summary}</div></div>`;
    }

    h += `<div style="font-size:.7rem;color:var(--text3);margin-top:18px;font-style:italic">${r.disclaimer||''}</div></div>`;
    html('incident-report', h);
  } catch(e) { html('incident-report','<div class="error-msg">Failed to generate report: '+e.message+'</div>'); }
}

// ═══════════════════════════════════════════════════
// AI CHAT
// ═══════════════════════════════════════════════════

async function handleChat(e) {
  e.preventDefault();
  const input = $('chat-input');
  const msg = input.value.trim();
  if (!msg) return;
  input.value = '';

  const msgs = $('chat-messages');
  msgs.innerHTML += `<div class="chat-msg user"><div class="chat-bubble">${escapeHTML(msg)}</div></div>`;
  msgs.innerHTML += `<div class="chat-msg assistant" id="chat-loading"><div class="chat-bubble" style="color:var(--text3)">Thinking…</div></div>`;
  msgs.scrollTop = msgs.scrollHeight;

  try {
    const r = await postJSON('/api/chat', { message: msg, zone_id: null });
    const el = $('chat-loading');
    if (el) el.outerHTML = `<div class="chat-msg assistant"><div class="chat-bubble">${escapeHTML(r.response)}</div><div style="font-size:.65rem;color:var(--text3);margin-top:4px">Zones: ${(r.context_zones||[]).join(', ')||'—'} | Alerts referenced: ${r.alerts_referenced||0}</div></div>`;
  } catch(e) {
    const el = $('chat-loading');
    if (el) el.outerHTML = `<div class="chat-msg assistant"><div class="chat-bubble" style="border-color:rgba(239,68,68,0.3)">Sorry, I couldn't process that request. Error: ${e.message}</div></div>`;
  }
  msgs.scrollTop = msgs.scrollHeight;
}

function escapeHTML(s) { const d=document.createElement('div'); d.textContent=s; return d.innerHTML; }

// ═══════════════════════════════════════════════════
// SIMULATION
// ═══════════════════════════════════════════════════

async function loadSimSetup() {
  const sel = $('sim-zone');
  if (sel && sel.options.length <= 1) {
    try {
      const zones = state.zones.length ? state.zones : await fetchJSON('/api/zones');
      state.zones = zones;
      sel.innerHTML = zones.map(z => `<option value="${z.id}">${z.name}</option>`).join('');
    } catch(e) { sel.innerHTML = '<option>Error loading zones</option>'; }
  }
  html('sim-results','');
}

async function runSimulation() {
  const zoneId = $('sim-zone')?.value;
  if (!zoneId) { toast('Select a zone','error'); return; }
  const scenario = {};
  const sst = parseFloat($('sim-sst')?.value); if (sst) scenario.sst = sst;
  const chl = parseFloat($('sim-chl')?.value); if (chl) scenario.chlorophyll = chl;
  const wind = parseFloat($('sim-wind')?.value); if (wind) scenario.wind_speed = wind;
  const ph = parseFloat($('sim-ph')?.value); if (ph) scenario.ph = ph;
  const turb = parseFloat($('sim-turb')?.value); if (turb) scenario.turbidity = turb;

  if (!Object.keys(scenario).length) { toast('Set at least one parameter','error'); return; }

  html('sim-results','<div class="loader">Running simulation…</div>');
  try {
    const r = await postJSON('/api/simulate', { zone_id: zoneId, scenario });
    let h = `<div class="sim-result"><h3>🎯 Risk Assessment — ${r.zone_name}</h3><div class="sim-kv">`;
    if (r.risk_assessment) Object.entries(r.risk_assessment).forEach(([k,v]) => {
      h += `<div class="sim-kv-item"><span class="kv-key">${k}</span><span class="kv-val" style="color:${typeof v==='number'&&v>0.5?'var(--critical)':'var(--text)'}">${typeof v==='number'?v.toFixed(3):v}</span></div>`;
    });
    h += '</div></div>';

    if (r.cascading_effects && Object.keys(r.cascading_effects).length) {
      h += `<div class="sim-result"><h3>🔗 Cascading Effects</h3><div class="sim-kv">`;
      Object.entries(r.cascading_effects).forEach(([k,v]) => {
        h += `<div class="sim-kv-item"><span class="kv-key">${k}</span><span class="kv-val">${typeof v==='number'?v.toFixed(3):JSON.stringify(v)}</span></div>`;
      });
      h += '</div></div>';
    }

    if (r.economic_impact && Object.keys(r.economic_impact).length) {
      h += `<div class="sim-result"><h3>💰 Projected Economic Impact</h3><div class="sim-kv">`;
      Object.entries(r.economic_impact).forEach(([k,v]) => {
        h += `<div class="sim-kv-item"><span class="kv-key">${k}</span><span class="kv-val">${typeof v==='number'?'₹'+v.toFixed(2)+' Cr':v}</span></div>`;
      });
      h += '</div></div>';
    }

    if (r.recommendations && r.recommendations.length) {
      h += `<div class="sim-result"><h3>📋 Recommendations</h3><ul style="list-style:none;padding:0">`;
      r.recommendations.forEach(rec => { h += `<li style="font-size:.82rem;padding:5px 0;color:var(--text2)"><span style="color:var(--teal);margin-right:8px">›</span>${rec}</li>`; });
      h += '</ul></div>';
    }

    html('sim-results', h);
    toast('Simulation complete!', 'success');
  } catch(e) { html('sim-results','<div class="error-msg">Simulation failed: '+e.message+'</div>'); }
}

// ═══════════════════════════════════════════════════
// AGENT LOGS
// ═══════════════════════════════════════════════════

async function loadLogs() {
  html('logs-content','<div class="loader">Loading agent logs…</div>');
  try {
    const data = await fetchJSON('/api/agent-logs?limit=50');
    let h = '';

    if (data.agent_activity) {
      h += '<div class="log-activity">';
      Object.entries(data.agent_activity).forEach(([agent, count]) => {
        h += `<div class="log-act-chip"><span class="la-name">${agent}</span><span class="la-count">${count}</span></div>`;
      });
      h += '</div>';
    }

    const icons = {'Data Agent':'📡','Analysis Agent':'🔵','Decision Agent':'🟡','Memory Agent':'🟣','Explanation Agent':'🔴','Cascade Agent':'🔗','Impact Agent':'💰','Intelligence Agent':'🧬','Telegram Agent':'📱','Scheduler':'⏰'};
    (data.logs||[]).forEach(log => {
      const icon = icons[log.agent] || '🤖';
      h += `<div class="log-item">
        <div class="log-icon">${icon}</div>
        <div class="log-body">
          <div class="log-agent">${log.agent}</div>
          <div class="log-action">${log.action}</div>
          <div class="log-details">${log.details}${log.zone_id?' · Zone: '+log.zone_id:''}</div>
        </div>
        <div class="log-time">${formatTime(log.timestamp)}</div>
      </div>`;
    });

    if (!data.logs || !data.logs.length) h += '<div class="empty">No agent logs yet</div>';
    html('logs-content', h);
  } catch(e) { html('logs-content','<div class="error-msg">'+e.message+'</div>'); }
}

// ═══════════════════════════════════════════════════
// INIT
// ═══════════════════════════════════════════════════

document.addEventListener('DOMContentLoaded', () => {
  if (window.lucide) lucide.createIcons();

  document.querySelectorAll('.nav-tab').forEach(tab => {
    tab.addEventListener('click', () => switchTab(tab.dataset.tab));
  });

  $('chat-input')?.addEventListener('keydown', e => {
    if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); $('chat-form')?.dispatchEvent(new Event('submit')); }
  });

  loadDashboard();

  setInterval(() => {
    if ($('page-dashboard')?.classList.contains('active')) loadDashboard();
  }, 60000);
});
