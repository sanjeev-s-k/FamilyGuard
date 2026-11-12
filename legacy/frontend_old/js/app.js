/**
 * IT System Log Analyzer - Main Application Controller
 * Orchestrates SOC dashboard state, REST API communications, live polling, and visualizations.
 */

class SOCApplication {
  constructor() {
    this.apiBase = '/api';
    this.state = {
      stats: {},
      events: [],
      incidents: [],
      agents: [],
      selectedIncident: null,
      selectedEvent: null,
      currentTab: 'overview',
      accounts: [],
      notifications: [],
      liveStreamActive: false,
      liveStreamTimer: null,
      pollTimer: null,
      activeFilters: {
        location: '',
        user_id: '',
        event_type: '',
        integrity_status: '',
        search: ''
      }
    };

    // Initialize UI Component Instances
    this.geoMap = new GeoMapComponent('geoMapContainer');
    this.attackGraph = new AttackGraphComponent('attackGraphCanvas');
    this.timeline = new TimelineComponent('timelineContainer');
    this.riskGauge = new RiskGaugeComponent('riskGaugeContainer');
    this.logTable = new LogTableComponent('logTableContainer');
    this.tamperLab = new TamperLabComponent('tamperLabContainer');
    this.agentPanel = new AgentPanelComponent('agentPanelContainer');
    this.mlPanel = new MLPanelComponent('mlPanelContainer');
    this.accountsPanel = new AccountsPanelComponent('accountsPanelContainer');
  }

  async init() {
    console.log('[*] Initializing CRPF SOC Threat Intelligence Dashboard...');
    this.setupEventListeners();
    await this.refreshAllData();

    // Start background live polling every 3.5 seconds
    this.state.pollTimer = setInterval(() => this.refreshAllData(true), 3500);
  }

  setupEventListeners() {
    // Tab Navigation
    document.querySelectorAll('.nav-tab').forEach(tab => {
      tab.addEventListener('click', (e) => {
        const targetTab = tab.getAttribute('data-tab');
        this.switchTab(targetTab);
      });
    });

    // Global Search & Filters
    const searchInput = document.getElementById('logSearchInput');
    if (searchInput) {
      searchInput.addEventListener('input', (e) => {
        this.state.activeFilters.search = e.target.value.toLowerCase();
        this.applyLogFilters();
      });
    }

    const locFilter = document.getElementById('logLocationFilter');
    if (locFilter) {
      locFilter.addEventListener('change', (e) => {
        this.state.activeFilters.location = e.target.value;
        this.applyLogFilters();
      });
    }

    const typeFilter = document.getElementById('logTypeFilter');
    if (typeFilter) {
      typeFilter.addEventListener('change', (e) => {
        this.state.activeFilters.event_type = e.target.value;
        this.applyLogFilters();
      });
    }

    const integFilter = document.getElementById('logIntegrityFilter');
    if (integFilter) {
      integFilter.addEventListener('change', (e) => {
        this.state.activeFilters.integrity_status = e.target.value;
        this.applyLogFilters();
      });
    }
  }

  switchTab(tabId) {
    this.state.currentTab = tabId;
    document.querySelectorAll('.nav-tab').forEach(t => {
      t.classList.toggle('active', t.getAttribute('data-tab') === tabId);
    });
    document.querySelectorAll('.tab-pane').forEach(p => {
      p.classList.toggle('active', p.id === `tab-${tabId}`);
    });

    // Refresh components for active tab
    if (tabId === 'correlation' && this.state.selectedIncident) {
      this.renderIncidentDetails(this.state.selectedIncident);
    } else if (tabId === 'tamper-lab') {
      this.tamperLab.render(this.state.events);
    } else if (tabId === 'agents') {
      this.agentPanel.render(this.state.agents);
    } else if (tabId === 'ml') {
      this.fetchMLMetrics();
    } else if (tabId === 'accounts') {
      this.accountsPanel.render(this.state.accounts, this.state.notifications);
    }
  }

