// plain svg and html after halbat's charts, colours live in style.css

const NB = " ";
const SVG = "http://www.w3.org/2000/svg";
const PHONE_W = 500;

const nf = (n) => Math.round(n).toLocaleString("en").replace(/,/g, NB);
const pts = (v) => `+${v.toFixed(1)} pts`;
const finals = (n) => `${n} finals`;
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

function drawScatter(host, entries, names) {
  const w = host.clientWidth;
  if (!w) return;
  const phone = w < PHONE_W;
  const TOP = 28;
  const BOTTOM = 44;
  const plotH = Math.min(w, phone ? 340 : 460);
  const h = plotH + TOP + BOTTOM;
  const most = Math.max(...entries.map((e) => Math.max(e.jury, e.televote)));
  const step = niceStep(most, 5);
  const top = Math.ceil(most / step) * step;
  const x = linear(0, top, 6, w - 6);
  const y = linear(0, top, TOP + plotH, TOP);
  const ticks = Array.from({ length: top / step + 1 }, (_, i) => i * step);
  const far = farEntries(entries);

  const svg = el("svg", { width: w, height: h, viewBox: `0 0 ${w} ${h}`, role: "img",
    "aria-label": "Points from the juries against points from the public for every song in a final since 2016" });

  // quiet horizontal grid, the zero line one step stronger, values inside the right edge
  for (const v of ticks) {
    svg.append(el("line", { class: v === 0 ? "base" : "grid", x1: 0, x2: w, y1: y(v), y2: y(v) }));
    if (v > 0) svg.append(el("text", { class: "axis", x: w, y: y(v) - 5, "text-anchor": "end" }, nf(v)));
  }
  svg.append(el("text", { class: "axis", x: 0, y: 14 }, "Points from the public"));

  // the line where both agree, and the two halves it splits
  svg.append(el("line", { class: "eq", x1: x(0), y1: y(0), x2: x(top), y2: y(top) }));
  svg.append(el("text", { class: "note", x: x(top * 0.8) - 12, y: y(top * 0.8), "text-anchor": "end" }, "same score"));
  svg.append(el("text", { class: "note", x: x(0) + 4, y: y(top * 0.9) }, "Public liked it more"));
  svg.append(el("text", { class: "note", x: w - 4, y: y(top * 0.3), "text-anchor": "end" }, "Juries liked it more"));

  // every song as a hollow grey ring, keyboard steps along the jury axis
  const ordered = [...entries].sort((a, b) => a.jury - b.jury || a.televote - b.televote);
  ordered.forEach((e, i) => {
    const named = far.has(e);
    const g = el("g", {
      class: named ? "mark named" : "mark",
      role: "img",
      tabindex: i === 0 ? 0 : -1,
      "data-i": i,
      "data-tip": `${names[e.country]} ${e.year}\nJuries ${nf(e.jury)}, public ${nf(e.televote)}`,
      "aria-label": `${names[e.country]} ${e.year}, juries ${e.jury}, public ${e.televote}`,
    });
    g.append(el("circle", { class: "hit", cx: x(e.jury), cy: y(e.televote), r: 9 }));
    g.append(el("circle", { class: named ? "dot" : "ring", cx: x(e.jury), cy: y(e.televote), r: named ? 5 : 3.5 }));
    svg.append(g);
  });

  // names of the far ones, kept inside the plot
  for (const e of far) {
    const label = `${names[e.country]} ${e.year}`;
    const cx = x(e.jury);
    const right = cx + 10 + label.length * 7.4 > w;
    svg.append(el("text", { class: "name", x: right ? cx - 10 : cx + 10, y: y(e.televote) + 4,
      "text-anchor": right ? "end" : "start" }, label));
  }

  // x values under the zero line, first left and last right aligned
  ticks.forEach((v, i) => {
    const anchor = i === 0 ? "start" : i === ticks.length - 1 ? "end" : "middle";
    svg.append(el("text", { class: "axis", x: i === ticks.length - 1 ? w : x(v), y: TOP + plotH + 18, "text-anchor": anchor }, nf(v)));
  });
  svg.append(el("text", { class: "axis", x: w, y: TOP + plotH + 38, "text-anchor": "end" }, "Points from the juries"));

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
  const head = '<tr><td></td><th scope="col" class="num"><i class="dot jury"></i>Juries</th>' +
    '<th scope="col" class="num"><i class="dot public"></i>Public</th></tr>';
  const rows = [["The song", "entry_only"], ["The two countries", "pair_only"]]
    .map(([label, key]) =>
      `<tr><th scope="row">${label}</th><td class="num">${percent(split.jury[key])}</td>` +
      `<td class="num">${percent(split.televote[key])}</td></tr>`)
    .join("");
  document.getElementById("split-tabelle").innerHTML = head + rows;
}

/* ---------- who favours whom ---------- */

function rankList(id, rows, label, empty) {
  const list = document.getElementById(id);
  list.innerHTML = rows.length
    ? rows
        .map((r) =>
          `<li><span class="nm">${escape(label(r))}</span>` +
          `<span class="n">${finals(r.meetings)}</span><span class="wert">${pts(r.excess)}</span></li>`)
        .join("")
    : `<li class="leer">${escape(empty)}</li>`;
}

function topPairs(affinity, names, count = 8) {
  for (const type of ["t", "j"]) {
    const rows = affinity.filter((r) => r.type === type).sort((a, b) => b.excess - a.excess).slice(0, count);
    rankList(`liebling-${type}`, rows, (r) => `${names[r.from]} → ${names[r.to]}`, "");
  }
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
  const cell = (v) => (v ? `<td class="num">${nf(v)}</td>` : '<td class="num leise">–</td>');
  const head = '<tr><th scope="col">Country</th><th scope="col" class="num"><i class="dot jury"></i>Juries</th>' +
    '<th scope="col" class="num"><i class="dot public"></i>Public</th></tr>';
  const body = rows
    .map((r) => `<tr><th scope="row">${escape(names[r.other])}</th>${cell(r.jury)}${cell(r.public)}</tr>`)
    .join("");
  document.getElementById("explorer-tabelle").innerHTML = rows.length ? head + body : "";
}

function favourites(affinity, names, country) {
  const publicVote = affinity.filter((r) => r.type === "t");
  const gives = publicVote.filter((r) => r.from === country).sort((a, b) => b.excess - a.excess).slice(0, 5);
  const gets = publicVote.filter((r) => r.to === country).sort((a, b) => b.excess - a.excess).slice(0, 5);
  document.getElementById("fav-gibt-titel").textContent = `${names[country]} favours`;
  document.getElementById("fav-bekommt-titel").textContent = `${names[country]} is favoured by`;
  rankList("fav-gibt", gives, (r) => names[r.to], "No pair with three finals together");
  rankList("fav-bekommt", gets, (r) => names[r.from], "No pair with three finals together");
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

  yearSelect.addEventListener("change", () => { state.year = Number(yearSelect.value); draw(); });
  countrySelect.addEventListener("change", () => { state.country = countrySelect.value; draw(); });
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
