src="https://www.gstatic.com/firebasejs/10.7.1/firebase-app-compat.js"
src="https://www.gstatic.com/firebasejs/10.7.1/firebase-database-compat.js"
document.addEventListener('DOMContentLoaded', () => {
  const firebaseConfig = {
    apiKey: "AIzaSyDM_St_gvOpRPpUbUTot0aVJwhpkqGT1bM",
    authDomain: "senior-project-a0b32.firebaseapp.com",
    databaseURL: "https://senior-project-a0b32-default-rtdb.firebaseio.com",
    projectId: "senior-project-a0b32",
    storageBucket: "senior-project-a0b32.firebasestorage.app",
    messagingSenderId: "237286209534",
    appId: "1:237286209534:web:9cb12721a31406382bf2af",
    measurementId: "G-T2DTQ8SF6H"
  };

  // ── Local Python backend URL ───────────────────────────────────────────
  // Make sure backend_server.py is running before clicking Analyze Now
  const BACKEND_URL = 'http://localhost:5000';

  // Initialize Firebase
  const app = firebase.initializeApp(firebaseConfig);
  const database = firebase.database();
  const dataRef2 = database.ref('sensor_data').limitToLast(100);

  // Holds the latest sensor reading for AI analysis
  let latestSensorData = null;

  // ── Charts ─────────────────────────────────────────────────────────────

  let charts = { wind: null, efficiency: null, sunlight: null, energy: null };

  function initializeCharts() {
    charts.wind     = createChart('windSpeedChart', 'line', 'Wind Speed (m/s)', '#9b59b6');
    charts.water    = createChart('efficiencyChart', 'bar',  'Water Consumption (L)', '#3498db');
    charts.sunlight = createChart('sunlightChart',   'line', 'Angle(°)', '#f39c12');
    charts.energy   = createChart('energyChart',     'line', 'percentage (%)', '#2D9CDB');
  }

  function createChart(elementId, type, label, color) {
    const ctx = document.getElementById(elementId).getContext('2d');
    return new Chart(ctx, {
      type: type,
      data: { labels: [], datasets: [{ label, data: [], borderColor: color, backgroundColor: `${color}33`, fill: type === 'line', tension: 0.2 }] },
      options: { responsive: true, maintainAspectRatio: false, scales: { y: { beginAtZero: true } } }
    });
  }

  function updateCharts(data) {
    const labels = data.map(e => new Date(e.timestamp).toLocaleTimeString());
    updateChart(charts.wind,     labels, data, 'wind_speed');
    updateChart(charts.water,    labels, data, 'water_used_l');
    updateChart(charts.sunlight, labels, data, 'servo_h');
    updateChart(charts.energy,   labels, data, 'battery_pct');
  }

  function updateChart(chart, labels, data, field) {
    try {
      chart.data.labels = labels;
      chart.data.datasets[0].data = data.map(e => typeof e[field] === 'number' ? e[field] : 0);
      chart.update();
    } catch (err) { console.error('Chart update error:', err); }
  }

  // ── Metrics ────────────────────────────────────────────────────────────

  function updateMetrics(data) {
    if (data.length > 0) {
      const latest = data[data.length - 1];
      latestSensorData = latest;
      document.getElementById('PowerOutput').textContent = `${Math.round(latest.battery_pct)?.toFixed(0) || 0}%`;
      document.getElementById('windSpeed').textContent   = `${latest.wind_speed?.toFixed(2) || 0} m/s`;
      document.getElementById('tiltAngle').textContent   = `V: ${Math.round(latest.servo_v)}° | H: ${Math.round(latest.servo_h)}°`;
    }
  }

  // ── Logs ───────────────────────────────────────────────────────────────

  function updateLogTable(data) {
    const tbody = document.querySelector('#logsTable tbody');
    const aiRows = Array.from(tbody.querySelectorAll('tr[data-source="ai"]'));
    tbody.innerHTML = '';
    aiRows.forEach(r => tbody.appendChild(r));
    data.slice(-10).reverse().forEach(entry => {
      const row = document.createElement('tr');
      row.innerHTML = `
        <td>${new Date(entry.timestamp).toLocaleString()}</td>
        <td>Battery: ${Math.round(entry.battery_pct)}% | Wind: ${Math.round(entry.wind_speed)}m/s | Tilt V: ${Math.round(entry.servo_v)?.toFixed(1)||0}° | H: ${Math.round(entry.servo_h)?.toFixed(1)||0}° | Water: ${Math.round(entry.water_used_l)}L</td>
      `;
      tbody.appendChild(row);
    });
  }

  // ── Firebase real-time listener ────────────────────────────────────────

  dataRef2.on('value', snapshot => {
    const data = [];
    snapshot.forEach(child => { const v = child.val(); if (v.timestamp) data.push(v); });
    const sorted = data.sort((a, b) => parseInt(a.timestamp) - parseInt(b.timestamp));
    updateCharts(sorted);
    updateMetrics(sorted);
    updateLogTable(sorted);
  });

  // ── Control buttons ────────────────────────────────────────────────────

  document.getElementById('startCleaningBtn').addEventListener('click', () => {
    const ref = database.ref('sensor_data');
    const newData = {
      timestamp: firebase.database.ServerValue.TIMESTAMP,
      battery_pct: Math.random() * 100,
      battery_voltage: 3.5 + Math.random() * 0.5,
      servo_h: Math.random() * 180,
      servo_v: Math.random() * 180,
      water_used_l: Math.random() * 2,
      wind_speed: Math.random() * 5,
      light_sensor: 500 + Math.random() * 500
    };
    ref.push(newData).then(() => console.log('Data pushed:', newData)).catch(err => console.error(err));
  });

  document.getElementById('resetSystemBtn').addEventListener('click', () => {
    database.ref('sensor_data').remove();
  });

  // ── AI DECISION ENGINE — calls local DeepSeek-R1 via Python backend ────

  function setAiStatus(state, text) {
    document.getElementById('aiStatusDot').className = 'ai-status-dot ' + state;
    document.getElementById('aiStatusText').textContent = text;
  }

  function showAiLoading(show) {
    document.getElementById('aiLoading').style.display      = show ? 'flex' : 'none';
    document.getElementById('aiBreakdown').style.display    = show ? 'none' : '';
    document.getElementById('aiActionBanner').style.display = show ? 'none' : '';
  }

  function renderAiResult(result) {
    document.getElementById('aiActionBanner').style.display = 'flex';
    const icons = { SUN_TRACKING: '☀️', CLEANING_WIND: '💨', CLEANING_WATER: '💧', IDLE: '⏸️' };
    document.getElementById('aiActionIcon').textContent = icons[result.action] || '⚙️';
    document.getElementById('aiActionName').textContent = result.action_label || result.action;

    const urgencyEl = document.getElementById('aiUrgencyBadge');
    urgencyEl.textContent = result.urgency || 'Normal';
    urgencyEl.className   = 'ai-urgency-badge urgency-' + (result.urgency || 'low').toLowerCase();

    document.getElementById('aiBreakdown').style.display    = '';
    document.getElementById('aiConditionsText').textContent = result.conditions_assessment || '—';
    document.getElementById('aiReasoningText').textContent  = result.reasoning || '—';

    let riskText = result.risks_and_notes || '—';
    if (result.confidence !== undefined) {
      riskText += `\n\nConfidence: ${(result.confidence * 100).toFixed(0)}% | Inference: ${result.inference_time_seconds}s | Model: ${result.model_used}`;
    }
    document.getElementById('aiRisksText').textContent = riskText;

    const stepsList = document.getElementById('aiStepsList');
    stepsList.innerHTML = '';
    (result.action_steps || []).forEach(step => {
      const li = document.createElement('li');
      li.textContent = step;
      stepsList.appendChild(li);
    });

    // Log to system logs
    const tbody = document.querySelector('#logsTable tbody');
    const row = document.createElement('tr');
    row.setAttribute('data-source', 'ai');
    row.style.background = '#eaf6ff';
    row.innerHTML = `
      <td>${new Date().toLocaleString()}</td>
      <td>🤖 AI (DeepSeek-R1): <strong>${result.action_label}</strong> — Urgency: ${result.urgency}</td>
    `;
    tbody.insertBefore(row, tbody.firstChild);
  }

  async function runAiAnalysis() {
    const btn = document.getElementById('aiAnalyzeBtn');
    btn.disabled = true;
    setAiStatus('loading', 'Connecting to local DeepSeek-R1 model...');
    showAiLoading(true);

    try {
      const response = await fetch(`${BACKEND_URL}/api/decide/auto`);

      if (!response.ok) throw new Error(`Backend returned ${response.status}. Is backend_server.py running?`);

      const result = await response.json();
      if (!result.success) throw new Error(result.error || 'LLM returned an error');

      showAiLoading(false);
      renderAiResult(result.decision);
      setAiStatus('ready', `Analysis complete — ${new Date().toLocaleTimeString()}`);

    } catch (err) {
      showAiLoading(false);
      let msg = err.message;
      if (msg.includes('Failed to fetch') || msg.includes('NetworkError')) {
        msg = '⚠️ Cannot reach backend. Open a terminal and run: python llm-backend/backend_server.py';
      }
      setAiStatus('error', msg);
      console.error('AI error:', err);
    } finally {
      btn.disabled = false;
    }
  }

  document.getElementById('aiAnalyzeBtn').addEventListener('click', runAiAnalysis);

  // ── END AI DECISION ENGINE ─────────────────────────────────────────────

  initializeCharts();
});
