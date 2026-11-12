/**
 * Interactive Attack Graph Visualizer
 * Pure HTML5 Canvas Force-Directed Entity Relationship Visualizer
 */

class AttackGraphComponent {
  constructor(canvasId) {
    this.canvas = document.getElementById(canvasId);
    if (!this.canvas) return;
    this.ctx = this.canvas.getContext('2d');
    this.nodes = [];
    this.edges = [];
    this.nodeMap = new Map();
    this.draggedNode = null;
    this.hoveredNode = null;
    this.zoom = 1.0;
    this.panX = 0;
    this.panY = 0;
    this.isPanning = false;
    this.startPan = { x: 0, y: 0 };
    this.particles = [];

    this._setupEvents();
    this._startLoop();
  }

  setData(graphData) {
    if (!graphData || !graphData.nodes) return;

    const width = this.canvas.width || 800;
    const height = this.canvas.height || 450;

    // Build internal nodes with physics
    this.nodes = graphData.nodes.map((n, idx) => {
      const angle = (idx / graphData.nodes.length) * 2 * Math.PI;
      const radius = 140 + (idx % 2) * 50;
      return {
        ...n,
        x: width / 2 + Math.cos(angle) * radius,
        y: height / 2 + Math.sin(angle) * radius,
        vx: 0,
        vy: 0,
        radius: n.type === 'user' ? 24 : n.type === 'server' ? 20 : 16
      };
    });

    this.nodeMap = new Map(this.nodes.map(n => [n.id, n]));
    this.edges = (graphData.edges || []).map(e => ({
      ...e,
      sourceNode: this.nodeMap.get(e.source),
      targetNode: this.nodeMap.get(e.target)
    })).filter(e => e.sourceNode && e.targetNode);

    // Initialize animation particles along edges
    this.particles = [];
    for (let i = 0; i < this.edges.length * 2; i++) {
      const edge = this.edges[i % this.edges.length];
      this.particles.push({
        edge: edge,
        progress: Math.random(),
        speed: 0.005 + Math.random() * 0.005
      });
    }
  }

  _setupEvents() {
    if (!this.canvas) return;

    this.canvas.addEventListener('mousedown', (e) => {
      const rect = this.canvas.getBoundingClientRect();
      const mx = (e.clientX - rect.left - this.panX) / this.zoom;
      const my = (e.clientY - rect.top - this.panY) / this.zoom;

      for (const node of this.nodes) {
        const dx = node.x - mx;
        const dy = node.y - my;
        if (Math.hypot(dx, dy) <= node.radius) {
          this.draggedNode = node;
          if (window.app && window.app.showNodeDetails) {
            window.app.showNodeDetails(node);
          }
          return;
        }
      }
      this.isPanning = true;
      this.startPan = { x: e.clientX - this.panX, y: e.clientY - this.panY };
    });

    window.addEventListener('mousemove', (e) => {
      if (!this.canvas) return;
      const rect = this.canvas.getBoundingClientRect();
      const mx = (e.clientX - rect.left - this.panX) / this.zoom;
      const my = (e.clientY - rect.top - this.panY) / this.zoom;

      if (this.draggedNode) {
        this.draggedNode.x = mx;
        this.draggedNode.y = my;
      } else if (this.isPanning) {
        this.panX = e.clientX - this.startPan.x;
        this.panY = e.clientY - this.startPan.y;
      } else {
        this.hoveredNode = null;
        for (const node of this.nodes) {
          if (Math.hypot(node.x - mx, node.y - my) <= node.radius) {
            this.hoveredNode = node;
            break;
          }
        }
        this.canvas.style.cursor = this.hoveredNode ? 'pointer' : 'default';
      }
    });

    window.addEventListener('mouseup', () => {
      this.draggedNode = null;
      this.isPanning = false;
    });

    this.canvas.addEventListener('wheel', (e) => {
      e.preventDefault();
      const zoomFactor = e.deltaY < 0 ? 1.1 : 0.9;
      this.zoom = Math.max(0.4, Math.min(2.5, this.zoom * zoomFactor));
    });
  }

  zoomIn() { this.zoom = Math.min(2.5, this.zoom * 1.2); }
  zoomOut() { this.zoom = Math.max(0.4, this.zoom / 1.2); }
  resetView() { this.zoom = 1.0; this.panX = 0; this.panY = 0; }

  _simulateForces() {
    const kRepel = 1200;
    const kSpring = 0.05;
    const springLength = 100;

    // Repulsion between nodes
    for (let i = 0; i < this.nodes.length; i++) {
      for (let j = i + 1; j < this.nodes.length; j++) {
        const n1 = this.nodes[i];
        const n2 = this.nodes[j];
        const dx = n2.x - n1.x;
        const dy = n2.y - n1.y;
        const dist = Math.hypot(dx, dy) || 1;
        const force = kRepel / (dist * dist);
        const fx = (dx / dist) * force;
        const fy = (dy / dist) * force;

        if (n1 !== this.draggedNode) { n1.vx -= fx; n1.vy -= fy; }
        if (n2 !== this.draggedNode) { n2.vx += fx; n2.vy += fy; }
      }
    }

    // Spring forces along edges
    for (const edge of this.edges) {
      const n1 = edge.sourceNode;
      const n2 = edge.targetNode;
      const dx = n2.x - n1.x;
      const dy = n2.y - n1.y;
      const dist = Math.hypot(dx, dy) || 1;
      const delta = dist - springLength;
      const fx = (dx / dist) * delta * kSpring;
      const fy = (dy / dist) * delta * kSpring;

      if (n1 !== this.draggedNode) { n1.vx += fx; n1.vy += fy; }
      if (n2 !== this.draggedNode) { n2.vx -= fx; n2.vy -= fy; }
    }

    // Update positions with damping
    for (const node of this.nodes) {
      if (node === this.draggedNode) continue;
      node.vx *= 0.85;
      node.vy *= 0.85;
      node.x += node.vx;
      node.y += node.vy;
    }
  }

