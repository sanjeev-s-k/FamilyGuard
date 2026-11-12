/**
 * Geo Map Component
 * Renders the multi-location geographical threat map with live node pulses and server telemetry.
 */

class GeoMapComponent {
  constructor(containerId) {
    this.container = document.getElementById(containerId);
    this.regions = {
      North: { name: "North Sector (HQ / Delhi-Srinagar)", x: 50, y: 22, servers: ["N-01 (DC)", "N-02 (DB)", "N-03 (Web)"], count: 0 },
      South: { name: "South Sector (Hyderabad / BLR)", x: 48, y: 78, servers: ["S-01 (Gateway)", "S-02 (Ops)"], count: 0 },
      East: { name: "East Sector (Guwahati / Kolkata)", x: 80, y: 44, servers: ["E-01 (Comms)", "E-02 (Archives)"], count: 0 },
      West: { name: "West Command (Mumbai / Jodhpur)", x: 22, y: 46, servers: ["W-01 (Relay)", "W-02 (Logistics)"], count: 0 }
    };
  }

  render(locationCounts = {}) {
    if (!this.container) return;

    let nodesHtml = '';
    for (const [key, reg] of Object.entries(this.regions)) {
      const count = locationCounts[key] || 0;
      const isHighRisk = key === "North" || key === "East" || key === "South";
      const badgeClass = count > 10 ? "VERY_HIGH" : count > 5 ? "HIGH" : count > 0 ? "MEDIUM" : "LOW";

      nodesHtml += `
        <div class="region-node pos-${key.toLowerCase()}" onclick="app.filterLogsByLocation('${key}')">
          <div class="region-node-title">
            <span style="display:inline-block;width:10px;height:10px;border-radius:50%;background:${count > 0 ? '#38bdf8' : '#64748b'};box-shadow:0 0 8px #38bdf8;"></span>
            ${reg.name}
          </div>
          <div class="region-node-stats">
            <span>Logs: <strong>${count}</strong></span> • 
            <span style="color:#94a3b8;">${reg.servers.length} Active Servers</span>
          </div>
          <div style="margin-top:4px;display:flex;gap:4px;flex-wrap:wrap;">
            ${reg.servers.map(s => `<span style="font-size:0.62rem;background:rgba(255,255,255,0.06);padding:1px 4px;border-radius:3px;color:#cbd5e1;">${s.split(' ')[0]}</span>`).join('')}
          </div>
        </div>
      `;
    }

    this.container.innerHTML = `
      <div class="map-canvas-wrapper">
        <!-- SVG Grid & Connection Lines -->
        <svg style="position:absolute;top:0;left:0;width:100%;height:100%;pointer-events:none;">
          <defs>
            <linearGradient id="lineGrad" x1="0%" y1="0%" x2="100%" y2="100%">
              <stop offset="0%" stop-color="#06b6d4" stop-opacity="0.6"/>
              <stop offset="100%" stop-color="#ef4444" stop-opacity="0.6"/>
            </linearGradient>
          </defs>
          <!-- Connection lines between regional nodes -->
          <line x1="50%" y1="26%" x2="48%" y2="76%" stroke="url(#lineGrad)" stroke-width="1.5" stroke-dasharray="4,4" opacity="0.5"/>
          <line x1="50%" y1="26%" x2="78%" y2="44%" stroke="url(#lineGrad)" stroke-width="1.5" stroke-dasharray="4,4" opacity="0.5"/>
          <line x1="50%" y1="26%" x2="26%" y2="46%" stroke="url(#lineGrad)" stroke-width="1.5" stroke-dasharray="4,4" opacity="0.5"/>
          <line x1="48%" y1="76%" x2="78%" y2="44%" stroke="url(#lineGrad)" stroke-width="1.5" stroke-dasharray="4,4" opacity="0.5"/>
          <line x1="48%" y1="76%" x2="26%" y2="46%" stroke="url(#lineGrad)" stroke-width="1.5" stroke-dasharray="4,4" opacity="0.5"/>
        </svg>
        ${nodesHtml}
      </div>
    `;
  }
}
