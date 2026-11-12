/**
 * Log Integrity & Tamper Detection Lab Component
 * Provides interactive demonstration of cryptographic log verification and tamper detection.
 */

class TamperLabComponent {
  constructor(containerId) {
    this.container = document.getElementById(containerId);
    this.selectedEvent = null;
  }

  render(events = []) {
    if (!this.container) return;

    if (!this.selectedEvent && events.length > 0) {
      this.selectedEvent = events[0];
    }

    const eventOptions = events.slice(0, 15).map(e => `
      <option value="${e.event_id}" ${this.selectedEvent && this.selectedEvent.event_id === e.event_id ? 'selected' : ''}>
        [${e.location}] ${e.event_type} - ${e.user_id} (${e.event_id.slice(0, 8)}...)
      </option>
    `).join('');

    const ev = this.selectedEvent || {};
    const isTampered = ev.integrity_status === 'TAMPERED';

    this.container.innerHTML = `
      <div class="tamper-lab-grid">
        <!-- Control Panel -->
        <div class="card">
          <div class="card-header">
            <h3 class="card-title">🔐 Cryptographic Tamper Simulator</h3>
            <span style="font-size:0.72rem;color:#94a3b8;font-family:var(--font-mono);">HMAC-SHA256</span>
          </div>

          <p style="font-size:0.8rem;color:#94a3b8;margin-bottom:1rem;line-height:1.4;">
            Every log collected by local agents is cryptographically signed using a secure HMAC-SHA256 digest. 
            Simulate an unauthorized modification below to observe the detection mechanism.
          </p>

          <div style="margin-bottom:1rem;">
            <label style="font-size:0.75rem;font-weight:600;color:#cbd5e1;display:block;margin-bottom:0.3rem;">Select Target Log Event:</label>
            <select id="tamperLogSelect" class="select-filter" style="width:100%;" onchange="app.onSelectTamperLog(this.value)">
              ${eventOptions}
            </select>
          </div>

          <div style="display:grid;grid-template-columns:1fr 1fr;gap:0.75rem;margin-bottom:1rem;">
            <div>
              <label style="font-size:0.75rem;font-weight:600;color:#cbd5e1;display:block;margin-bottom:0.3rem;">Field to Alter:</label>
              <select id="tamperField" class="select-filter" style="width:100%;">
                <option value="source_ip">source_ip (e.g. disguise attacker IP)</option>
                <option value="login_status">login_status (e.g. flip FAILURE to SUCCESS)</option>
                <option value="user_id">user_id (e.g. frame another account)</option>
                <option value="event_type">event_type (e.g. downgrade severity)</option>
                <option value="raw_log">raw_log (e.g. alter audit string)</option>
              </select>
            </div>
            <div>
              <label style="font-size:0.75rem;font-weight:600;color:#cbd5e1;display:block;margin-bottom:0.3rem;">New Malicious Value:</label>
              <input type="text" id="tamperNewValue" class="input-search" value="127.0.0.1" style="width:100%;">
            </div>
          </div>

          <div style="display:flex;gap:0.5rem;">
            <button class="btn-action btn-danger" onclick="app.executeTamperTest()" style="flex:1;">
              ⚡ Execute Unauthorized Alteration
            </button>
            <button class="btn-action btn-primary" onclick="app.verifySelectedLogIntegrity()">
              🔍 Run Cryptographic Audit
            </button>
          </div>
        </div>

        <!-- Verification Results & Payload Comparison -->
        <div class="card">
          <div class="card-header">
            <h3 class="card-title">🛡️ Integrity Verification Status</h3>
            <span class="badge-risk ${isTampered ? 'VERY_HIGH' : 'LOW'}">
              ${isTampered ? '⚠️ TAMPER WARNING' : '✅ VERIFIED'}
            </span>
          </div>

          <div id="tamperResultBox" class="tamper-diff-box">
<span style="color:#06b6d4;">=== LOG PAYLOAD INTEGRITY REPORT ===</span>
Event ID        : ${ev.event_id || 'N/A'}
Timestamp       : ${ev.timestamp || 'N/A'}
Location / Host : ${ev.location || 'N/A'} / ${ev.server_id || 'N/A'}
User Identity   : ${ev.user_id || 'N/A'}
Source IP       : ${ev.source_ip || 'N/A'}
Event Type      : ${ev.event_type || 'N/A'}
Login Status    : ${ev.login_status || 'N/A'}

<span style="color:#f59e0b;">--- CRYPTOGRAPHIC SIGNATURE CHECK ---</span>
Recorded HMAC   : ${ev.hash_signature || 'N/A'}
Integrity Status: ${ev.integrity_status || 'VERIFIED'}
${isTampered ? '<span style="color:#ef4444;font-weight:bold;">[!] WARNING: Hash mismatch! Payload was modified after collection!</span>' : '<span style="color:#10b981;">[✓] Payload cryptographically authentic. No alterations detected.</span>'}
          </div>
        </div>
      </div>
    `;
  }
}