  async refreshAllData(isBackground = false) {
    try {
      const [statsRes, eventsRes, incidentsRes, agentsRes, accountsRes, notifsRes] = await Promise.all([
        fetch(`${this.apiBase}/stats`).then(r => r.json()),
        fetch(`${this.apiBase}/events?limit=200`).then(r => r.json()),
        fetch(`${this.apiBase}/incidents?limit=50`).then(r => r.json()),
        fetch(`${this.apiBase}/agents`).then(r => r.json()),
        fetch(`${this.apiBase}/auth/accounts`).then(r => r.json()),
        fetch(`${this.apiBase}/notifications`).then(r => r.json())
      ]);

      this.state.stats = statsRes;
      this.state.events = eventsRes.events || [];
      this.state.incidents = incidentsRes.incidents || [];
      this.state.agents = agentsRes.agents || [];
      this.state.accounts = accountsRes.accounts || [];
      this.state.notifications = notifsRes.notifications || [];

      this.updateKPIs();
      this.geoMap.render(this.state.stats.location_counts || {});
      this.applyLogFilters();
      this.renderIncidentsList();
      this.agentPanel.render(this.state.agents);
      this.accountsPanel.render(this.state.accounts, this.state.notifications);

      // Auto-select first incident if none selected
      if (!this.state.selectedIncident && this.state.incidents.length > 0) {
        this.selectIncident(this.state.incidents[0].incident_id);
      }
    } catch (err) {
      if (!isBackground) console.error('[!] Error refreshing data:', err);
    }
  }

  updateKPIs() {
    const s = this.state.stats;
    const totalEventsEl = document.getElementById('kpiTotalEvents');
    if (totalEventsEl) totalEventsEl.innerText = (s.total_events || 0).toLocaleString();

    const totalIncidentsEl = document.getElementById('kpiTotalIncidents');
    if (totalIncidentsEl) totalIncidentsEl.innerText = s.total_incidents || 0;

    const highAlertsEl = document.getElementById('kpiHighAlerts');
    const highCount = (s.risk_distribution?.HIGH || 0) + (s.risk_distribution?.VERY_HIGH || 0);
    if (highAlertsEl) highAlertsEl.innerText = highCount;

    const tamperedEl = document.getElementById('kpiTamperedLogs');
    if (tamperedEl) tamperedEl.innerText = s.tampered_count || 0;

    const pendingSyncEl = document.getElementById('kpiPendingSync');
    const totalBuffered = (s.agents || []).reduce((acc, a) => acc + (a.buffered_logs_count || 0), 0);
    if (pendingSyncEl) pendingSyncEl.innerText = totalBuffered;

    // Badges in nav tabs
    const incidentBadge = document.getElementById('navIncidentBadge');
    if (incidentBadge) incidentBadge.innerText = s.total_incidents || 0;

    const tamperBadge = document.getElementById('navTamperBadge');
    if (tamperBadge) tamperBadge.innerText = s.tampered_count || 0;

    const notifBadge = document.getElementById('navNotifBadge');
    if (notifBadge) notifBadge.innerText = (this.state.notifications || []).filter(n => n.status === 'UNREAD').length;
  }

  applyLogFilters() {
    let filtered = [...this.state.events];
    const { location, user_id, event_type, integrity_status, search } = this.state.activeFilters;

    if (location) filtered = filtered.filter(e => e.location === location);
    if (event_type) filtered = filtered.filter(e => e.event_type === event_type);
    if (integrity_status) filtered = filtered.filter(e => e.integrity_status === integrity_status);
    if (search) {
      filtered = filtered.filter(e => 
        (e.user_id && e.user_id.toLowerCase().includes(search)) ||
        (e.server_id && e.server_id.toLowerCase().includes(search)) ||
        (e.source_ip && e.source_ip.includes(search)) ||
        (e.raw_log && e.raw_log.toLowerCase().includes(search)) ||
        (e.event_type && e.event_type.toLowerCase().includes(search))
      );
    }

    this.logTable.render(filtered);
  }

  filterLogsByLocation(location) {
    this.switchTab('logs');
    const locFilter = document.getElementById('logLocationFilter');
    if (locFilter) {
      locFilter.value = location;
      this.state.activeFilters.location = location;
      this.applyLogFilters();
    }
  }

  renderIncidentsList() {
    const listContainer = document.getElementById('incidentsListContainer');
    if (!listContainer) return;

    if (this.state.incidents.length === 0) {
      listContainer.innerHTML = `<div style="color:#64748b;padding:1.5rem;text-align:center;">No correlated incidents detected.</div>`;
      return;
    }

    const itemsHtml = this.state.incidents.map(inc => {
      const isSelected = this.state.selectedIncident && this.state.selectedIncident.incident_id === inc.incident_id;
      const risk = inc.risk_assessment || {};
      const score = risk.overall_score || 0;
      const level = risk.risk_level || 'LOW';

      return `
        <div class="incident-item ${isSelected ? 'selected' : ''}" onclick="app.selectIncident('${inc.incident_id}')">
          <div class="incident-item-header">
            <span class="incident-id">${inc.incident_id}</span>
            <span class="badge-risk ${level}">${score}/100 ${level}</span>
          </div>
          <div class="incident-title">${inc.title}</div>
          <div class="incident-meta-row">
            <span>👤 ${inc.user_id}</span>
            <span>📍 ${(inc.involved_locations || []).join(' → ')}</span>
            <span>⚡ ${inc.event_count} events</span>
          </div>
        </div>
      `;
    }).join('');

    listContainer.innerHTML = itemsHtml;
  }

