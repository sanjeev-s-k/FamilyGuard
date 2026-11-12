/**
 * Local Agent & Offline Sync Panel Component
 * Demonstrates local agent connectivity states, offline buffering, and central synchronization.
 */

class AgentPanelComponent {
  constructor(containerId) {
    this.container = document.getElementById(containerId);
  }

  render(agents = []) {
    if (!this.container) return;

    if (!agents || agents.length === 0) {
      this.container.innerHTML = `<div style="color:#64748b;padding:2rem;">No local agents registered.</div>`;
      return;
    }

    const cardsHtml = agents.map(ag => {
      const isOnline = ag.status === 'ONLINE';
      const bufferCount = ag.buffered_logs_count || 0;
      const statusColor = isOnline ? '#10b981' : '#ef4444';

      return `
        <div class="agent-card ${!isOnline ? 'offline' : ''}">
          <div class="agent-header">
            <div>
              <div class="agent-title">📍 ${ag.location} Local Agent</div>
              <span style="font-size:0.7rem;color:#94a3b8;font-family:var(--font-mono);">${ag.agent_id} (${ag.ip_address})</span>
            </div>
            <span class="badge-risk ${isOnline ? 'LOW' : 'VERY_HIGH'}" style="font-size:0.68rem;">
              ${ag.status}
            </span>
          </div>

          <div style="font-size:0.75rem;color:#cbd5e1;margin-bottom:0.6rem;">
            <strong>Monitored Servers:</strong>
            <ul style="padding-left:1.1rem;margin-top:0.2rem;color:#94a3b8;">
              ${(ag.server_ids || []).map(s => `<li>${s}</li>`).join('')}
            </ul>
          </div>

          <div class="buffer-gauge">
            <span>Offline Local Queue:</span>
            <strong style="color:${bufferCount > 0 ? '#f59e0b' : '#38bdf8'};">${bufferCount} logs buffered</strong>
          </div>

          <div style="display:flex;gap:0.4rem;flex-wrap:wrap;margin-top:0.85rem;">
            <button class="btn-action ${isOnline ? 'btn-danger' : 'btn-success'}" style="flex:1;"
                    onclick="app.toggleAgentStatus('${ag.location}', '${isOnline ? 'OFFLINE' : 'ONLINE'}')">
              ${isOnline ? '⚡ Simulate Network Cut' : '🔌 Restore Connectivity'}
            </button>
            <button class="btn-action btn-primary" onclick="app.generateAgentLog('${ag.location}')" title="Generate a local event on this agent">
              📝 Generate Local Log
            </button>
            ${bufferCount > 0 ? `
              <button class="btn-action btn-success" style="width:100%;margin-top:0.2rem;" onclick="app.syncAgentBuffer('${ag.location}')">
                🔄 Synchronize Buffered Logs (${bufferCount})
              </button>
            ` : ''}
          </div>
        </div>
      `;
    }).join('');

    this.container.innerHTML = `
      <div style="margin-bottom:1.25rem;">
        <p style="font-size:0.82rem;color:#94a3b8;line-height:1.45;">
          Each organizational outpost operates a lightweight <strong>Local Agent</strong> that collects, normalizes, and signs logs.
          When a remote location experiences connectivity loss, the agent automatically buffers events locally until connectivity is restored.
        </p>
      </div>
      <div class="agents-grid">
        ${cardsHtml}
      </div>
    `;
  }
}
