/**
 * CRPF Personnel Accounts & SOC Precautionary Controls Component
 * Allows SOC Security Experts to monitor accounts, view risk notifications, and enforce temporary blocks.
 */

class AccountsPanelComponent {
  constructor(containerId) {
    this.container = document.getElementById(containerId);
    this.accounts = [];
    this.notifications = [];
  }

  render(accounts = [], notifications = []) {
    this.accounts = accounts;
    this.notifications = notifications;
    if (!this.container) return;

    // Notifications Feed HTML
    let notifsHtml = '';
    if (notifications.length > 0) {
      notifsHtml = notifications.map(n => {
        const isCrit = n.severity === 'CRITICAL';
        const isActioned = n.status === 'ACTIONED';
        const formattedTime = n.timestamp ? new Date(n.timestamp).toLocaleTimeString() : 'N/A';

        return `
          <div style="background:rgba(16,22,36,0.9);border:1px solid ${isCrit ? 'rgba(239,68,68,0.5)' : 'rgba(245,158,11,0.4)'};border-radius:8px;padding:0.85rem;margin-bottom:0.6rem;">
            <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:0.3rem;">
              <span style="font-weight:700;font-size:0.82rem;color:${isCrit ? '#f87171' : '#fbbf24'};">${n.title}</span>
              <span style="font-family:var(--font-mono);font-size:0.7rem;color:#94a3b8;">${formattedTime}</span>
            </div>
            <p style="font-size:0.76rem;color:#cbd5e1;white-space:pre-line;margin-bottom:0.5rem;font-family:var(--font-mono);line-height:1.4;">${n.message}</p>
            
            <div style="display:flex;gap:0.4rem;align-items:center;justify-content:flex-end;">
              ${isActioned ? `
                <span style="font-size:0.7rem;color:#34d399;background:rgba(16,185,129,0.15);padding:2px 6px;border-radius:4px;">
                  ✓ Action Taken: ${n.action_taken}
                </span>
              ` : `
                <button class="btn-action btn-danger" style="font-size:0.7rem;padding:0.25rem 0.55rem;"
                        onclick="app.takePrecautionaryBlock('${n.force_id}', '${n.notification_id}', '${n.title}')">
                  🛑 Precaution: Temporarily Block ${n.force_id}
                </button>
                <button class="btn-action btn-scenario btn-reset" style="font-size:0.7rem;padding:0.25rem 0.55rem;"
                        onclick="app.dismissNotification('${n.notification_id}')">
                  Dismiss
                </button>
              `}
            </div>
          </div>
        `;
      }).join('');
    } else {
      notifsHtml = `<div style="color:#64748b;font-size:0.8rem;padding:1rem;text-align:center;">No active security expert notifications. All accounts operating within normal baseline.</div>`;
    }

    // Accounts Cards HTML
    const accountsHtml = accounts.map(acc => {
      const isBlocked = acc.status === 'TEMPORARILY_BLOCKED';
      const statusBadge = isBlocked 
        ? `<span class="badge-risk VERY_HIGH" style="font-size:0.68rem;">🛑 TEMPORARILY BLOCKED</span>`
        : `<span class="badge-risk LOW" style="font-size:0.68rem;">✅ ACTIVE</span>`;

      return `
        <div class="card" style="border-color:${isBlocked ? 'rgba(239,68,68,0.5)' : 'var(--border-color)'};background:${isBlocked ? 'rgba(239,68,68,0.04)' : 'var(--bg-card)'};">
          <div class="card-header">
            <div>
              <div style="font-size:0.95rem;font-weight:700;color:#fff;">${acc.full_name}</div>
              <div style="font-size:0.72rem;color:#38bdf8;font-family:var(--font-mono);">${acc.rank} • ID: ${acc.force_id}</div>
            </div>
            ${statusBadge}
          </div>

          <div style="font-size:0.76rem;color:#cbd5e1;margin-bottom:0.75rem;">
            <div><strong>Home Base:</strong> <span class="tag-pill loc">📍 ${acc.home_location} Sector</span></div>
            <div style="margin-top:0.25rem;"><strong>Trusted Hardware:</strong> <span style="font-family:var(--font-mono);font-size:0.7rem;color:#94a3b8;">${(acc.trusted_devices || []).join(', ')}</span></div>
            <div style="margin-top:0.25rem;"><strong>Last Telemetry:</strong> <span style="font-family:var(--font-mono);font-size:0.7rem;color:#94a3b8;">${acc.last_login_location ? `${acc.last_login_location} (${acc.last_login_device})` : 'No recent login'}</span></div>
            ${isBlocked ? `
              <div style="margin-top:0.4rem;padding:0.4rem;background:rgba(239,68,68,0.15);border-radius:4px;border-left:3px solid #ef4444;color:#fca5a5;font-size:0.72rem;">
                <strong>Lockout Reason:</strong> ${acc.block_reason || 'Administrative Security Lock'}
              </div>
            ` : ''}
          </div>

          <div style="display:flex;gap:0.4rem;margin-top:auto;">
            ${isBlocked ? `
              <button class="btn-action btn-success" style="flex:1;font-size:0.74rem;" onclick="app.unblockAccount('${acc.force_id}')">
                🔓 Unblock / Restore Account
              </button>
            ` : `
              <button class="btn-action btn-danger" style="flex:1;font-size:0.74rem;" onclick="app.blockAccountPrompt('${acc.force_id}', '${acc.full_name}')">
                🛑 Precaution: Temporarily Block
              </button>
            `}
            <button class="btn-action btn-primary" style="font-size:0.74rem;" onclick="app.filterLogsByUser('${acc.user_id}')" title="Filter log stream for this user">
              📋 Audit Logs
            </button>
          </div>
        </div>
      `;
    }).join('');

    this.container.innerHTML = `
      <!-- Top Section: Expert Notifications Center -->
      <div class="card" style="margin-bottom:1.5rem;">
        <div class="card-header">
          <h3 class="card-title">🚨 Real-Time Security Expert Notifications Center</h3>
          <span style="font-size:0.72rem;color:#f59e0b;font-family:var(--font-mono);">${notifications.length} Alerts Dispatched</span>
        </div>
        <p style="font-size:0.78rem;color:#94a3b8;margin-bottom:0.75rem;">
          Real-time incident dispatches generated by the correlation and risk engine. Security experts can take immediate action to isolate or temporarily block compromised credentials.
        </p>
        <div>
          ${notifsHtml}
        </div>
      </div>

      <!-- Bottom Section: CRPF Accounts Grid -->
      <div class="card-header" style="margin-bottom:1rem;">
        <h3 class="card-title">👥 Monitored CRPF Personnel Identity Roster & Status</h3>
        <a href="/login.html" target="_blank" class="btn-scenario btn-live-stream" style="text-decoration:none;">
          🔐 Open CRPF Login Portal ↗
        </a>
      </div>
      <div style="display:grid;grid-template-columns:repeat(auto-fit, minmax(320px, 1fr));gap:1.25rem;">
        ${accountsHtml}
      </div>
    `;
  }
}
