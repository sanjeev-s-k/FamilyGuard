/**
 * Cross-Location Attack Timeline Component
 * Renders chronological sequence of events across distributed locations.
 */

class TimelineComponent {
  constructor(containerId) {
    this.container = document.getElementById(containerId);
  }

  render(timelineSteps = []) {
    if (!this.container) return;

    if (!timelineSteps || timelineSteps.length === 0) {
      this.container.innerHTML = `
        <div style="text-align:center;padding:2rem;color:#64748b;font-size:0.85rem;">
          No timeline events available for this incident.
        </div>
      `;
      return;
    }

    let stepsHtml = '';
    timelineSteps.forEach((step) => {
      const impactClass = step.risk_impact || 'LOW';
      const timeFormatted = step.timestamp ? new Date(step.timestamp).toLocaleTimeString() : 'N/A';

      stepsHtml += `
        <div class="timeline-step-item">
          <div class="timeline-node-dot ${impactClass}">
            ${step.step_number}
          </div>
          <div class="timeline-card">
            <div class="timeline-card-head">
              <div class="timeline-tags">
                <span class="tag-pill loc">📍 ${step.location}</span>
                <span class="tag-pill srv">🖥️ ${step.server_id}</span>
                <span class="tag-pill" style="font-family:var(--font-mono);font-size:0.65rem;">👤 ${step.user_id}</span>
                <span class="tag-pill" style="font-family:var(--font-mono);font-size:0.65rem;">💻 ${step.device_id}</span>
              </div>
              <span class="timeline-time">${timeFormatted}</span>
            </div>
            <div class="timeline-text">${step.description}</div>
          </div>
        </div>
      `;
    });

    this.container.innerHTML = `
      <div class="timeline-container">
        ${stepsHtml}
      </div>
    `;
  }
}
