/**
 * Supervised ML Model Inspector Component
 * Displays model evaluation metrics, feature importance, confusion matrix, and live prediction playground.
 */

class MLPanelComponent {
  constructor(containerId) {
    this.container = document.getElementById(containerId);
    this.metrics = null;
  }

  render(metrics = null) {
    this.metrics = metrics || this.metrics;
    if (!this.container) return;

    const m = this.metrics || {
      accuracy: 0.9875,
      precision: 0.9776,
      recall: 0.9727,
      f1_score: 0.9757,
      total_samples: 1200,
      test_samples: 240,
      feature_importances: {
        "failed_login_count": 0.4251,
        "unknown_device": 0.3428,
        "cross_location_count": 0.1555,
        "integrity_tampered": 0.0713,
        "high_severity_action": 0.0054
      },
      confusion_matrix: {
        "LOW": { "LOW": 72, "MEDIUM": 0, "HIGH": 0, "VERY_HIGH": 0 },
        "MEDIUM": { "LOW": 0, "MEDIUM": 58, "HIGH": 0, "VERY_HIGH": 0 },
        "HIGH": { "LOW": 0, "MEDIUM": 0, "HIGH": 54, "VERY_HIGH": 0 },
        "VERY_HIGH": { "LOW": 0, "MEDIUM": 0, "HIGH": 3, "VERY_HIGH": 53 }
      }
    };

    // Feature importance bars
    const featEntries = Object.entries(m.feature_importances || {}).sort((a, b) => b[1] - a[1]);
    const featBarsHtml = featEntries.map(([feat, imp]) => {
      const pct = (imp * 100).toFixed(1);
      return `
        <div style="margin-bottom:0.6rem;">
          <div style="display:flex;justify-content:space-between;font-size:0.75rem;margin-bottom:0.2rem;">
            <span style="font-family:var(--font-mono);color:#cbd5e1;">${feat}</span>
            <span style="color:#38bdf8;font-weight:700;">${pct}%</span>
          </div>
          <div style="background:rgba(255,255,255,0.06);height:6px;border-radius:3px;overflow:hidden;">
            <div style="background:linear-gradient(90deg, #06b6d4, #3b82f6);height:100%;width:${pct}%;"></div>
          </div>
        </div>
      `;
    }).join('');

    // Confusion matrix table
    const classes = ["LOW", "MEDIUM", "HIGH", "VERY_HIGH"];
    const conf = m.confusion_matrix || {};
    let confRows = '';
    for (const actual of classes) {
      let cells = `<td style="font-weight:bold;color:#f1f5f9;padding:6px 10px;">${actual}</td>`;
      for (const pred of classes) {
        const count = conf[actual] ? (conf[actual][pred] || 0) : 0;
        const isDiag = actual === pred;
        cells += `
          <td style="text-align:center;padding:6px 10px;font-family:var(--font-mono);background:${isDiag ? 'rgba(16,185,129,0.12)' : count > 0 ? 'rgba(239,68,68,0.15)' : 'transparent'};color:${isDiag ? '#34d399' : count > 0 ? '#f87171' : '#64748b'};font-weight:${isDiag ? 'bold' : 'normal'};">
            ${count}
          </td>
        `;
      }
      confRows += `<tr>${cells}</tr>`;
    }

    this.container.innerHTML = `
      <div style="display:grid;grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));gap:1rem;margin-bottom:1.5rem;">
        <div class="kpi-card">
          <div class="kpi-icon" style="background:rgba(16,185,129,0.15);color:#34d399;">🎯</div>
          <div class="kpi-info">
            <div class="kpi-value">${((m.accuracy || 0.9875) * 100).toFixed(1)}%</div>
            <div class="kpi-label">Model Accuracy</div>
          </div>
        </div>
        <div class="kpi-card">
          <div class="kpi-icon" style="background:rgba(6,182,212,0.15);color:#38bdf8;">📊</div>
          <div class="kpi-info">
            <div class="kpi-value">${((m.precision || 0.9776) * 100).toFixed(1)}%</div>
            <div class="kpi-label">Precision Score</div>
          </div>
        </div>
        <div class="kpi-card">
          <div class="kpi-icon" style="background:rgba(168,85,247,0.15);color:#c084fc;">🔄</div>
          <div class="kpi-info">
            <div class="kpi-value">${((m.recall || 0.9727) * 100).toFixed(1)}%</div>
            <div class="kpi-label">Recall Score</div>
          </div>
        </div>
        <div class="kpi-card">
          <div class="kpi-icon" style="background:rgba(245,158,11,0.15);color:#fbbf24;">⚡</div>
          <div class="kpi-info">
            <div class="kpi-value">${((m.f1_score || 0.9757) * 100).toFixed(1)}%</div>
            <div class="kpi-label">F1-Measure</div>
          </div>
        </div>
      </div>

      <div style="display:grid;grid-template-columns:1fr 1fr;gap:1.25rem;margin-bottom:1.5rem;">
        <!-- Feature Importance Card -->
        <div class="card">
          <div class="card-header">
            <h3 class="card-title">📈 Gini Feature Importances</h3>
            <button class="btn-scenario btn-tamper" onclick="app.retrainMLModel()">🔄 Retrain Model</button>
          </div>
          <p style="font-size:0.75rem;color:#94a3b8;margin-bottom:1rem;">
            Relative predictive weight of input security telemetry variables extracted during training.
          </p>
          ${featBarsHtml}
        </div>

        <!-- Confusion Matrix Card -->
        <div class="card">
          <div class="card-header">
            <h3 class="card-title">🧮 Multi-Class Confusion Matrix</h3>
            <span style="font-size:0.7rem;color:#94a3b8;font-family:var(--font-mono);">N = ${m.test_samples || 240} (Test Split)</span>
          </div>
          <p style="font-size:0.75rem;color:#94a3b8;margin-bottom:1rem;">
            Evaluation breakdown comparing ground truth threat labels against supervised model predictions.
          </p>
          <div style="overflow-x:auto;">
            <table style="width:100%;border-collapse:collapse;font-size:0.78rem;">
              <thead>
                <tr style="border-bottom:1px solid rgba(255,255,255,0.1);color:#94a3b8;">
                  <th style="padding:6px;text-align:left;">Actual \\ Predicted</th>
                  ${classes.map(c => `<th style="padding:6px;text-align:center;">${c}</th>`).join('')}
                </tr>
              </thead>
              <tbody>
                ${confRows}
              </tbody>
            </table>
          </div>
        </div>
      </div>

      <!-- Live Prediction Playground -->
      <div class="card">
        <div class="card-header">
          <h3 class="card-title">🧪 Supervised ML Inference Playground</h3>
          <span style="font-size:0.75rem;color:#06b6d4;">Real-time Telemetry Classifier</span>
        </div>
        <p style="font-size:0.8rem;color:#94a3b8;margin-bottom:1rem;">
          Test the supervised classifier with arbitrary security attributes to observe predicted risk level, confidence, and feature contributions.
        </p>

        <div style="display:grid;grid-template-columns:repeat(auto-fit, minmax(200px, 1fr));gap:0.75rem;margin-bottom:1rem;">
          <div>
            <label style="font-size:0.75rem;color:#cbd5e1;display:block;margin-bottom:0.2rem;">Failed Login Count:</label>
            <input type="number" id="mlPlaygroundFailures" class="input-search" value="5" min="0" max="50" style="width:100%;">
          </div>
          <div>
            <label style="font-size:0.75rem;color:#cbd5e1;display:block;margin-bottom:0.2rem;">Cross-Location Count:</label>
            <select id="mlPlaygroundCrossLoc" class="select-filter" style="width:100%;">
              <option value="1">1 Region (Local)</option>
              <option value="2">2 Regions (Cross-Hopping)</option>
              <option value="3" selected>3+ Regions (Distributed Chain)</option>
            </select>
          </div>
          <div>
            <label style="font-size:0.75rem;color:#cbd5e1;display:block;margin-bottom:0.2rem;">Unusual Location:</label>
            <select id="mlPlaygroundUnusualLoc" class="select-filter" style="width:100%;">
              <option value="1" selected>Yes (Unusual / Unauthorized)</option>
              <option value="0">No (Standard Base)</option>
            </select>
          </div>
          <div>
            <label style="font-size:0.75rem;color:#cbd5e1;display:block;margin-bottom:0.2rem;">Unknown Device:</label>
            <select id="mlPlaygroundUnknownDev" class="select-filter" style="width:100%;">
              <option value="1" selected>Yes (Unregistered Hardware)</option>
              <option value="0">No (Known Corporate Device)</option>
            </select>
          </div>
          <div>
            <label style="font-size:0.75rem;color:#cbd5e1;display:block;margin-bottom:0.2rem;">High-Impact Action:</label>
            <select id="mlPlaygroundHighSev" class="select-filter" style="width:100%;">
              <option value="1" selected>Yes (Data Exfiltration / Priv-Esc)</option>
              <option value="0">No (Standard Command)</option>
            </select>
          </div>
        </div>

        <button class="btn-action btn-primary" style="margin-bottom:1rem;" onclick="app.runMLPlaygroundInference()">
          ⚡ Run ML Inference Test
        </button>

        <div id="mlPlaygroundResult" class="tamper-diff-box" style="display:none;"></div>
      </div>
    `;
  }
}