  _startLoop() {
    const render = () => {
      this._simulateForces();
      this._draw();
      requestAnimationFrame(render);
    };
    requestAnimationFrame(render);
  }

  _getNodeColor(node) {
    if (node.risk_level === 'CRITICAL' || node.risk_level === 'VERY_HIGH') return '#ef4444';
    if (node.risk_level === 'HIGH') return '#f97316';
    if (node.type === 'user') return '#38bdf8';
    if (node.type === 'location') return '#06b6d4';
    if (node.type === 'server') return '#818cf8';
    if (node.type === 'device') return '#a855f7';
    if (node.type === 'resource') return '#f43f5e';
    return '#10b981';
  }

  _draw() {
    if (!this.ctx || !this.canvas) return;

    // Resize canvas if needed
    const rect = this.canvas.getBoundingClientRect();
    if (this.canvas.width !== rect.width || this.canvas.height !== rect.height) {
      this.canvas.width = rect.width;
      this.canvas.height = rect.height;
    }

    const ctx = this.ctx;
    ctx.clearRect(0, 0, this.canvas.width, this.canvas.height);

    ctx.save();
    ctx.translate(this.panX, this.panY);
    ctx.scale(this.zoom, this.zoom);

    // 1. Draw Edges
    for (const edge of this.edges) {
      const isCrit = edge.severity === 'CRITICAL';
      ctx.beginPath();
      ctx.moveTo(edge.sourceNode.x, edge.sourceNode.y);
      ctx.lineTo(edge.targetNode.x, edge.targetNode.y);
      ctx.strokeStyle = isCrit ? 'rgba(239, 68, 68, 0.7)' : 'rgba(56, 189, 248, 0.35)';
      ctx.lineWidth = isCrit ? 2.5 : 1.5;
      if (isCrit) ctx.setLineDash([4, 4]);
      else ctx.setLineDash([]);
      ctx.stroke();

      // Edge Label
      const midX = (edge.sourceNode.x + edge.targetNode.x) / 2;
      const midY = (edge.sourceNode.y + edge.targetNode.y) / 2;
      ctx.fillStyle = '#94a3b8';
      ctx.font = '9px monospace';
      ctx.textAlign = 'center';
      ctx.fillText(edge.label || '', midX, midY - 4);
    }

    // 2. Draw Moving Threat Particles
    for (const p of this.particles) {
      p.progress += p.speed;
      if (p.progress > 1.0) p.progress = 0.0;
      const n1 = p.edge.sourceNode;
      const n2 = p.edge.targetNode;
      const px = n1.x + (n2.x - n1.x) * p.progress;
      const py = n1.y + (n2.y - n1.y) * p.progress;

      ctx.beginPath();
      ctx.arc(px, py, 3, 0, 2 * Math.PI);
      ctx.fillStyle = p.edge.severity === 'CRITICAL' ? '#ef4444' : '#38bdf8';
      ctx.shadowColor = ctx.fillStyle;
      ctx.shadowBlur = 6;
      ctx.fill();
      ctx.shadowBlur = 0;
    }

    // 3. Draw Nodes
    for (const node of this.nodes) {
      const color = this._getNodeColor(node);
      const isHovered = this.hoveredNode === node;

      // Glow effect
      ctx.beginPath();
      ctx.arc(node.x, node.y, node.radius + (isHovered ? 6 : 2), 0, 2 * Math.PI);
      ctx.fillStyle = isHovered ? 'rgba(56, 189, 248, 0.25)' : 'rgba(16, 22, 36, 0.8)';
      ctx.fill();

      // Core Node Circle
      ctx.beginPath();
      ctx.arc(node.x, node.y, node.radius, 0, 2 * Math.PI);
      ctx.fillStyle = '#101624';
      ctx.fill();
      ctx.lineWidth = 2.5;
      ctx.strokeStyle = color;
      ctx.stroke();

      // Icon / Label in center
      ctx.fillStyle = '#fff';
      ctx.font = `${node.radius * 0.7}px monospace`;
      ctx.textAlign = 'center';
      ctx.textBaseline = 'middle';
      const icon = node.type === 'user' ? '👤' : node.type === 'location' ? '📍' : node.type === 'server' ? '🖥️' : node.type === 'device' ? '💻' : '⚡';
      ctx.fillText(icon, node.x, node.y);

      // Node Name Label underneath
      ctx.fillStyle = '#f1f5f9';
      ctx.font = 'bold 10px sans-serif';
      ctx.fillText(node.label, node.x, node.y + node.radius + 12);
    }

    ctx.restore();
  }
}
