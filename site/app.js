// plain svg and html after halbat's charts, colours live in style.css

const NB = " ";
const SVG = "http://www.w3.org/2000/svg";
const PHONE_W = 500;

const nf = (n) => Math.round(n).toLocaleString("en").replace(/,/g, NB);
const percent = (share) => `${Math.round(share * 100)}${NB}%`;

const escape = (text) =>
  String(text).replace(/[&<>"]/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" })[c]);

async function load(name) {
  const response = await fetch(`data/${name}.json`);
  if (!response.ok) throw new Error(`data/${name}.json: ${response.status}`);
  return response.json();
}

const records = (payload) =>
  payload.rows.map((row) => Object.fromEntries(payload.columns.map((c, i) => [c, row[i]])));

/* ---------- scale and tooltip, after halbat's charts/scale.ts and tip.ts ---------- */

function niceStep(max, ticks = 5) {
  const raw = max / ticks;
  const p = 10 ** Math.floor(Math.log10(raw || 1));
  return [1, 2, 2.5, 5, 10].map((m) => m * p).find((s) => s >= raw) ?? p * 10;
}

const linear = (d0, d1, r0, r1) => {
  const k = d1 === d0 ? 0 : (r1 - r0) / (d1 - d0);
  return (v) => r0 + (v - d0) * k;
};

// one tooltip for hover, tap and keyboard focus
function tip(node) {
  const box = document.createElement("div");
  box.className = "tip";
  box.hidden = true;
  box.setAttribute("role", "tooltip");
  document.body.appendChild(box);
  let current = null;
  const show = (t) => {
    current = t;
    const [first, ...rest] = (t.dataset.tip ?? "").split("\n");
    box.replaceChildren(document.createTextNode(first));
    for (const line of rest) {
      const b = document.createElement("b");
      b.textContent = line;
      box.append(document.createElement("br"), b);
    }
    box.hidden = false;
    const r = t.getBoundingClientRect();
    const w = box.offsetWidth;
    const vw = document.documentElement.clientWidth;
    const x = Math.max(scrollX + w / 2 + 8, Math.min(r.left + r.width / 2 + scrollX, scrollX + vw - w / 2 - 8));
    box.style.left = `${x}px`;
    box.style.top = `${r.top + scrollY - 6}px`;
  };
  const over = (e) => {
    const t = e.target.closest?.("[data-tip]");
    if (t && node.contains(t)) show(t);
    else box.hidden = true;
  };
  const hide = () => { box.hidden = true; current = null; };
  node.addEventListener("pointerover", over);
  node.addEventListener("pointerdown", over);
  node.addEventListener("focusin", over);
  node.addEventListener("pointerleave", hide);
  node.addEventListener("focusout", hide);
  // focusing a mark scrolls it into view, so a focused mark keeps its tooltip
  addEventListener("scroll", () => {
    if (current && document.activeElement === current) show(current);
    else hide();
  }, { passive: true });
}

// roving focus over the marks, arrow keys step through them
function stepFocus(e) {
  const el = e.target;
  if (!el?.dataset?.i) return;
  const d = e.key === "ArrowRight" || e.key === "ArrowUp" ? 1 : e.key === "ArrowLeft" || e.key === "ArrowDown" ? -1 : 0;
  if (!d) return;
  e.preventDefault();
  const all = [...el.closest("svg").querySelectorAll("[data-i]")];
  const next = all[Math.max(0, Math.min(all.length - 1, all.indexOf(el) + d))];
  if (next && next !== el) {
    el.setAttribute("tabindex", "-1");
    next.setAttribute("tabindex", "0");
    next.focus();
  }
}

function el(name, attrs = {}, text) {
  const node = document.createElementNS(SVG, name);
  for (const [k, v] of Object.entries(attrs)) node.setAttribute(k, v);
  if (text != null) node.textContent = text;
  return node;
}

/* ---------- juries against public ---------- */

