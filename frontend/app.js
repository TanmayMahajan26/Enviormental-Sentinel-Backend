/**
 * EcoSentinel — Ultra Premium Dashboard
 * Every page stunning. Zero compromise.
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
function sevColor(s) { return s==='critical'?'#f43f5e':s==='high'?'#f97316':s==='medium'?'#eab308':'#10b981'; }
function sevClass(s) { return s==='critical'?'critical':s==='high'?'high':s==='medium'?'medium':'low'; }
function riskColor(score) { return score>0.7?'#f43f5e':score>0.4?'#f97316':score>0.2?'#eab308':'#10b981'; }
function riskGrad(score) { return score>0.7?'linear-gradient(90deg,#be123c,#f43f5e)':score>0.4?'linear-gradient(90deg,#c2410c,#f97316)':score>0.2?'linear-gradient(90deg,#a16207,#eab308)':'linear-gradient(90deg,#059669,#10b981)'; }
function riskLabel(score) { return score>0.7?'CRITICAL':score>0.4?'HIGH':score>0.2?'MEDIUM':'NORMAL'; }
function escapeHTML(s) { const d=document.createElement('div'); d.textContent=s; return d.innerHTML; }
function toast(msg, type='info') {
  const c = $('toast-container'), t = document.createElement('div');
  t.className = 'toast '+type; t.textContent = msg; c.appendChild(t);
  setTimeout(() => { t.style.opacity='0'; t.style.transform='translateX(20px)'; setTimeout(()=>t.remove(),400); }, 3800);
}
function sevIcon(s) {
  const icons = { critical:'🔴', high:'🟠', medium:'🟡', low:'🟢' };
  return icons[s] || '⚪';
}

// ═══════════════════════════════════════════════════
// SVG GAUGE — Circular ring meter
// ═══════════════════════════════════════════════════

function buildGauge(value, max, label, unit, color, size=120) {
  const pct = Math.min(value / max, 1);
  const r = (size - 18) / 2;
  const circ = 2 * Math.PI * r;
  const dash = circ * pct;
  const gap = circ - dash;
  const uid = 'g-' + label.replace(/\W/g,'') + Math.random().toString(36).substr(2,4);
  return `<div class="gauge-ring" style="width:${size}px;height:${size}px;" title="${label}: ${typeof value==='number'?value.toFixed(1):value} ${unit||''}">
    <svg viewBox="0 0 ${size} ${size}">
      <defs>
        <linearGradient id="${uid}" x1="0%" y1="0%" x2="100%" y2="100%">
          <stop offset="0%" stop-color="${color}" stop-opacity="0.6"/>
          <stop offset="100%" stop-color="${color}"/>
        </linearGradient>
        <filter id="glow-${uid}"><feGaussianBlur stdDeviation="3" result="blur"/><feMerge><feMergeNode in="blur"/><feMergeNode in="SourceGraphic"/></feMerge></filter>
      </defs>
      <circle class="gauge-bg" cx="${size/2}" cy="${size/2}" r="${r}"/>
      <circle class="gauge-fill" cx="${size/2}" cy="${size/2}" r="${r}"
        stroke="url(#${uid})" stroke-dasharray="${dash} ${gap}"
        filter="url(#glow-${uid})"/>
    </svg>
    <div class="gauge-label">
      <span class="gauge-value" style="color:${color}">${typeof value==='number'?(value<10?value.toFixed(1):Math.round(value)):value}</span>
      <span class="gauge-name">${label}${unit?' '+unit:''}</span>
    </div>
  </div>`;
}

// ═══════════════════════════════════════════════════
// SVG AREA CHART — Gradient-filled trend vis
// ═══════════════════════════════════════════════════

function buildAreaChart(datasets, width=900, height=180) {
  const pad = { top:12, right:12, bottom:30, left:44 };
  const w = width - pad.left - pad.right;
  const h = height - pad.top - pad.bottom;
  let allVals = [];
  datasets.forEach(ds => ds.data.forEach(v => allVals.push(v)));
  if (!allVals.length) return '';
  const minY = Math.min(...allVals) * 0.92;
  const maxY = Math.max(...allVals) * 1.08;
  const range = maxY - minY || 1;
  function toX(i, len) { return pad.left + (i / Math.max(len - 1, 1)) * w; }
  function toY(v) { return pad.top + h - ((v - minY) / range) * h; }

  let svg = `<svg viewBox="0 0 ${width} ${height}" preserveAspectRatio="none" style="height:${height}px;">`;

  // Grid
  for (let i = 0; i <= 4; i++) {
    const y = pad.top + (h / 4) * i;
    const val = maxY - (range / 4) * i;
    svg += `<line x1="${pad.left}" y1="${y}" x2="${width-pad.right}" y2="${y}" stroke="rgba(255,255,255,0.03)" stroke-width="1"/>`;
    svg += `<text x="${pad.left-7}" y="${y+3}" fill="rgba(255,255,255,0.15)" font-size="9" font-family="'JetBrains Mono'" text-anchor="end">${val.toFixed(1)}</text>`;
  }

  datasets.forEach((ds, di) => {
    const n = ds.data.length; if (n < 2) return;
    const gid = `ag-${di}-${Math.random().toString(36).substr(2,4)}`;
    let pts = [];
    for (let i = 0; i < n; i++) pts.push(`${toX(i,n).toFixed(1)},${toY(ds.data[i]).toFixed(1)}`);
    const lineD = 'M' + pts.join(' L');
    const areaD = lineD + ` L${toX(n-1,n).toFixed(1)},${pad.top+h} L${toX(0,n).toFixed(1)},${pad.top+h} Z`;

    svg += `<defs><linearGradient id="${gid}" x1="0" y1="0" x2="0" y2="1">
      <stop offset="0%" stop-color="${ds.color}" stop-opacity="0.3"/>
      <stop offset="100%" stop-color="${ds.color}" stop-opacity="0.01"/>
    </linearGradient></defs>`;
    svg += `<path d="${areaD}" fill="url(#${gid})"/>`;
    svg += `<path d="${lineD}" fill="none" stroke="${ds.color}" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round" style="filter:drop-shadow(0 0 6px ${ds.color}30)"/>`;

    // Points
    const pStep = Math.max(1, Math.floor(n/8));
    for (let i = 0; i < n; i++) {
      if (i % pStep === 0 || i === n-1) {
        const cx = toX(i,n).toFixed(1), cy = toY(ds.data[i]).toFixed(1);
        svg += `<circle cx="${cx}" cy="${cy}" r="4" fill="${ds.color}" stroke="rgba(5,8,16,0.8)" stroke-width="2"/>`;
      }
    }
  });

  // X labels
  const labels = datasets[0]?.labels || [];
  const xStep = Math.max(1, Math.floor(labels.length / 6));
  labels.forEach((lbl, i) => {
    if (i % xStep === 0 || i === labels.length - 1) {
      svg += `<text x="${toX(i,labels.length).toFixed(1)}" y="${height-5}" fill="rgba(255,255,255,0.18)" font-size="9" font-family="'JetBrains Mono'" text-anchor="middle">${lbl}</text>`;
    }
  });
  svg += '</svg>';
  return svg;
}

// ═══════════════════════════════════════════════════
// MINI BAR CHART — For alerts/incidents inline
// ═══════════════════════════════════════════════════

function buildMiniBar(values, colors, width=200, height=40) {
  if (!values.length) return '';
  const max = Math.max(...values, 1);
  const barW = Math.min(24, (width - values.length * 3) / values.length);
  let svg = `<svg width="${width}" height="${height}" viewBox="0 0 ${width} ${height}">`;
  values.forEach((v, i) => {
    const bh = (v / max) * (height - 6);
    const x = i * (barW + 3) + 2;
    const col = colors[i % colors.length];
    svg += `<rect x="${x}" y="${height - bh - 2}" width="${barW}" height="${bh}" rx="3" fill="${col}" opacity="0.7"/>`;
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
// DASHBOARD — Gauges + Charts + Zone Intelligence
// ═══════════════════════════════════════════════════

async function loadDashboard() {
  // System health
  try {
    const h = await fetchJSON('/api/system/health');
    state.health = h;
    const dot = document.querySelector('#nav-status .status-dot');
    const txt = document.querySelector('#nav-status .status-text');
    if (dot) dot.classList.remove('offline');
    if (txt) { const s=h.uptime_seconds; txt.textContent = s<60?'Online — just started':s<3600?`Online — ${Math.floor(s/60)}m`:`Online — ${Math.floor(s/3600)}h`; }

    html('stats-row', `
      <div class="stat-card"><span class="stat-icon">🎯</span><div class="stat-val">${h.total_zones}</div><div class="stat-lbl">Zones Active</div></div>
      <div class="stat-card"><span class="stat-icon">📡</span><div class="stat-val">${(h.total_readings/1000).toFixed(1)}k</div><div class="stat-lbl">Data Points</div></div>
      <div class="stat-card"><span class="stat-icon">⚠️</span><div class="stat-val">${h.total_anomalies_detected}</div><div class="stat-lbl">Anomalies</div></div>
      <div class="stat-card"><span class="stat-icon">🚨</span><div class="stat-val">${h.total_alerts_generated}</div><div class="stat-lbl">Alerts</div></div>
      <div class="stat-card"><span class="stat-icon">🧠</span><div class="stat-val">${(h.model_accuracy*100).toFixed(0)}%</div><div class="stat-lbl">ML Accuracy</div></div>
      <div class="stat-card"><span class="stat-icon">⏱️</span><div class="stat-val">${h.uptime_seconds<3600?Math.floor(h.uptime_seconds/60)+'m':Math.floor(h.uptime_seconds/3600)+'h'}</div><div class="stat-lbl">Uptime</div></div>
    `);

    // Gauges
    const acc = h.model_accuracy * 100;
    const anomR = Math.min((h.total_anomalies_detected / Math.max(h.total_readings,1)) * 1000, 100);
    html('system-gauges',
      buildGauge(acc, 100, 'Accuracy', '%', '#2dd4bf') +
      buildGauge(h.total_zones, 8, 'Zones', '', '#e8c95a') +
      buildGauge(h.total_anomalies_detected, Math.max(h.total_anomalies_detected, 50), 'Anomalies', '', anomR > 60 ? '#f43f5e' : '#f97316') +
      buildGauge(h.total_alerts_generated, Math.max(h.total_alerts_generated, 20), 'Alerts', '', '#eab308') +
      buildGauge(parseFloat((h.total_readings/1000).toFixed(1)), 25, 'Data', 'k', '#3b82f6') +
      buildGauge(h.uptime_seconds < 3600 ? Math.floor(h.uptime_seconds/60) : Math.floor(h.uptime_seconds/3600), h.uptime_seconds < 3600 ? 60 : 24, 'Uptime', h.uptime_seconds < 3600 ? 'm' : 'h', '#a78bfa')
    );
  } catch(e) {
    const dot = document.querySelector('#nav-status .status-dot');
    if (dot) dot.classList.add('offline');
    const txt = document.querySelector('#nav-status .status-text');
    if (txt) txt.textContent = 'Offline';
    html('stats-row','<div class="error-msg">Backend offline — start with: <code class="mono">python main.py</code></div>');
    html('system-gauges','');
  }

  // Zones
  try {
    const zones = await fetchJSON('/api/zones');
    state.zones = zones;
    if (!zones.length) { html('zone-grid','<div class="empty">No zones found — run data ingestion first</div>'); }
    else {
      html('zone-grid', zones.map((z, idx) => {
        const score = z.anomaly_score || 0;
        const label = riskLabel(score);
        const col = riskColor(score);
        const pct = Math.min(score * 100, 100);
        return `<div class="zone-card" onclick="showZoneDetail('${z.id}')" style="animation-delay:${idx*60}ms">
          <div class="zc-top"><h3>${z.name}</h3><span class="badge ${sevClass(label.toLowerCase())}">${label}</span></div>
          <div class="zc-region"><i data-lucide="map-pin" style="width:12px;height:12px"></i>${z.region} · ${z.lat.toFixed(2)}°N, ${z.lng.toFixed(2)}°E</div>
          <div class="zc-signals">
            <div class="zc-sig"><div class="zc-sig-label">Sensitivity</div><div class="zc-sig-val">${z.current_sensitivity.toFixed(2)}</div></div>
            <div class="zc-sig"><div class="zc-sig-label">Alerts 24h</div><div class="zc-sig-val" style="color:${z.alert_count_24h>10?'#f97316':'inherit'}">${z.alert_count_24h}</div></div>
            <div class="zc-sig"><div class="zc-sig-label">Anomaly</div><div class="zc-sig-val" style="color:${col}">${score.toFixed(3)}</div></div>
          </div>
          <div class="zc-risk"><div class="zc-bar"><div class="zc-bar-fill" style="width:${pct}%;background:${riskGrad(score)}"></div></div><span class="zc-score" style="color:${col}">${score.toFixed(2)}</span></div>
        </div>`;
      }).join(''));
    }
    loadTrendChart(zones);
  } catch(e) { html('zone-grid','<div class="error-msg">Failed to load zones: '+e.message+'</div>'); }

  // Alerts
  try {
    const data = await fetchJSON('/api/alerts?limit=5');
    state.alerts = data.alerts || [];
    if (!state.alerts.length) { html('dash-alerts','<div class="empty">No active alerts</div>'); }
    else { html('dash-alerts', state.alerts.map(a => alertItemHTML(a, false)).join('')); }
  } catch(e) { html('dash-alerts','<div class="error-msg">'+e.message+'</div>'); }

  // Briefing
  try {
    const b = await fetchJSON('/api/briefing');
    html('dash-briefing', `<div class="briefing-box">
      <div class="briefing-text">${b.summary}</div>
      <div class="briefing-meta">
        <span class="briefing-confidence" style="color:${b.system_confidence>.7?'#10b981':b.system_confidence>.4?'#eab308':'#f43f5e'}">${(b.system_confidence*100).toFixed(0)}% confidence</span>
        <span>Zones needing attention: <strong>${(b.zones_requiring_attention||[]).join(', ')||'None'}</strong></span>
      </div></div>`);
  } catch(e) { html('dash-briefing','<div class="error-msg">Briefing unavailable</div>'); }

  if (window.lucide) lucide.createIcons();
}

// ═══════════════════════════════════════════════════
// TREND CHART
// ═══════════════════════════════════════════════════

async function loadTrendChart(zones) {
  if (!zones || !zones.length) return;
  const topZone = zones.reduce((a, b) => (a.anomaly_score || 0) > (b.anomaly_score || 0) ? a : b);
  try {
    const data = await fetchJSON(`/api/zones/${topZone.id}/readings?limit=24`);
    if (!data.readings || data.readings.length < 2) {
      html('trend-chart', '<div class="empty" style="padding:24px">Waiting for signal data…</div>');
      return;
    }
    const readings = data.readings;
    const labels = readings.map(r => { try { return new Date(r.timestamp).getHours()+':00'; } catch(_) { return ''; } });
    html('trend-chart', buildAreaChart([
      { label:'SST', data:readings.map(r=>r.sst||0), color:'#e8c95a', labels },
      { label:'Chl-a', data:readings.map(r=>r.chlorophyll||0), color:'#2dd4bf', labels },
      { label:'Wind', data:readings.map(r=>r.wind_speed||0), color:'#3b82f6', labels },
    ], 900, 180));
    const titleEl = document.querySelector('#trend-chart-panel .chart-title');
    if (titleEl) titleEl.innerHTML = `<i data-lucide="trending-up" style="width:16px;height:16px;color:var(--gold2)"></i> Signal Trend — ${topZone.name} (24h)`;
    if (window.lucide) lucide.createIcons();
  } catch(e) { html('trend-chart', '<div class="empty" style="padding:24px">Chart unavailable</div>'); }
}

// ═══════════════════════════════════════════════════
// ALERT HTML — Premium severity-driven card
// ═══════════════════════════════════════════════════

function alertItemHTML(a, showFeedback=true) {
  const sev = a.severity || 'medium';
  const signals = (a.signals_involved || []);
  return `<div class="alert-item">
    <div class="alert-sev-bar ${sevClass(sev)}"></div>
    <div class="alert-body">
      <div style="display:flex;align-items:flex-start;gap:14px">
        <div class="alert-icon ${sevClass(sev)}">${sevIcon(sev)}</div>
        <div style="flex:1;min-width:0">
          <div class="alert-title">${a.title||a.description||'Environmental Alert'}</div>
          <div class="alert-meta">
            <span class="badge ${sevClass(sev)}">${sev}</span>
            <span class="alert-priority" style="color:${riskColor(a.priority_score||0)}">${(a.priority_score||0).toFixed(3)}</span>
            <span><i data-lucide="map-pin" style="width:11px;height:11px"></i> ${a.zone_name||a.zone_id||'—'}</span>
            <span><i data-lucide="clock" style="width:11px;height:11px"></i> ${formatTime(a.timestamp)}</span>
          </div>
          ${signals.length ? `<div class="alert-signals">${signals.map(s=>`<span class="alert-signal-chip">${s}</span>`).join('')}</div>` : ''}
          ${showFeedback && !a.feedback ? `<div class="alert-actions">
            <button class="btn-fb" onclick="event.stopPropagation();submitFeedback(${a.id},'validated')"><i data-lucide="check" style="width:12px;height:12px"></i> Validated</button>
            <button class="btn-fb reject" onclick="event.stopPropagation();submitFeedback(${a.id},'false_positive')"><i data-lucide="x" style="width:12px;height:12px"></i> False Positive</button>
          </div>` : a.feedback ? `<div style="font-size:.72rem;color:var(--text3);margin-top:8px;font-style:italic">✓ Feedback: ${a.feedback}</div>` : ''}
        </div>
      </div>
    </div></div>`;
}

// ═══════════════════════════════════════════════════
// ALERTS PAGE — Full premium view with stats
// ═══════════════════════════════════════════════════

async function loadAlerts() {
  html('alerts-list','<div class="loader">Fetching priority alerts…</div>');
  try {
    const data = await fetchJSON('/api/alerts?limit=50&include_suppressed=true');
    const alerts = data.alerts || [];
    if (!alerts.length) { html('alerts-list','<div class="empty">No alerts generated yet — system is learning</div>'); return; }

    // Compute severity distribution
    const sevCounts = { critical:0, high:0, medium:0, low:0 };
    alerts.forEach(a => { sevCounts[a.severity] = (sevCounts[a.severity]||0) + 1; });

    let out = `<div class="alerts-stats">
      <div class="alert-stat"><div class="as-val" style="color:#f43f5e">${sevCounts.critical}</div><div class="as-lbl">Critical</div></div>
      <div class="alert-stat"><div class="as-val" style="color:#f97316">${sevCounts.high}</div><div class="as-lbl">High</div></div>
      <div class="alert-stat"><div class="as-val" style="color:#eab308">${sevCounts.medium}</div><div class="as-lbl">Medium</div></div>
      <div class="alert-stat"><div class="as-val" style="color:#10b981">${data.active_alerts||alerts.length}</div><div class="as-lbl">Active</div></div>
    </div>`;
    out += `<div style="margin-bottom:16px;font-size:.78rem;color:var(--text2);display:flex;gap:16px;align-items:center;flex-wrap:wrap">
      <span>Total: <strong class="mono" style="color:var(--text)">${data.total}</strong></span>
      <span>Active: <strong class="mono" style="color:var(--teal)">${data.active_alerts}</strong></span>
      <span>Suppressed: <strong class="mono" style="color:var(--text3)">${data.suppressed_alerts}</strong></span>
    </div>`;
    out += alerts.map(a => alertItemHTML(a, true)).join('');
    html('alerts-list', out);
  } catch(e) { html('alerts-list','<div class="error-msg">'+e.message+'</div>'); }
  if (window.lucide) lucide.createIcons();
}

async function submitFeedback(alertId, feedback) {
  try {
    const r = await postJSON(`/api/alerts/${alertId}/feedback`, { feedback, notes:'' });
    toast(`Feedback recorded! Sensitivity: ${r.zone_sensitivity_before.toFixed(2)} → ${r.zone_sensitivity_after.toFixed(2)}`, 'success');
    loadAlerts();
  } catch(e) { toast('Feedback failed: '+e.message, 'error'); }
}

// ═══════════════════════════════════════════════════
// ZONE DETAIL — Full intelligence view with charts
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

  // Signal gauges
  if (readings && readings.readings && readings.readings.length) {
    const latest = readings.readings[readings.readings.length-1];
    out += `<div class="gauge-panel mb-24"><div class="gauge-header"><div class="gauge-title"><i data-lucide="activity" style="width:16px;height:16px;color:var(--teal)"></i> Current Readings</div></div>
      <div class="gauge-container">
        ${buildGauge(latest.sst||0, 35, 'SST', '°C', '#e8c95a')}
        ${buildGauge(latest.chlorophyll||0, 10, 'Chl-a', 'mg/m³', '#2dd4bf')}
        ${buildGauge(latest.wind_speed||0, 20, 'Wind', 'm/s', '#3b82f6')}
        ${buildGauge(latest.ph||0, 9, 'pH', '', '#a78bfa')}
        ${buildGauge(latest.turbidity||0, 15, 'Turbidity', 'NTU', '#f97316')}
      </div></div>`;

    // Area chart
    const labels = readings.readings.map(r => { try { return new Date(r.timestamp).getHours()+':00'; } catch(_) { return ''; } });
    out += `<div class="chart-panel mb-24"><div class="chart-header"><div class="chart-title"><i data-lucide="trending-up" style="width:16px;height:16px;color:var(--gold2)"></i> 24h Signal Trends</div>
      <div class="chart-legend">
        <div class="legend-item"><span class="legend-dot" style="background:#e8c95a"></span>SST</div>
        <div class="legend-item"><span class="legend-dot" style="background:#2dd4bf"></span>Chl-a</div>
        <div class="legend-item"><span class="legend-dot" style="background:#3b82f6"></span>Wind</div>
      </div></div>
      <div class="chart-body">${buildAreaChart([
        { label:'SST', data:readings.readings.map(r=>r.sst||0), color:'#e8c95a', labels },
        { label:'Chl-a', data:readings.readings.map(r=>r.chlorophyll||0), color:'#2dd4bf', labels },
        { label:'Wind', data:readings.readings.map(r=>r.wind_speed||0), color:'#3b82f6', labels },
      ], 900, 180)}</div></div>`;
  }

  out += '<div class="zd-grid">';

  // Root Cause
  if (rootcause && rootcause.root_causes) {
    out += `<div class="zd-section"><h3>🔍 Root Cause Analysis</h3>`;
    rootcause.root_causes.forEach(rc => {
      const pct = (rc.confidence*100).toFixed(0);
      out += `<div class="rc-bar-row"><div class="rc-bar-head"><span>${rc.cause}</span><span style="color:var(--teal)">${pct}%</span></div>
        <div class="rc-bar"><div class="rc-bar-fill" style="width:${pct}%;background:linear-gradient(90deg,rgba(45,212,191,0.2),var(--teal))"></div></div>
        <div style="font-size:.7rem;color:var(--text3);margin-top:3px">${rc.mechanism}</div></div>`;
    });
    out += '</div>';
  }

  // Cascade
  if (cascade && cascade.predictions && cascade.predictions.length) {
    out += `<div class="zd-section"><h3>🔗 Cascade Predictions</h3>`;
    cascade.predictions.forEach(p => {
      out += `<div class="cascade-item"><div><div class="ci-target">→ ${p.target_zone_name}</div><div class="ci-eta">${p.propagation_days_min}–${p.propagation_days_max} days · ${p.mechanism}</div></div><div class="ci-prob" style="color:${riskColor(p.cascade_probability)}">${(p.cascade_probability*100).toFixed(0)}%</div></div>`;
    });
    out += '</div>';
  }

  // Economic Impact
  if (impact && impact.economic_impact) {
    const ei = impact.economic_impact;
    out += `<div class="zd-section"><h3>💰 Economic Impact</h3>
      <div class="impact-row">
        <div class="impact-item"><div class="ii-val">₹${ei.fishing_impact_crore?.toFixed(1)||0}</div><div class="ii-lbl">Fishing (Cr)</div></div>
        <div class="impact-item"><div class="ii-val">₹${ei.shipping_impact_crore?.toFixed(1)||0}</div><div class="ii-lbl">Shipping (Cr)</div></div>
        <div class="impact-item"><div class="ii-val">₹${ei.tourism_impact_crore?.toFixed(1)||0}</div><div class="ii-lbl">Tourism (Cr)</div></div>
      </div>
      <div class="impact-summary">${impact.impact_summary||''}</div></div>`;
  }

  // Time to Risk
  if (ttr && ttr.warnings && ttr.warnings.length) {
    out += `<div class="zd-section"><h3>⏰ Time-to-Risk Warning</h3>`;
    ttr.warnings.forEach(w => {
      out += `<div class="ttr-item"><div class="ttr-signal">${w.signal.toUpperCase()} — ${w.trend}</div>
        <div class="ttr-text">Current: <strong>${w.current_value.toFixed(2)}</strong> | Baseline: ${w.baseline.toFixed(2)} | Rate: ${w.rate_per_day.toFixed(3)}/day</div>
        ${w.human_readable?`<div style="font-size:.78rem;color:var(--high);margin-top:5px;font-weight:600">${w.human_readable}</div>`:''}
      </div>`;
    });
    out += '</div>';
  }

  // Forecast
  if (forecast && forecast.forecast && forecast.forecast.length) {
    const fLabels = forecast.forecast.slice(0,12).map(f=>formatTime(f.timestamp));
    out += `<div class="zd-section"><h3>📈 SST Forecast (${forecast.forecast_horizon_hours}h)</h3>
      <div class="chart-body" style="margin-bottom:12px">${buildAreaChart([
        { label:'Upper', data:forecast.forecast.slice(0,12).map(f=>f.upper_bound), color:'rgba(244,63,94,0.5)', labels:fLabels },
        { label:'Predicted', data:forecast.forecast.slice(0,12).map(f=>f.predicted_value), color:'#e8c95a', labels:fLabels },
        { label:'Lower', data:forecast.forecast.slice(0,12).map(f=>f.lower_bound), color:'rgba(16,185,129,0.4)', labels:fLabels },
      ], 600, 150)}</div></div>`;
  }

  // Pattern Memory
  if (memory && memory.similar_events && memory.similar_events.length) {
    out += `<div class="zd-section"><h3>🧠 Pattern Memory</h3><div style="font-size:.82rem;color:var(--text2);margin-bottom:14px;line-height:1.6">${memory.insight||''}</div>`;
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
// INCIDENTS — Premium report generator
// ═══════════════════════════════════════════════════

async function loadIncidents() {
  try {
    const data = await fetchJSON('/api/alerts?limit=20');
    const alerts = data.alerts || [];
    if (!alerts.length) { html('incidents-controls','<div class="empty">No alerts to generate reports for</div>'); return; }
    html('incidents-controls', `<div class="inc-select">
      <label>Select an alert to generate a detailed incident report:</label>
      <select id="inc-alert-select" onchange="loadIncidentReport(this.value)">
        <option value="">— Choose an Alert —</option>
        ${alerts.map(a => `<option value="${a.id}">${sevIcon(a.severity)} [${a.severity.toUpperCase()}] ${a.title} — ${a.zone_name}</option>`).join('')}
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
      <div class="ir-header"><span class="ir-id">${r.report_id}</span><span class="ir-class badge ${sevClass(r.classification.toLowerCase())}">${r.classification}</span></div>
      <div class="ir-time"><i data-lucide="clock" style="width:12px;height:12px"></i> Generated: ${r.generated_at}</div>`;

    if (r.header) {
      h += `<div class="ir-section"><h4><i data-lucide="file-text" style="width:14px;height:14px"></i> Report Header</h4><div class="sim-kv" style="grid-template-columns:repeat(auto-fill,minmax(200px,1fr))">`;
      Object.entries(r.header).forEach(([k,v]) => { h += `<div class="sim-kv-item"><span class="kv-key">${k}</span><span class="kv-val">${v}</span></div>`; });
      h += '</div></div>';
    }

    if (r.scoring_breakdown) {
      h += `<div class="ir-section"><h4><i data-lucide="bar-chart-3" style="width:14px;height:14px"></i> Scoring Breakdown</h4><div class="sim-kv">`;
      Object.entries(r.scoring_breakdown).forEach(([k,v]) => {
        const isHigh = typeof v==='number' && v > 0.5;
        h += `<div class="sim-kv-item"><span class="kv-key">${k}</span><span class="kv-val" style="color:${isHigh?'var(--critical)':'var(--text)'}">${typeof v==='number'?v.toFixed(3):v}</span></div>`;
      });
      h += '</div></div>';
    }

    if (r.timeline && r.timeline.length) {
      h += `<div class="ir-section"><h4><i data-lucide="git-branch" style="width:14px;height:14px"></i> Event Timeline</h4><div class="ir-timeline">`;
      r.timeline.forEach(t => { h += `<div class="ir-tl-item"><strong>${t.time||t.timestamp||''}</strong> — ${t.event||t.description||JSON.stringify(t)}</div>`; });
      h += '</div></div>';
    }

    if (r.economic_impact) {
      h += `<div class="ir-section"><h4><i data-lucide="indian-rupee" style="width:14px;height:14px"></i> Economic Impact</h4><div class="sim-kv">`;
      Object.entries(r.economic_impact).forEach(([k,v]) => { h += `<div class="sim-kv-item"><span class="kv-key">${k}</span><span class="kv-val" style="color:var(--gold2)">${typeof v==='number'?'₹'+v.toFixed(2)+' Cr':v}</span></div>`; });
      h += '</div></div>';
    }

    if (r.recommended_actions && r.recommended_actions.length) {
      h += `<div class="ir-section"><h4><i data-lucide="list-checks" style="width:14px;height:14px"></i> Recommended Actions</h4><ul>${r.recommended_actions.map(a => `<li>${a}</li>`).join('')}</ul></div>`;
    }

    if (r.impact_summary) {
      h += `<div class="ir-section"><h4><i data-lucide="alert-circle" style="width:14px;height:14px"></i> Impact Summary</h4><div class="impact-summary">${r.impact_summary}</div></div>`;
    }

    h += `<div style="font-size:.7rem;color:var(--text3);margin-top:20px;font-style:italic;padding-top:14px;border-top:1px solid var(--border)">${r.disclaimer||''}</div></div>`;
    html('incident-report', h);
  } catch(e) { html('incident-report','<div class="error-msg">Failed to generate report: '+e.message+'</div>'); }
  if (window.lucide) lucide.createIcons();
}

// ═══════════════════════════════════════════════════
// AI CHAT — with avatars and typing indicator
// ═══════════════════════════════════════════════════

async function handleChat(e) {
  e.preventDefault();
  const input = $('chat-input');
  const msg = input.value.trim();
  if (!msg) return;
  input.value = '';

  const msgs = $('chat-messages');
  msgs.innerHTML += `<div class="chat-msg user"><div class="chat-bubble">${escapeHTML(msg)}</div><div class="chat-avatar">👤</div></div>`;
  msgs.innerHTML += `<div class="chat-msg assistant" id="chat-loading"><div class="chat-avatar">🤖</div><div class="chat-bubble"><div class="chat-typing"><span></span><span></span><span></span></div></div></div>`;
  msgs.scrollTop = msgs.scrollHeight;

  try {
    const r = await postJSON('/api/chat', { message: msg, zone_id: null });
    const el = $('chat-loading');
    if (el) el.outerHTML = `<div class="chat-msg assistant"><div class="chat-avatar">🤖</div><div class="chat-bubble">${escapeHTML(r.response)}<div class="chat-meta"><span>Zones: ${(r.context_zones||[]).join(', ')||'—'}</span><span>Alerts: ${r.alerts_referenced||0}</span></div></div></div>`;
  } catch(e) {
    const el = $('chat-loading');
    if (el) el.outerHTML = `<div class="chat-msg assistant"><div class="chat-avatar">🤖</div><div class="chat-bubble" style="border-color:rgba(244,63,94,0.2)">Sorry, I couldn't process that. Error: ${e.message}</div></div>`;
  }
  msgs.scrollTop = msgs.scrollHeight;
  if (window.lucide) lucide.createIcons();
}

// ═══════════════════════════════════════════════════
// SIMULATION — with animated results
// ═══════════════════════════════════════════════════

async function loadSimSetup() {
  const sel = $('sim-zone');
  if (sel && sel.options.length <= 1) {
    try {
      const zones = state.zones.length ? state.zones : await fetchJSON('/api/zones');
      state.zones = zones;
      sel.innerHTML = zones.map(z => `<option value="${z.id}">${z.name} — ${z.region}</option>`).join('');
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

  html('sim-results','<div class="loader">Running what-if simulation…</div>');
  try {
    const r = await postJSON('/api/simulate', { zone_id: zoneId, scenario });
    let h = '';

    // Risk assessment
    h += `<div class="sim-result"><h3>🎯 Risk Assessment — ${r.zone_name}</h3><div class="sim-kv">`;
    if (r.risk_assessment) Object.entries(r.risk_assessment).forEach(([k,v]) => {
      const isHigh = typeof v==='number'&&v>0.5;
      h += `<div class="sim-kv-item"><span class="kv-key">${k}</span><span class="kv-val" style="color:${isHigh?'var(--critical)':'var(--text)'}">${typeof v==='number'?v.toFixed(3):v}</span></div>`;
    });
    h += '</div></div>';

    // Cascading effects
    if (r.cascading_effects && Object.keys(r.cascading_effects).length) {
      h += `<div class="sim-result"><h3>🔗 Cascading Effects</h3><div class="sim-kv">`;
      Object.entries(r.cascading_effects).forEach(([k,v]) => {
        h += `<div class="sim-kv-item"><span class="kv-key">${k}</span><span class="kv-val">${typeof v==='number'?v.toFixed(3):JSON.stringify(v)}</span></div>`;
      });
      h += '</div></div>';
    }

    // Economic impact
    if (r.economic_impact && Object.keys(r.economic_impact).length) {
      h += `<div class="sim-result"><h3>💰 Projected Economic Impact</h3><div class="sim-kv">`;
      Object.entries(r.economic_impact).forEach(([k,v]) => {
        h += `<div class="sim-kv-item"><span class="kv-key">${k}</span><span class="kv-val" style="color:var(--gold2)">${typeof v==='number'?'₹'+v.toFixed(2)+' Cr':v}</span></div>`;
      });
      h += '</div></div>';
    }

    // Recommendations
    if (r.recommendations && r.recommendations.length) {
      h += `<div class="sim-result"><h3>📋 Recommended Actions</h3><ul style="list-style:none;padding:0">`;
      r.recommendations.forEach((rec,i) => {
        h += `<li style="font-size:.84rem;padding:10px 16px;color:var(--text2);border-radius:var(--r-sm);margin-bottom:4px;transition:background .2s;display:flex;align-items:flex-start;gap:10px" onmouseover="this.style.background='var(--bg-glass2)'" onmouseout="this.style.background='transparent'"><span style="color:var(--teal);font-weight:900;font-size:.9rem">${i+1}</span>${rec}</li>`;
      });
      h += '</ul></div>';
    }

    html('sim-results', h);
    toast('Simulation complete!', 'success');
  } catch(e) { html('sim-results','<div class="error-msg">Simulation failed: '+e.message+'</div>'); }
  if (window.lucide) lucide.createIcons();
}

// ═══════════════════════════════════════════════════
// AGENT LOGS — Color-coded intelligence feed
// ═══════════════════════════════════════════════════

async function loadLogs() {
  html('logs-content','<div class="loader">Loading agent intelligence feed…</div>');
  try {
    const data = await fetchJSON('/api/agent-logs?limit=50');
    let h = '';

    if (data.agent_activity) {
      h += '<div class="log-activity">';
      const colors = {'Data Agent':'#2dd4bf','Analysis Agent':'#3b82f6','Decision Agent':'#e8c95a','Memory Agent':'#a78bfa','Explanation Agent':'#f43f5e','Cascade Agent':'#22d3ee','Impact Agent':'#f97316','Intelligence Agent':'#f472b6','Telegram Agent':'#10b981','Scheduler':'#94a3b8'};
      Object.entries(data.agent_activity).forEach(([agent, count]) => {
        const col = colors[agent] || '#94a3b8';
        h += `<div class="log-act-chip" style="border-color:${col}20"><span class="la-name">${agent}</span><span class="la-count" style="color:${col}">${count}</span></div>`;
      });
      h += '</div>';
    }

    const icons = {'Data Agent':'📡','Analysis Agent':'🔬','Decision Agent':'⚖️','Memory Agent':'🧠','Explanation Agent':'💬','Cascade Agent':'🔗','Impact Agent':'💰','Intelligence Agent':'🧬','Telegram Agent':'📱','Scheduler':'⏰'};
    const agentColors = {'Data Agent':'var(--teal)','Analysis Agent':'var(--info)','Decision Agent':'var(--gold2)','Memory Agent':'var(--purple)','Explanation Agent':'var(--critical)','Cascade Agent':'var(--cyan)','Impact Agent':'var(--high)','Intelligence Agent':'#f472b6'};
    (data.logs||[]).forEach((log,i) => {
      const icon = icons[log.agent] || '🤖';
      const agentCol = agentColors[log.agent] || 'var(--text2)';
      h += `<div class="log-item" data-agent="${log.agent}" style="animation-delay:${i*30}ms">
        <div class="log-icon" style="border-color:${agentCol}30">${icon}</div>
        <div class="log-body">
          <div class="log-agent" style="color:${agentCol}">${log.agent}</div>
          <div class="log-action">${log.action}</div>
          <div class="log-details">${log.details}${log.zone_id?' · <span style="color:var(--teal)">Zone: '+log.zone_id+'</span>':''}</div>
        </div>
        <div class="log-time">${formatTime(log.timestamp)}</div>
      </div>`;
    });

    if (!data.logs || !data.logs.length) h += '<div class="empty">No agent logs yet — waiting for first ingestion cycle</div>';
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
