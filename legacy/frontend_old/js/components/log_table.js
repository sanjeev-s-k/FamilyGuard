/**
 * Log Table Explorer Component
 * Renders filterable, searchable stream of normalized log telemetry.
 */

class LogTableComponent {
  constructor(containerId) {
    this.container = document.getElementById(containerId);
    this.events = [];
  }

  render(events = []) {
    this.events = events;
    if (!this.container) return;

    if (!events || events.length === 0) {
      this.container.innerHTML = `
        <div style="text-align:center;padding:3rem;color:#64748b;font-size:0.85rem;">
          No log events matching current filters.
        </div>
      `;
      return;
    }

    const rowsHtml = events.map(e => {
      const isTampered = e.integrity_status === 'TAMPERED';
      const integrityBadge = isTampered 
        ? `<span style="color:#ef4444;background:rgba(239,68,68,0.15);padding:2px 6px;border-radius:4px;font-weight:700;font-size:0.68rem;">⚠️ TAMPERED</span>`
        : `<span style="color:#10b981;background:rgba(16,185,129,0.15);padding:2px 6px;border-radius:4px;font-weight:600;font-size:0.68rem;">✅ VERIFIED</span>`;

      const typeBadgeColor = e.event_type.includes('FAIL') ? '#f59e0b' : e.event_type.includes('EXFIL') || e.event_type.includes('PRIV') ? '#ef4444' : '#38bdf8';
      const formattedTime = e.timestamp ? new Date(e.timestamp).toLocaleTimeString() : 'N/A';

      return `
        <tr onclick="app.showEventModal('${e.event_id}')">
          <td style="font-family:var(--font-mono);font-size:0.72rem;color:#94a3b8;">${formattedTime}</td>
          <td><span class="tag-pill loc">📍 ${e.location}</span></td>
          <td><span class="tag-pill srv">${e.server_id}</span></td>
          <td style="font-family:var(--font-mono);font-weight:600;color:#f1f5f9;">${e.user_id}</td>
          <td style="font-family:var(--font-mono);font-size:0.72rem;color:#94a3b8;">${e.device_id}</td>
          <td style="font-family:var(--font-mono);font-size:0.72rem;color:#94a3b8;">${e.source_ip}</td>
          <td><span class="code-badge" style="color:${typeBadgeColor};">${e.event_type}</span></td>
          <td>${integrityBadge}</td>
          <td style="max-width:260px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;color:#94a3b8;font-size:0.72rem;font-family:var(--font-mono);">${e.raw_log || '-'}</td>
        </tr>
      `;
    }).join('');

    this.container.innerHTML = `
      <div class="log-table-wrapper">
        <table class="log-table">
          <thead>
            <tr>
              <th>Timestamp</th>
              <th>Location</th>
              <th>Server</th>
              <th>User Identity</th>
              <th>Device ID</th>
              <th>Source IP</th>
              <th>Event Type</th>
              <th>Log Integrity</th>
              <th>Raw Payload Preview</th>
            </tr>
          </thead>
          <tbody>
            ${rowsHtml}
          </tbody>
        </table>
      </div>
    `;
  }
}