function farEntries(entries) {
  const byGap = [...entries].sort((a, b) => (a.televote - a.jury) - (b.televote - b.jury));
  return new Set([...byGap.slice(0, 2), ...byGap.slice(-3)]);
}

// songs on the same spot (often 0 and 0) fan out on a small spiral, the same way every time
function spread(entries, x, y) {
  const seen = new Map();
  return entries.map((e) => {
    const key = `${e.jury},${e.televote}`;
    const k = seen.get(key) ?? 0;
    seen.set(key, k + 1);
    const angle = k * 2.4;
    const radius = k ? 2.5 * Math.sqrt(k) : 0;
    return { e, cx: x(e.jury) + radius * Math.cos(angle), cy: y(e.televote) + radius * Math.sin(angle) };
  });
}

// real text width in the page font, a guess per letter was off by a few pixels
const measurer = document.createElement("canvas").getContext("2d");
function textWidth(text, weight = 500) {
  measurer.font = `${weight} 13px ${getComputedStyle(document.body).fontFamily}`;
  return measurer.measureText(text).width;
}

// a box per text that is already in the plot, names must not touch them
function textBox(x, y, text, anchor, weight = 400) {
  const w = textWidth(text, weight);
  const left = anchor === "end" ? x - w : anchor === "middle" ? x - w / 2 : x;
  return [left - 2, y - 14, w + 4, 19];
}

// geometry for the label checks
const DOT_R = 7;
const overlaps = ([ax, ay, aw, ah], [bx, by, bw, bh]) => ax < bx + bw && bx < ax + aw && ay < by + bh && by < ay + ah;
const grow = ([x, y, w, h], m) => [x - m, y - m, w + 2 * m, h + 2 * m];

function segmentHitsBox([x1, y1, x2, y2], [bx, by, bw, bh]) {
  // sample the segment, fine enough for boxes of a few pixels
  for (let t = 0; t <= 1; t += 0.05) {
    const px = x1 + (x2 - x1) * t;
    const py = y1 + (y2 - y1) * t;
    if (px > bx && px < bx + bw && py > by && py < by + bh) return true;
  }
  return false;
}

function segmentNearDot([x1, y1, x2, y2], d, r) {
  const vx = x2 - x1;
  const vy = y2 - y1;
  const t = Math.max(0, Math.min(1, ((d.cx - x1) * vx + (d.cy - y1) * vy) / (vx * vx + vy * vy || 1)));
  return Math.hypot(x1 + vx * t - d.cx, y1 + vy * t - d.cy) < r;
}

function segmentsCross([a, b, c, d], [e, f, g, h]) {
  const side = (px, py, qx, qy, rx, ry) => Math.sign((qx - px) * (ry - py) - (qy - py) * (rx - px));
  return side(a, b, c, d, e, f) !== side(a, b, c, d, g, h) && side(e, f, g, h, a, b) !== side(e, f, g, h, c, d);
}