  async selectIncident(incidentId) {
    try {
      const res = await fetch(`${this.apiBase}/incidents/${incidentId}`);
      if (!res.ok) return;
      const incident = await res.json();
      this.state.selectedIncident = incident;
      this.renderIncidentsList();
      this.renderIncidentDetails(incident);
    } catch (err) {
      console.error('[!] Error selecting incident:', err);
    }
  }

  renderIncidentDetails(inc) {
    if (!inc) return;

    // 1. Render Explainable Risk Score & Factor Breakdown
    this.riskGauge.render(inc.risk_assessment, inc.title);

    // 2. Render Interactive Attack Graph
    this.attackGraph.setData(inc.attack_graph);

    // 3. Render Timeline
    this.timeline.render(inc.timeline);

    // 4. Update Incident Action Bar
    const statusEl = document.getElementById('selectedIncidentStatus');
    if (statusEl) statusEl.innerText = `Status: ${inc.status} | Analyst: ${inc.assigned_analyst || 'SOC Analyst 1'}`;
  }

  async updateIncidentStatus(newStatus) {
    if (!this.state.selectedIncident) return;
    const incId = this.state.selectedIncident.incident_id;
    try {
      const res = await fetch(`${this.apiBase}/incidents/${incId}/status`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ status: newStatus, analyst: 'SOC Lead' })
      });
      const data = await res.json();
      this.showToast(`Incident ${incId} updated to ${newStatus}`, 'alert-info');
      await this.refreshAllData();
      await this.selectIncident(incId);
    } catch (err) {
      console.error(err);
    }
  }

  // --- Scenario Triggers ---
  async runScenario(scenarioName) {
    this.showToast(`Executing ${scenarioName.replace('_', ' ')}...`, 'alert-info');
    try {
      const res = await fetch(`${this.apiBase}/scenarios/run`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ scenario: scenarioName })
      });
      const data = await res.json();

      if (data.status === 'SCENARIO_EXECUTED') {
        const inc = data.incident;
        if (inc) {
          const riskLevel = inc.risk_assessment ? inc.risk_assessment.risk_level : 'INFO';
          const alertType = riskLevel === 'VERY_HIGH' || riskLevel === 'HIGH' ? 'alert-high' : 'alert-success';
          this.showToast(`⭐ Correlation Created: ${data.title} (${inc.risk_assessment?.overall_score || 0}/100)`, alertType);
          this.switchTab('correlation');
        } else {
          this.showToast(`Generated baseline log events`, 'alert-info');
        }
        await this.refreshAllData();
        if (inc) this.selectIncident(inc.incident_id);
      }
    } catch (err) {
      console.error(err);
      this.showToast(`Failed to run scenario: ${err.message}`, 'alert-high');
    }
  }

  toggleLiveStream() {
    this.state.liveStreamActive = !this.state.liveStreamActive;
    const btn = document.getElementById('btnLiveStream');
    if (btn) btn.classList.toggle('active', this.state.liveStreamActive);

    if (this.state.liveStreamActive) {
      this.showToast('🚀 Live Background Telemetry Feed Started', 'alert-info');
      this.state.liveStreamTimer = setInterval(() => {
        const locs = ["North", "South", "East", "West"];
        const srvs = { "North": "N-01", "South": "S-01", "East": "E-01", "West": "W-01" };
        const loc = locs[Math.floor(Math.random() * locs.length)];
        this.runScenarioBackground('RANDOM_NORMAL', loc, srvs[loc]);
      }, 3000);
    } else {
      if (this.state.liveStreamTimer) clearInterval(this.state.liveStreamTimer);
      this.showToast('⏹️ Live Telemetry Stream Paused', 'alert-info');
    }
  }

  async runScenarioBackground(scenarioName, location, serverId) {
    try {
      await fetch(`${this.apiBase}/scenarios/run`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ scenario: scenarioName, location, server_id: serverId })
      });
      this.refreshAllData(true);
    } catch (e) {}
  }

  async resetSystem() {
    if (!confirm('Are you sure you want to reset all telemetry and reload baseline scenarios?')) return;
    try {
      await fetch(`${this.apiBase}/system/reset`, { method: 'POST' });
      this.showToast('System successfully reset to initial baseline', 'alert-success');
      await this.refreshAllData();
      this.switchTab('overview');
    } catch (e) {
      console.error(e);
    }
  }

  // --- Local Agent Actions ---
  async toggleAgentStatus(location, newStatus) {
    try {
      const res = await fetch(`${this.apiBase}/agents/${location}/status`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ status: newStatus })
      });
      const data = await res.json();
      this.showToast(`Agent ${location} is now ${newStatus}`, newStatus === 'ONLINE' ? 'alert-success' : 'alert-high');
      await this.refreshAllData();
    } catch (e) {
      console.error(e);
    }
  }

  async generateAgentLog(location) {
    try {
      const srvMap = { "North": "N-02", "South": "S-02", "East": "E-02", "West": "W-02" };
      const res = await fetch(`${this.apiBase}/events`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          location: location,
          server_id: srvMap[location] || 'N-01',
          user_id: 'user_u102',
          raw_log: `Local tactical audit checkpoint executed on ${location} at ${new Date().toISOString()}`
        })
      });
      const data = await res.json();
      if (data.buffered) {
        this.showToast(`Agent ${location} offline: Log stored in local buffer (Depth: ${data.agent.buffered_logs_count})`, 'alert-high');
      } else {
        this.showToast(`Agent ${location} online: Log ingested to Central Intelligence`, 'alert-success');
      }
      await this.refreshAllData();
    } catch (e) {
      console.error(e);
    }
  }

  async syncAgentBuffer(location) {
    try {
      const res = await fetch(`${this.apiBase}/agents/${location}/sync`, { method: 'POST' });
      const data = await res.json();
      this.showToast(data.message, 'alert-success');
      // Automatically trigger correlation on recent logs
      await fetch(`${this.apiBase}/correlate`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ scenario_tag: 'OFFLINE_SYNC_RECOVERY' })
      });
      await this.refreshAllData();
    } catch (e) {
      console.error(e);
    }
  }

  // --- Tamper Lab Actions ---
  onSelectTamperLog(eventId) {
    const ev = this.state.events.find(e => e.event_id === eventId);
    if (ev) {
      this.tamperLab.selectedEvent = ev;
      this.tamperLab.render(this.state.events);
    }
  }

  async executeTamperTest() {
    const selectEl = document.getElementById('tamperLogSelect');
    const fieldEl = document.getElementById('tamperField');
    const valEl = document.getElementById('tamperNewValue');
    if (!selectEl || !fieldEl || !valEl) return;

    const eventId = selectEl.value;
    const field = fieldEl.value;
    const value = valEl.value;

    try {
      const res = await fetch(`${this.apiBase}/events/${eventId}/tamper`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ field: field, value: value })
      });
      const data = await res.json();

      const resultBox = document.getElementById('tamperResultBox');
      if (resultBox) {
        resultBox.innerHTML = `
<span style="color:#ef4444;font-weight:bold;">=== ⚠️ CRYPTOGRAPHIC TAMPER DISCREPANCY DETECTED ===</span>
Event ID            : ${data.event_id}
Altered Field       : <span style="color:#f59e0b;font-weight:bold;">${data.field_altered}</span> → <span style="color:#ef4444;font-weight:bold;">"${data.new_value}"</span>
Original HMAC Sig   : ${data.original_hash}
Recalculated Digest : ${data.recalculated_hash}
Integrity Match     : <span style="color:#ef4444;font-weight:bold;">FALSE (DISCREPANCY DETECTED)</span>

<span style="color:#f87171;">${data.explanation}</span>
        `;
      }
      this.showToast('🚨 Tampering Alert: Cryptographic HMAC signature failed!', 'alert-high');
      await this.refreshAllData();
    } catch (e) {
      console.error(e);
    }
  }

  async verifySelectedLogIntegrity() {
    const selectEl = document.getElementById('tamperLogSelect');
    if (!selectEl) return;
    const eventId = selectEl.value;

    try {
      const res = await fetch(`${this.apiBase}/events/${eventId}/verify`, { method: 'POST' });
      const data = await res.json();
      const resultBox = document.getElementById('tamperResultBox');
      if (resultBox) {
        resultBox.innerHTML = `
<span style="color:#06b6d4;">=== CRYPTOGRAPHIC AUDIT VERIFICATION ===</span>
Event ID        : ${data.event_id}
Recorded Hash   : ${data.recorded_hash}
Calculated Hash : ${data.calculated_hash}
Status          : ${data.is_valid ? '<span style="color:#10b981;font-weight:bold;">VALID (AUTHENTIC)</span>' : '<span style="color:#ef4444;font-weight:bold;">INVALID (TAMPERED)</span>'}

${data.explanation}
        `;
      }
      this.showToast(data.explanation, data.is_valid ? 'alert-success' : 'alert-high');
    } catch (e) {
      console.error(e);
    }
  }

  // --- ML Actions ---
  async fetchMLMetrics() {
    try {
      const res = await fetch(`${this.apiBase}/ml/metrics`);
      const metrics = await res.json();
      this.mlPanel.render(metrics);
    } catch (e) {
      console.error(e);
    }
  }

  async retrainMLModel() {
    this.showToast('Retraining Supervised Threat Classifier...', 'alert-info');
    try {
      const res = await fetch(`${this.apiBase}/ml/retrain`, { method: 'POST' });
      const data = await res.json();
      this.showToast(`Model retrained successfully! Accuracy: ${(data.metrics.accuracy * 100).toFixed(1)}%`, 'alert-success');
      this.mlPanel.render(data.metrics);
    } catch (e) {
      console.error(e);
    }
  }

  async runMLPlaygroundInference() {
    const failedCount = parseInt(document.getElementById('mlPlaygroundFailures')?.value || '0', 10);
    const crossLoc = parseInt(document.getElementById('mlPlaygroundCrossLoc')?.value || '1', 10);
    const unusualLoc = parseInt(document.getElementById('mlPlaygroundUnusualLoc')?.value || '0', 10);
    const unknownDev = parseInt(document.getElementById('mlPlaygroundUnknownDev')?.value || '0', 10);
    const highSev = parseInt(document.getElementById('mlPlaygroundHighSev')?.value || '0', 10);

    const payload = {
      failed_attempt_count: failedCount,
      unusual_location: !!unusualLoc,
      unknown_device: !!unknownDev,
      event_type: highSev ? 'DATA_EXFILTRATION' : 'SUCCESSFUL_LOGIN',
      context: {
        cross_location_count: crossLoc,
        is_unusual_location: !!unusualLoc,
        is_unknown_device: !!unknownDev
      }
    };

    try {
      const res = await fetch(`${this.apiBase}/ml/predict`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
      });
      const data = await res.json();

      const resultBox = document.getElementById('mlPlaygroundResult');
      if (resultBox) {
        resultBox.style.display = 'block';
        const predColor = data.predicted_class === 'VERY_HIGH' ? '#ef4444' : data.predicted_class === 'HIGH' ? '#f97316' : data.predicted_class === 'MEDIUM' ? '#f59e0b' : '#10b981';
        
        resultBox.innerHTML = `
<span style="color:#06b6d4;">=== SUPERVISED ML PREDICTION RESULT ===</span>
Predicted Risk Class : <span style="color:${predColor};font-weight:bold;font-size:0.95rem;">${data.predicted_class}</span>
Confidence Level     : <strong>${(data.confidence * 100).toFixed(1)}%</strong>

<span style="color:#a855f7;">--- CLASS PROBABILITIES ---</span>
${Object.entries(data.probabilities || {}).map(([c, p]) => `${c.padEnd(10)}: ${(p * 100).toFixed(1)}%`).join('\n')}

<span style="color:#38bdf8;">--- FEATURE CONTRIBUTIONS ---</span>
${Object.entries(data.feature_contributions || {}).map(([f, w]) => `• ${f.padEnd(25)}: +${w.toFixed(1)}%`).join('\n')}
        `;
      }
    } catch (e) {
      console.error(e);
    }
  }

  // --- SOC Expert Precautionary Actions ---
  async takePrecautionaryBlock(forceId, notifId, notifTitle) {
    const reason = prompt(`Enforce Precautionary Account Block on ${forceId}:\nEnter Lockout Reason:`, `Anomalous cross-location risk detected (${notifTitle})`);
    if (!reason) return;

    try {
      // 1. Block account
      await fetch(`${this.apiBase}/auth/accounts/${forceId}/status`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ status: 'TEMPORARILY_BLOCKED', reason: reason, expert_name: 'SOC Defense Lead' })
      });

      // 2. Mark notification actioned
      if (notifId) {
        await fetch(`${this.apiBase}/notifications/${notifId}/action`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ action: 'BLOCK_ACCOUNT', force_id: forceId, reason: reason })
        });
      }

      this.showToast(`🛑 Account ${forceId} is now TEMPORARILY BLOCKED. Logins will be denied at SSO.`, 'alert-high');
      await this.refreshAllData();
    } catch (e) {
      console.error(e);
    }
  }

  async blockAccountPrompt(forceId, fullName) {
    const reason = prompt(`Enforce Temporary Administrative Lockout on ${fullName} (${forceId}):\nEnter Lockout Reason:`, "Security Precaution: Suspicious unauthorized activity reported.");
    if (!reason) return;

    try {
      await fetch(`${this.apiBase}/auth/accounts/${forceId}/status`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ status: 'TEMPORARILY_BLOCKED', reason: reason, expert_name: 'SOC Defense Lead' })
      });
      this.showToast(`🛑 Account ${forceId} TEMPORARILY BLOCKED.`, 'alert-high');
      await this.refreshAllData();
    } catch (e) {
      console.error(e);
    }
  }

  async unblockAccount(forceId) {
    if (!confirm(`Restore and re-activate account ${forceId}?`)) return;
    try {
      await fetch(`${this.apiBase}/auth/accounts/${forceId}/status`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ status: 'ACTIVE', expert_name: 'SOC Defense Lead' })
      });
      this.showToast(`✅ Account ${forceId} restored to ACTIVE status.`, 'alert-success');
      await this.refreshAllData();
    } catch (e) {
      console.error(e);
    }
  }

  async dismissNotification(notifId) {
    try {
      await fetch(`${this.apiBase}/notifications/${notifId}/action`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ action: 'DISMISS' })
      });
      this.showToast('Notification dismissed', 'alert-info');
      await this.refreshAllData();
    } catch (e) {
      console.error(e);
    }
  }

  filterLogsByUser(userId) {
    this.switchTab('logs');
    const searchInput = document.getElementById('logSearchInput');
    if (searchInput) {
      searchInput.value = userId;
      this.state.activeFilters.search = userId.toLowerCase();
      this.applyLogFilters();
    }
  }

  // --- Modals & Inspecting ---
  showEventModal(eventId) {
    const ev = this.state.events.find(e => e.event_id === eventId);
    if (!ev) return;

    const modal = document.getElementById('eventDetailModal');
    const content = document.getElementById('eventModalBody');
    if (!modal || !content) return;

    content.innerHTML = `
      <div style="font-family:var(--font-mono);font-size:0.8rem;background:#090d16;padding:1rem;border-radius:8px;border:1px solid rgba(255,255,255,0.08);margin-bottom:1rem;">
        <span style="color:#38bdf8;">// RAW LOG RECORD</span>\n
        ${ev.raw_log || 'N/A'}\n\n
        <span style="color:#10b981;">// NORMALIZED CANONICAL JSON</span>\n
        ${JSON.stringify(ev, null, 2)}
      </div>
      <div style="display:flex;gap:0.5rem;justify-content:flex-end;">
        <button class="btn-action btn-danger" onclick="app.tamperFromModal('${ev.event_id}')">
          ⚡ Send to Tamper Lab
        </button>
        <button class="btn-action btn-primary" onclick="app.closeModal()">
          Close
        </button>
      </div>
    `;
    modal.classList.add('open');
  }

  tamperFromModal(eventId) {
    this.closeModal();
    this.switchTab('tamper-lab');
    this.onSelectTamperLog(eventId);
  }

  showNodeDetails(node) {
    this.showToast(`Inspecting Entity: ${node.label} (${node.type})`, 'alert-info');
  }

  closeModal() {
    document.querySelectorAll('.modal-overlay').forEach(m => m.classList.remove('open'));
  }

  showToast(message, type = 'alert-info') {
    const container = document.getElementById('toastContainer');
    if (!container) return;

    const toast = document.createElement('div');
    toast.className = `toast ${type}`;
    toast.innerHTML = `<span>🛡️</span> <span>${message}</span>`;
    container.appendChild(toast);

    setTimeout(() => {
      toast.style.opacity = '0';
      toast.style.transform = 'translateX(50px)';
      setTimeout(() => toast.remove(), 300);
    }, 4000);
  }
}

// Global bootstrap
document.addEventListener('DOMContentLoaded', () => {
  window.app = new SOCApplication();
  window.app.init();
});
