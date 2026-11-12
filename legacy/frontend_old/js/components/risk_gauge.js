/**
 * Explainable Risk Gauge and Breakdown Component
 * Renders the deterministic risk score, factor breakdown, and ML comparison.
 */

class RiskGaugeComponent {
  constructor(containerId) {
    this.container = document.getElementById(containerId);
  }

  render(riskAssessment, incidentTitle = "") {
    if (!this.container) return;

    if (!riskAssessment) {
      this.container.innerHTML = `<div style="color:#64748b;padding:1rem;">No risk assessment data available.</div>`;
      return;
    }

    const score = riskAssessment.overall_score || 0;
    const level = riskAssessment.risk_level || "LOW";
    const reasons = riskAssessment.reasons || [];
    const breakdown = riskAssessment.factor_breakdown || [];
    const mlPred = riskAssessment.ml_prediction;
    const mlConf = riskAssessment.ml_confidence ? (riskAssessment.ml_confidence * 100).toFixed(1) : "N/A";
    const recommendations = riskAssessment.recommended_action || "";

    const color = level === "VERY_HIGH" ? "#ef4444" : level === "HIGH" ? "#f97316" : level === "MEDIUM" ? "#f59e0b" : "#10b981";
    const strokeDash = `${(score / 100) * 283} 283`;

    // Factor breakdown cards
    let factorsHtml = '';
    if (breakdown.length > 0) {
      factorsHtml = breakdown.map(f => `
        <div class="factor-card ${f.severity}">
          <div class="factor-header">
            <span>${f.factor_name}</span>
            <span class="factor-pts">+${f.points_contributed} pts</span>
          </div>
          <div class="factor-desc">${f.description}</div>
        </div>
      `).join('');
    } else {
      factorsHtml = `<div style="color:#64748b;font-size:0.75rem;">No anomalous risk factors identified. Normal baseline.</div>`;
    }

    // Reasons bullet list
    const reasonsHtml = reasons.map(r => `<li style="margin-bottom:4px;color:#cbd5e1;">${r}</li>`).join('');

    this.container.innerHTML = `
      <div class="risk-explanation-panel">
        <!-- Hero Section with Dial and Summary -->
        <div class="risk-score-hero">
          <div class="risk-dial-wrapper">
            <svg viewBox="0 0 100 100" style="width:100%;height:100%;transform:rotate(-90deg);">
              <circle cx="50" cy="50" r="45" fill="none" stroke="rgba(255,255,255,0.06)" stroke-width="8"/>
              <circle cx="50" cy="50" r="45" fill="none" stroke="${color}" stroke-width="8"
                      stroke-dasharray="${strokeDash}" stroke-linecap="round" style="transition: stroke-dasharray 0.6s ease;"/>
            </svg>
            <div style="position:absolute;display:flex;flex-direction:column;align-items:center;">
              <span class="risk-dial-number" style="color:${color};">${score}</span>
              <span class="risk-dial-label">/ 100</span>
            </div>
          </div>

          <div class="risk-summary-text" style="flex:1;">
            <div style="display:flex;align-items:center;gap:0.6rem;margin-bottom:0.35rem;">
              <span class="badge-risk ${level}">${level.replace('_', ' ')} RISK</span>
              <span style="font-size:0.75rem;color:#94a3b8;font-family:var(--font-mono);">Confidence: ${(riskAssessment.confidence * 100).toFixed(0)}%</span>
              ${mlPred ? `<span style="font-size:0.72rem;background:rgba(168,85,247,0.15);border:1px solid rgba(168,85,247,0.4);color:#c084fc;padding:2px 6px;border-radius:4px;">🧠 ML Classifier: ${mlPred} (${mlConf}%)</span>` : ''}
            </div>
            <h3 style="color:#fff;">${incidentTitle || 'Cross-Location Risk Assessment'}</h3>
            <ul style="padding-left:1.2rem;font-size:0.82rem;margin-top:0.4rem;">
              ${reasonsHtml}
            </ul>
          </div>
        </div>

        <!-- Factor Contributions Grid -->
        <div style="margin-top:1rem;">
          <h4 style="font-size:0.8rem;color:#94a3b8;text-transform:uppercase;letter-spacing:0.6px;margin-bottom:0.5rem;">
            🎯 Quantified Risk Factors Breakdown
          </h4>
          <div class="factors-grid">
            ${factorsHtml}
          </div>
        </div>

        <!-- Actionable Recommendations -->
        ${recommendations ? `
          <div class="recommendation-box">
            <div class="rec-title">
              <span>🛡️ Actionable SOC Investigation & Containment Protocol</span>
            </div>
            <div class="rec-body">${recommendations}</div>
          </div>
        ` : ''}
      </div>
    `;
  }
}