// put a name where it covers no dot, no axis number and no other name, never under the
// zero line, stacked in the same order as the dots. near the dot first, further out
// with a short leader if it has to, and the leader gets the same checks as the name
function placeName(label, dot, dots, texts, placed, w, floor) {
  const width = textWidth(label) + 4;
  const height = 19;
  // the classic spots right next to the dot, then a grid further out that needs a leader
  const near = [
    { dx: 10, dy: 0, anchor: "start" },
    { dx: -10, dy: 0, anchor: "end" },
    { dx: 10, dy: -10, anchor: "start" },
    { dx: -10, dy: -10, anchor: "end" },
    { dx: 0, dy: -16, anchor: "middle" },
    { dx: 0, dy: 16, anchor: "middle" },
  ];
  const far = [];
  for (let dy = 40; dy >= -136; dy -= 8) {
    if (dy === 0) continue;
    for (let dx = 12; dx <= 156; dx += 12) {
      far.push({ dx, dy, anchor: "start", far: true }, { dx: -dx, dy, anchor: "end", far: true });
    }
  }
  const box = (o) => {
    const x = dot.cx + o.dx;
    const left = o.anchor === "end" ? x - width : o.anchor === "middle" ? x - width / 2 : x;
    return [left, dot.cy + o.dy - 10, width, height];
  };
  // from the edge of the dot to the nearest point of the name
  const leader = (b) => {
    const tx = Math.max(b[0], Math.min(dot.cx, b[0] + b[2]));
    const ty = Math.max(b[1], Math.min(dot.cy, b[1] + b[3]));
    const len = Math.hypot(tx - dot.cx, ty - dot.cy) || 1;
    return [dot.cx + ((tx - dot.cx) / len) * 6, dot.cy + ((ty - dot.cy) / len) * 6, tx, ty];
  };
  const inside = ([bx, by, bw, bh]) => bx >= 0 && bx + bw <= w && by >= 0 && by + bh <= floor - 2;
  const allBoxes = () => [...texts, ...placed.map((p) => p.box)];
  const freeOfText = (b) => !allBoxes().some((t) => overlaps(t, b));
  const covered = (b) => dots.filter((d) => d !== dot && overlaps(grow([d.cx, d.cy, 0, 0], DOT_R), b)).length;
  // a lower dot never gets its name above the name of a higher dot it shares columns with
  const inOrder = (b) =>
    placed.every((p) => {
      if (b[0] >= p.box[0] + p.box[2] || p.box[0] >= b[0] + b[2]) return true;
      const mine = b[1] + b[3] / 2;
      const theirs = p.box[1] + p.box[3] / 2;
      return dot.cy > p.cy ? mine > theirs : mine < theirs;
    });
  const leaderClear = (seg) =>
    !allBoxes().some((t) => segmentHitsBox(seg, grow(t, 4))) &&
    !dots.some((d) => d !== dot && segmentNearDot(seg, d, DOT_R)) &&
    !placed.some((p) => p.leader && segmentsCross(seg, p.leader));
  const clear = (o) => {
    const b = box(o);
    const crossesLeader = placed.some((p) => p.leader && segmentHitsBox(p.leader, grow(b, 4)));
    return inside(b) && freeOfText(b) && covered(b) === 0 && inOrder(b) && !crossesLeader && (!o.far || leaderClear(leader(b)));
  };
  // the closest spot that breaks no rule. if none exists, the closest that hides the
  // fewest dots, never one over text or below the axis
  const distance = (o) => Math.hypot(o.dx, o.dy);
  const byDistance = (list) => [...list].sort((a, b) => distance(a) - distance(b));
  const cost = (o) => {
    const b = box(o);
    return covered(b) * 1000 + (inOrder(b) ? 0 : 500) + (o.far && !leaderClear(leader(b)) ? 500 : 0) + distance(o);
  };
  const fallback = () =>
    far.filter((o) => inside(box(o)) && freeOfText(box(o))).sort((a, b) => cost(a) - cost(b))[0] ?? far[0];
  const toSpot = (o, penalty) => {
    const b = box(o);
    const spot = { x: dot.cx + o.dx, y: dot.cy + o.dy + 4, anchor: o.anchor, box: b, cy: dot.cy, cost: penalty + distance(o) };
    if (o.far) spot.leader = leader(b);
    return spot;
  };
  // every free spot, closest first, and the least bad one if none is free
  return {
    free: [...near.filter(clear), ...byDistance(far.filter(clear))].map((o) => toSpot(o, 0)),
    fallback: () => toSpot(fallback(), cost(fallback()) + 10000),
  };
}

