/* Tiny dependency-free chart helpers (SVG / CSS bars). */
const RP = {
  tone(d) { return d <= 5 ? "var(--ok)" : d <= 30 ? "var(--warn)" : "var(--bad)"; },

  gauge(el, value, max = 60) {
    const v = Math.max(0, Math.min(value / max, 1));
    const col = RP.tone(value);
    el.innerHTML =
      `<svg viewBox="0 0 200 112"><path class="gtrack" d="M20 100 A80 80 0 0 1 180 100"/>` +
      `<path class="gval" pathLength="100" stroke="${col}" stroke-dasharray="0 100" d="M20 100 A80 80 0 0 1 180 100"/></svg>` +
      `<div class="gv" style="color:${col}">${value.toFixed(1)}<small>MIN DELAY</small></div>`;
    requestAnimationFrame(() => setTimeout(() => {
      el.querySelector(".gval").setAttribute("stroke-dasharray", `${(v * 100).toFixed(1)} 100`);
    }, 80));
  },

  bars(el, items, opts = {}) {
    const max = opts.max || Math.max(...items.map(i => i.value), 1);
    const unit = opts.unit || "";
    el.innerHTML = items.map(i =>
      `<div class="bar-row ${opts.narrow ? "narrow" : ""}"><div class="bar-label" title="${i.label}">${i.label}</div>` +
      `<div class="bar-track"><div class="bar-fill ${i.cls || ""}" data-w="${(i.value / max * 100).toFixed(1)}"></div></div>` +
      `<div class="bar-val">${i.value}${unit}</div></div>`).join("");
    requestAnimationFrame(() => setTimeout(() =>
      el.querySelectorAll(".bar-fill").forEach(b => b.style.width = b.dataset.w + "%"), 60));
  },

  scatter(el, pts) {
    const W = 420, H = 330, p = { l: 44, r: 14, t: 12, b: 38 };
    const max = Math.ceil(Math.max(...pts.flat()) / 10) * 10;
    const x = v => p.l + v / max * (W - p.l - p.r), y = v => H - p.b - v / max * (H - p.t - p.b);
    let s = `<svg class="chart" viewBox="0 0 ${W} ${H}">`;
    for (let i = 0; i <= 4; i++) {
      const t = max * i / 4;
      s += `<line class="grid" x1="${p.l}" x2="${W - p.r}" y1="${y(t)}" y2="${y(t)}"/><text x="${p.l - 6}" y="${y(t) + 3}" text-anchor="end">${Math.round(t)}</text>`;
      s += `<text x="${x(t)}" y="${H - p.b + 14}" text-anchor="middle">${Math.round(t)}</text>`;
    }
    s += `<line x1="${x(0)}" y1="${y(0)}" x2="${x(max)}" y2="${y(max)}" stroke="#e5534b" stroke-dasharray="5 4" stroke-width="1.5"/>`;
    s += pts.map(q => `<circle cx="${x(q[0]).toFixed(1)}" cy="${y(q[1]).toFixed(1)}" r="2.6" fill="#3478f6" opacity=".45"/>`).join("");
    s += `<text x="${(W + p.l) / 2}" y="${H - 6}" text-anchor="middle">Actual delay (min)</text>`;
    s += `<text transform="translate(12 ${H / 2}) rotate(-90)" text-anchor="middle">Predicted delay (min)</text></svg>`;
    el.innerHTML = s;
  },

  hist(el, counts, edges) {
    const W = 420, H = 250, p = { l: 36, r: 10, t: 10, b: 36 };
    const max = Math.max(...counts), n = counts.length, bw = (W - p.l - p.r) / n;
    const zero = p.l + (0 - edges[0]) / (edges[n] - edges[0]) * (W - p.l - p.r);
    let s = `<svg class="chart" viewBox="0 0 ${W} ${H}">`;
    counts.forEach((c, i) => {
      const h = c / max * (H - p.t - p.b);
      s += `<rect x="${(p.l + i * bw + 1).toFixed(1)}" y="${(H - p.b - h).toFixed(1)}" width="${(bw - 2).toFixed(1)}" height="${h.toFixed(1)}" rx="2" fill="#29b8c7" opacity=".85"/>`;
    });
    s += `<line x1="${zero}" x2="${zero}" y1="${p.t}" y2="${H - p.b}" stroke="#e5534b" stroke-dasharray="4 3"/>`;
    [0, Math.floor(n / 2), n].forEach(i => s += `<text x="${p.l + i * bw}" y="${H - p.b + 14}" text-anchor="middle">${edges[i].toFixed(0)}</text>`);
    s += `<text x="${(W + p.l) / 2}" y="${H - 6}" text-anchor="middle">Prediction error (min): predicted - actual</text></svg>`;
    el.innerHTML = s;
  },

  line(el, labels, values, hi) {
    const W = 560, H = 270, p = { l: 38, r: 16, t: 14, b: 40 };
    const max = Math.max(35, Math.ceil(Math.max(...values, hi || 0) / 10) * 10 + 5);
    const x = i => p.l + (labels.length === 1 ? 0 : i / (labels.length - 1)) * (W - p.l - p.r);
    const y = v => H - p.b - v / max * (H - p.t - p.b);
    let s = `<svg class="chart" viewBox="0 0 ${W} ${H}">`;
    for (let t = 0; t <= max; t += 10)
      s += `<line class="grid" x1="${p.l}" x2="${W - p.r}" y1="${y(t)}" y2="${y(t)}"/><text x="${p.l - 6}" y="${y(t) + 3}" text-anchor="end">${t}</text>`;
    [[5, "On-time limit", "#16865b"], [30, "Heavy delay", "#c0392b"]].forEach(([t, l, c]) => {
      if (t < max) s += `<line x1="${p.l}" x2="${W - p.r}" y1="${y(t)}" y2="${y(t)}" stroke="${c}" stroke-dasharray="5 4" opacity=".7"/><text x="${W - p.r}" y="${y(t) - 4}" text-anchor="end" fill="${c}" style="fill:${c}">${l}</text>`;
    });
    const pts = values.map((v, i) => `${x(i).toFixed(1)},${y(v).toFixed(1)}`);
    s += `<polygon points="${x(0)},${y(0)} ${pts.join(" ")} ${x(values.length - 1)},${y(0)}" fill="#3478f6" opacity=".12"/>`;
    s += `<polyline points="${pts.join(" ")}" fill="none" stroke="#3478f6" stroke-width="2.6" stroke-linejoin="round" stroke-dasharray="1200" stroke-dashoffset="1200"><animate attributeName="stroke-dashoffset" from="1200" to="0" dur="1.2s" fill="freeze"/></polyline>`;
    values.forEach((v, i) => {
      s += `<circle cx="${x(i).toFixed(1)}" cy="${y(v).toFixed(1)}" r="4.5" fill="var(--card)" stroke="${RP.tone(v)}" stroke-width="2.5"><title>${labels[i]}: ${v} min</title></circle>`;
      if (labels.length <= 12 || i % 2 === 0) s += `<text x="${x(i)}" y="${H - p.b + 15}" text-anchor="middle">${labels[i].replace("Destination", "Dest.")}</text>`;
    });
    s += `<text transform="translate(11 ${H / 2}) rotate(-90)" text-anchor="middle">Predicted delay (min)</text></svg>`;
    el.innerHTML = s;
  },
};

/* theme toggle */
(function () {
  const btn = document.getElementById("themeBtn");
  if (!btn) return;
  const set = t => { document.documentElement.setAttribute("data-theme", t); btn.textContent = t === "dark" ? "☀️" : "🌙"; };
  set(document.documentElement.getAttribute("data-theme") || "light");
  btn.addEventListener("click", () => {
    const t = document.documentElement.getAttribute("data-theme") === "dark" ? "light" : "dark";
    set(t); try { localStorage.setItem("rp-theme", t); } catch (e) {}
  });
})();
