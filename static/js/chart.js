// static/js/chart.js
// Минималистичные графики (линия + горизонтальные бары) на чистом Canvas.
// Автор: CulT

const MiniCharts = (() => {
  function dpr(ctx, canvas) {
    const ratio = window.devicePixelRatio || 1;
    if (ratio !== 1) {
      const w = canvas.width, h = canvas.height;
      canvas.width = w * ratio;
      canvas.height = h * ratio;
      canvas.style.width = w + "px";
      canvas.style.height = h + "px";
      ctx.scale(ratio, ratio);
    }
  }

  function getCtx(id) {
    const canvas = document.getElementById(id);
    if (!canvas) return {};
    const ctx = canvas.getContext('2d');
    dpr(ctx, canvas);
    return { ctx, canvas };
  }

  function maxOf(values) {
    let m = 0;
    for (const v of values) if (v > m) m = v;
    return m;
  }

  function renderLine(id, labels, values, opts = {}) {
    const { ctx, canvas } = getCtx(id);
    if (!ctx) return;

    const W = canvas.width / (window.devicePixelRatio || 1);
    const H = canvas.height / (window.devicePixelRatio || 1);
    const pad = { t: 10, r: 10, b: 30, l: 30 };

    ctx.clearRect(0, 0, W, H);
    ctx.font = "12px system-ui, -apple-system, Segoe UI, Roboto, Arial";
    ctx.fillStyle = "#222";
    ctx.strokeStyle = "#ccc";

    // grid
    const maxV = Math.max(1, maxOf(values));
    const steps = 4;
    for (let i = 0; i <= steps; i++) {
      const y = pad.t + (H - pad.t - pad.b) * (i / steps);
      ctx.beginPath();
      ctx.moveTo(pad.l, y);
      ctx.lineTo(W - pad.r, y);
      ctx.strokeStyle = "#eee";
      ctx.stroke();

      // y labels (optional)
      const val = Math.round((maxV * (1 - i / steps)));
      // пропускаем подписи по Y для простоты
    }

    // line
    ctx.strokeStyle = "#3a7afe";
    ctx.lineWidth = 2;
    ctx.beginPath();
    const n = values.length || 1;
    for (let i = 0; i < n; i++) {
      const x = pad.l + (W - pad.l - pad.r) * (n === 1 ? 0.5 : i / (n - 1));
      const y = pad.t + (H - pad.t - pad.b) * (1 - values[i] / maxV);
      if (i === 0) ctx.moveTo(x, y); else ctx.lineTo(x, y);
    }
    ctx.stroke();

    // points
    ctx.fillStyle = "#3a7afe";
    for (let i = 0; i < n; i++) {
      const x = pad.l + (W - pad.l - pad.r) * (n === 1 ? 0.5 : i / (n - 1));
      const y = pad.t + (H - pad.t - pad.b) * (1 - values[i] / maxV);
      ctx.beginPath();
      ctx.arc(x, y, 2.5, 0, Math.PI * 2);
      ctx.fill();
    }

    // x labels (редко рисуем, чтобы не слипались)
    ctx.fillStyle = "#555";
    const stride = Math.ceil(labels.length / 8);
    for (let i = 0; i < labels.length; i += stride) {
      const x = pad.l + (W - pad.l - pad.r) * (labels.length === 1 ? 0.5 : i / (labels.length - 1));
      const y = H - pad.b + 14;
      ctx.fillText(labels[i], x - 12, y + 8);
    }

    // units
    if (opts.units) {
      ctx.fillStyle = "#777";
      ctx.fillText(opts.units, W - pad.r - 24, pad.t + 12);
    }
  }

  function renderHBar(id, labels, values, opts = {}) {
    const { ctx, canvas } = getCtx(id);
    if (!ctx) return;

    const W = canvas.width / (window.devicePixelRatio || 1);
    const H = canvas.height / (window.devicePixelRatio || 1);
    const pad = { t: 10, r: 10, b: 10, l: 100 };
    ctx.clearRect(0, 0, W, H);
    ctx.font = "12px system-ui, -apple-system, Segoe UI, Roboto, Arial";
    ctx.fillStyle = "#222";

    const maxV = Math.max(1, maxOf(values));
    const n = values.length;
    if (!n) return;

    const barH = Math.min(26, (H - pad.t - pad.b) / n - 6);
    let y = pad.t;

    for (let i = 0; i < n; i++) {
      const label = labels[i] || '';
      const val = values[i] || 0;
      const w = (W - pad.l - 20) * (val / maxV);

      // label
      ctx.fillStyle = "#333";
      ctx.fillText(label, 8, y + barH - 4);

      // bar
      ctx.fillStyle = "#5ac76d";
      ctx.fillRect(pad.l, y, w, barH);

      // value
      ctx.fillStyle = "#111";
      const text = val.toLocaleString("ru-RU");
      ctx.fillText(text, pad.l + w + 6, y + barH - 4);

      y += barH + 10;
    }

    if (opts.units) {
      ctx.fillStyle = "#777";
      ctx.fillText(opts.units, W - 40, 16);
    }
  }

  return { renderLine, renderHBar };
})();