// the names go in one after another, but a greedy pick can block a later name. with
// only a handful of names every combination of the closest free spots can be tried
function searchNames(items, dots, texts, w, floor) {
  const TRIES = 40;
  let budget = 50000;
  // the name with the fewest free spots goes first, it has the least room to give way
  const order = items.map((it, i) => ({ ...it, i, room: placeName(it.label, it.d, dots, texts, [], w, floor).free.length }))
    .sort((a, b) => a.room - b.room);
  let best = null;
  const search = (k, placed, total) => {
    if (--budget < 0 || (best && total >= best.total)) return;
    if (k === order.length) {
      best = { total, spots: [...placed] };
      return;
    }
    const { label, d } = order[k];
    const { free } = placeName(label, d, dots, texts, placed, w, floor);
    for (const spot of free.slice(0, TRIES)) {
      placed.push(spot);
      search(k + 1, placed, total + spot.cost);
      placed.pop();
    }
  };
  search(0, [], 0);
  if (!best) return null;
  const spots = [];
  order.forEach((o, k) => { spots[o.i] = best.spots[k]; });
  return { spots, total: best.total };
}

// if the names cannot all sit cleanly, one is left out. its dot keeps the tooltip and
// the table row, which is better than a name over a dot or a crossed line
function placeNames(items, dots, texts, w, floor) {
  const all = searchNames(items, dots, texts, w, floor);
  if (all) return all.spots;
  let best = null;
  items.forEach((_, skip) => {
    const rest = items.filter((__, i) => i !== skip);
    const found = searchNames(rest, dots, texts, w, floor);
    if (found && (!best || found.total < best.total)) {
      best = { total: found.total, spots: items.map((__, i) => (i === skip ? null : found.spots[i < skip ? i : i - 1])) };
    }
  });
  return best ? best.spots : items.map(() => null);
}

function drawScatter(host, entries, names) {
  const w = host.clientWidth;
  if (!w) return;
  const TOP = 28;
  const BOTTOM = 44;
  // square plot, the same pixels per point on both axes, so the diagonal runs at 45 degrees
  const plot = w - 12;
  const h = plot + TOP + BOTTOM;
  const most = Math.max(...entries.map((e) => Math.max(e.jury, e.televote)));
  const step = niceStep(most, 5);
  const top = Math.ceil(most / step) * step;
  const x = linear(0, top, 6, 6 + plot);
  const y = linear(0, top, TOP + plot, TOP);
  const ticks = Array.from({ length: top / step + 1 }, (_, i) => i * step);
  const far = farEntries(entries);

  const svg = el("svg", { width: w, height: h, viewBox: `0 0 ${w} ${h}`, role: "img",
    "aria-label": "Points from the juries against points from the public for every song in a final since 2016" });

  // every text already in the plot reserves its box, the names keep clear of them
  const taken = [];
  const write = (cls, px, py, text, anchor = "start") => {
    svg.append(el("text", { class: cls, x: px, y: py, "text-anchor": anchor }, text));
    taken.push(textBox(px, py, text, anchor));
  };

  // quiet horizontal grid, the zero line one step stronger, values inside the right edge,
  // the highest value stays unlabelled like in halbat
  for (const v of ticks) {
    svg.append(el("line", { class: v === 0 ? "base" : "grid", x1: 0, x2: w, y1: y(v), y2: y(v) }));
    if (v > 0 && v < top) write("axis", w, y(v) - 5, nf(v), "end");
  }
  // the y title sits over its own numbers
  write("axis", w, 12, "Points from the public", "end");

  // the line where both agree, the two halves named between the grid lines
  const between = (k) => y(step * (k + 0.5)) + 4;
  svg.append(el("line", { class: "eq", x1: x(0), y1: y(0), x2: x(top), y2: y(top) }));
  const sameAt = step * (ticks.length - 2.5);
  write("note", x(sameAt) - 10, between(ticks.length - 3), "same score", "end");
  write("note", x(0) + 4, between(ticks.length - 2), "Public liked it more");
  write("note", x(top), between(1), "Juries liked it more", "end");

  // every song as a hollow grey ring, keyboard steps along the jury axis
  const ordered = [...entries].sort((a, b) => a.jury - b.jury || a.televote - b.televote);
  const dots = spread(ordered, x, y);
  dots.forEach((d, i) => {
    const { e } = d;
    const named = far.has(e);
    const g = el("g", {
      class: named ? "mark named" : "mark",
      "data-key": e.country + e.year,
      role: "img",
      tabindex: i === 0 ? 0 : -1,
      "data-i": i,
      "data-tip": `${names[e.country]} ${e.year}\nJuries ${nf(e.jury)}, public ${nf(e.televote)}`,
      "aria-label": `${names[e.country]} ${e.year}, juries ${e.jury}, public ${e.televote}`,
    });
    g.append(el("circle", { class: "hit", cx: d.cx, cy: d.cy, r: 9 }));
    g.append(el("circle", { class: named ? "dot" : "ring", cx: d.cx, cy: d.cy, r: named ? 5 : 3.5 }));
    svg.append(g);
  });

  // names of the far ones, placed where they hide nothing, top dot first
  const items = dots.filter((dd) => far.has(dd.e)).sort((a, b) => a.cy - b.cy)
    .map((d) => ({ d, label: `${names[d.e.country]} ${d.e.year}` }));
  const spots = placeNames(items, dots, taken, w, y(0));
  for (const [i, { d, label }] of items.entries()) {
    const spot = spots[i];
    if (!spot) continue;
    if (spot.leader) {
      const [x1, y1, x2, y2] = spot.leader;
      svg.append(el("line", { class: "leader", x1, y1, x2, y2, "data-for": d.e.country + d.e.year }));
    }
    svg.append(el("text", { class: "name", x: spot.x, y: spot.y, "text-anchor": spot.anchor, "data-for": d.e.country + d.e.year }, label));
  }

  // x values under the zero line, the first left aligned, the highest unlabelled
  ticks.slice(0, -1).forEach((v, i) => {
    svg.append(el("text", { class: "axis", x: x(v), y: TOP + plot + 18, "text-anchor": i === 0 ? "start" : "middle" }, nf(v)));
  });
  svg.append(el("text", { class: "axis", x: w, y: TOP + plot + 38, "text-anchor": "end" }, "Points from the juries"));

  svg.addEventListener("keydown", stepFocus);
  host.replaceChildren(svg);
}

function scatterTable(entries, names) {
  const head = '<tr><th scope="col">Year</th><th scope="col">Country</th><th scope="col">Song</th>' +
    '<th scope="col" class="num">Juries</th><th scope="col" class="num">Public</th></tr>';
  const body = entries
    .map((e) =>
      `<tr><td class="num">${e.year}</td><td>${escape(names[e.country])}</td>` +
      `<td>${escape(e.artist)}, ${escape(e.song)}</td>` +
      `<td class="num">${nf(e.jury)}</td><td class="num">${nf(e.televote)}</td></tr>`)
    .join("");
  document.getElementById("streuung-tabelle").innerHTML = head + body;
}

/* ---------- the four times ---------- */

function splitTable(split) {
  const head = '<tr><td></td><th scope="col" class="num">Juries</th><th scope="col" class="num">Public</th></tr>';
  const rows = [["The song", "entry_only"], ["The two countries", "pair_only"]]
    .map(([label, key]) =>
      `<tr><th scope="row">${label}</th><td class="num">${percent(split.jury[key])}</td>` +
      `<td class="num">${percent(split.televote[key])}</td></tr>`)
    .join("");
  document.getElementById("split-tabelle").innerHTML = head + rows;
}

/* ---------- who favours whom ---------- */

const signed = (v) => (v < 0 ? `−${Math.abs(v).toFixed(1)}` : `+${v.toFixed(1)}`);

function rankTable(id, rows, label, empty, first = "Pair") {
  const table = document.getElementById(id);
  if (!rows.length) {
    table.innerHTML = `<tr><td class="leise">${escape(empty)}</td></tr>`;
    return;
  }
  const head = `<tr><th scope="col">${first}</th><th scope="col" class="num">Finals</th>` +
    '<th scope="col" class="num">Above song</th></tr>';
  const body = rows
    .map((r) =>
      `<tr><th scope="row">${escape(label(r))}</th><td class="num leise">${r.meetings}</td>` +
      `<td class="num">${signed(r.excess)}</td></tr>`)
    .join("");
  table.innerHTML = head + body;
}

function topPairs(affinity, names, count = 8) {
  for (const type of ["t", "j"]) {
    const rows = affinity.filter((r) => r.type === type).sort((a, b) => b.excess - a.excess).slice(0, count);
    rankTable(`liebling-${type}`, rows, (r) => `${names[r.from]} → ${names[r.to]}`, "");
  }
}

// on a phone the two lists share one place and a tab switches between them
function setupRankTabs() {
  const tabs = { t: document.getElementById("rang-tab-t"), j: document.getElementById("rang-tab-j") };
  const panels = { t: document.getElementById("rang-t"), j: document.getElementById("rang-j") };
  let shown = "t";
  const paint = () => {
    for (const k of ["t", "j"]) {
      tabs[k].setAttribute("aria-selected", String(k === shown));
      tabs[k].tabIndex = k === shown ? 0 : -1;
      panels[k].classList.toggle("aus", k !== shown);
    }
  };
  for (const k of ["t", "j"]) {
    tabs[k].addEventListener("click", () => { shown = k; paint(); });
    tabs[k].addEventListener("keydown", (e) => {
      if (e.key !== "ArrowLeft" && e.key !== "ArrowRight") return;
      shown = shown === "t" ? "j" : "t";
      paint();
      tabs[shown].focus();
    });
  }
  paint();
}


/* ---------- a select-only combobox, the aria pattern for a listbox behind a button ---------- */

function menu(host, labelId, options, initial, onPick) {
  const id = host.id;
  let value = initial;
  let active = 0;
  let typed = "";
  let typedAt = 0;

  host.innerHTML =
    `<button type="button" class="menue-knopf" role="combobox" aria-haspopup="listbox" aria-expanded="false" ` +
    `aria-controls="${id}-liste" aria-labelledby="${labelId} ${id}-wert">` +
    `<span id="${id}-wert"></span>` +
    '<svg class="chevron" viewBox="0 0 16 16" aria-hidden="true"><path d="M4 6l4 4 4-4"/></svg></button>' +
    `<ul class="menue-liste" role="listbox" id="${id}-liste" aria-labelledby="${labelId}" tabindex="-1" hidden>` +
    options
      .map((o, i) =>
        `<li role="option" id="${id}-o${i}" data-value="${escape(o.value)}" aria-selected="false">` +
        '<svg class="haken" viewBox="0 0 16 16" aria-hidden="true"><path d="M3.5 8.5l3 3 6-7"/></svg>' +
        `${escape(o.label)}</li>`)
      .join("") +
    "</ul>";

  const button = host.querySelector("button");
  const list = host.querySelector("ul");
  const items = [...list.children];
  const index = (v) => options.findIndex((o) => String(o.value) === String(v));

  const paint = () => {
    host.querySelector(`#${id}-wert`).textContent = options[index(value)].label;
    items.forEach((li, i) => {
      li.setAttribute("aria-selected", String(String(options[i].value) === String(value)));
      li.classList.toggle("aktiv", i === active);
    });
    button.setAttribute("aria-activedescendant", list.hidden ? "" : `${id}-o${active}`);
  };
  const open = () => {
    active = Math.max(0, index(value));
    list.hidden = false;
    button.setAttribute("aria-expanded", "true");
    paint();
    // the chosen row in the middle, so its neighbours show above and below
    const row = items[active];
    list.scrollTop = row.offsetTop - list.clientHeight / 2 + row.offsetHeight / 2;
  };
  const close = () => {
    list.hidden = true;
    button.setAttribute("aria-expanded", "false");
    paint();
  };
  const move = (i) => {
    active = Math.max(0, Math.min(options.length - 1, i));
    paint();
    items[active].scrollIntoView({ block: "nearest" });
  };
  const pick = (i) => {
    value = options[i].value;
    close();
    button.focus();
    onPick(value);
  };

  button.addEventListener("click", () => (list.hidden ? open() : close()));
  button.addEventListener("keydown", (e) => {
    const shut = list.hidden;
    if (shut && ["ArrowDown", "ArrowUp", "Enter", " "].includes(e.key)) { e.preventDefault(); open(); return; }
    if (shut) return;
    if (e.key === "ArrowDown") { e.preventDefault(); move(active + 1); }
    else if (e.key === "ArrowUp") { e.preventDefault(); move(active - 1); }
    else if (e.key === "Home") { e.preventDefault(); move(0); }
    else if (e.key === "End") { e.preventDefault(); move(options.length - 1); }
    else if (e.key === "PageDown") { e.preventDefault(); move(active + 8); }
    else if (e.key === "PageUp") { e.preventDefault(); move(active - 8); }
    else if (e.key === "Enter" || e.key === " ") { e.preventDefault(); pick(active); }
    else if (e.key === "Escape") { e.preventDefault(); close(); }
    else if (e.key === "Tab") close();
    else if (e.key.length === 1 && /\S/.test(e.key)) {
      // typing jumps to the first label that starts with what was typed
      const now = Date.now();
      typed = now - typedAt > 700 ? e.key.toLowerCase() : typed + e.key.toLowerCase();
      typedAt = now;
      const hit = options.findIndex((o) => String(o.label).toLowerCase().startsWith(typed));
      if (hit >= 0) move(hit);
    }
  });
  list.addEventListener("pointerdown", (e) => e.preventDefault());
  list.addEventListener("click", (e) => {
    const li = e.target.closest("li");
    if (li) pick(items.indexOf(li));
  });
  list.addEventListener("pointermove", (e) => {
    const li = e.target.closest("li");
    if (li && items.indexOf(li) !== active) { active = items.indexOf(li); paint(); }
  });
  document.addEventListener("pointerdown", (e) => { if (!host.contains(e.target) && !list.hidden) close(); });
  button.addEventListener("blur", () => { if (!list.hidden) close(); });
  paint();
  return { set: (v) => { value = v; paint(); } };
}

/* ---------- the explorer ---------- */

function explorerRows(votes, state) {
  const mine = votes.filter((v) => v.year === state.year && v[state.gave ? "from" : "to"] === state.country);
  const byOther = new Map();
  for (const v of mine) {
    const other = state.gave ? v.to : v.from;
    const row = byOther.get(other) ?? { other, jury: 0, public: 0 };
    row[v.type === "j" ? "jury" : "public"] += v.points;
    byOther.set(other, row);
  }
  return [...byOther.values()].sort((a, b) => b.jury + b.public - (a.jury + a.public));
}

function explorerTable(rows, names) {
  // no points stays an empty cell
  const cell = (v) => `<td class="num">${v ? nf(v) : ""}</td>`;
  const head = '<tr><th scope="col">Country</th><th scope="col" class="num">Juries</th>' +
    '<th scope="col" class="num">Public</th>' +
    '<th scope="col" class="num" aria-sort="descending">Total <span aria-hidden="true">↓</span></th></tr>';
  const body = rows
    .map((r) =>
      `<tr><th scope="row">${escape(names[r.other])}</th>${cell(r.jury)}${cell(r.public)}` +
      `<td class="num summe">${nf(r.jury + r.public)}</td></tr>`)
    .join("");
  document.getElementById("explorer-tabelle").innerHTML = rows.length ? head + body : "";
}

function favourites(affinity, names, country) {
  const publicVote = affinity.filter((r) => r.type === "t");
  const gives = publicVote.filter((r) => r.from === country).sort((a, b) => b.excess - a.excess).slice(0, 5);
  const gets = publicVote.filter((r) => r.to === country).sort((a, b) => b.excess - a.excess).slice(0, 5);
  document.getElementById("fav-gibt-titel").textContent = `${names[country]} favours`;
  document.getElementById("fav-bekommt-titel").textContent = `${names[country]} is favoured by`;
  rankTable("fav-gibt", gives, (r) => names[r.to], "No pair with three finals together", "Country");
  rankTable("fav-bekommt", gets, (r) => names[r.from], "No pair with three finals together", "Country");
}

function setupExplorer(meta, votes, affinity) {
  const names = meta.countries;
  const yearSelect = document.getElementById("wahl-jahr");
  const countrySelect = document.getElementById("wahl-land");
  const tabs = { gave: document.getElementById("richtung-gab"), got: document.getElementById("richtung-bekam") };
  const hint = document.getElementById("explorer-hinweis");
  const state = { year: 2024, country: "GRC", gave: true };

  yearSelect.innerHTML = [...meta.years].reverse().map((y) => `<option value="${y}">${y}</option>`).join("");
  const countries = Object.keys(names).sort((a, b) => names[a].localeCompare(names[b]));
  countrySelect.innerHTML = countries.map((c) => `<option value="${c}">${escape(names[c])}</option>`).join("");
  yearSelect.value = String(state.year);
  countrySelect.value = state.country;

  const draw = () => {
    const rows = explorerRows(votes, state);
    hint.hidden = rows.length > 0;
    if (!rows.length) {
      const name = names[state.country];
      hint.textContent = state.gave
        ? `${name} did not vote in the final in ${state.year}.`
        : `${name} was not in the final in ${state.year}.`;
    }
    explorerTable(rows, names);
    favourites(affinity, names, state.country);
    tabs.gave.setAttribute("aria-selected", String(state.gave));
    tabs.got.setAttribute("aria-selected", String(!state.gave));
    tabs.gave.tabIndex = state.gave ? 0 : -1;
    tabs.got.tabIndex = state.gave ? -1 : 0;
  };

  // own menus on wide screens, the native selects on phones, both kept in step
  const years = [...meta.years].reverse().map((y) => ({ value: y, label: String(y) }));
  const lands = countries.map((c) => ({ value: c, label: names[c] }));
  const yearMenu = menu(document.getElementById("menue-jahr"), "name-jahr", years, state.year, (v) => {
    state.year = Number(v); yearSelect.value = String(v); draw();
  });
  const landMenu = menu(document.getElementById("menue-land"), "name-land", lands, state.country, (v) => {
    state.country = v; countrySelect.value = v; draw();
  });
  yearSelect.addEventListener("change", () => { state.year = Number(yearSelect.value); yearMenu.set(state.year); draw(); });
  countrySelect.addEventListener("change", () => { state.country = countrySelect.value; landMenu.set(state.country); draw(); });
  tabs.gave.addEventListener("click", () => { state.gave = true; draw(); });
  tabs.got.addEventListener("click", () => { state.gave = false; draw(); });
  // arrow keys move between the two tabs
  for (const tab of Object.values(tabs)) {
    tab.addEventListener("keydown", (e) => {
      if (e.key !== "ArrowLeft" && e.key !== "ArrowRight") return;
      state.gave = !state.gave;
      draw();
      (state.gave ? tabs.gave : tabs.got).focus();
    });
  }
  draw();
}

/* ---------- start ---------- */

async function main() {
  const [meta, splitData, entryData, voteData, affinityData] = await Promise.all(
    ["meta", "split", "entries", "votes", "affinity"].map(load));
  const names = meta.countries;
  const entries = records(entryData);

  splitTable(splitData.split);
  scatterTable(entries, names);
  topPairs(records(affinityData), names);
  setupRankTabs();
  setupExplorer(meta, records(voteData), records(affinityData));

  const host = document.getElementById("streuung");
  tip(host);
  drawScatter(host, entries, names);
  let last = host.clientWidth;
  new ResizeObserver(() => {
    if (host.clientWidth !== last) {
      last = host.clientWidth;
      drawScatter(host, entries, names);
    }
  }).observe(host);
}

main().catch((error) => {
  console.error(error);
  document.querySelector("main").insertAdjacentHTML(
    "afterbegin", '<p class="meta">The data could not be loaded.</p>');
});
