// colours come from the css tokens at draw time, so light and dark need no images

const css = (name) => getComputedStyle(document.documentElement).getPropertyValue(name).trim();
const still = matchMedia("(prefers-reduced-motion: reduce)").matches;
const narrow = () => innerWidth < 500;
const percent = (share) => Math.round(share * 100);
const font = () => getComputedStyle(document.body).fontFamily;

async function load(name) {
  const response = await fetch(`data/${name}.json`);
  if (!response.ok) throw new Error(`data/${name}.json: ${response.status}`);
  return response.json();
}

const records = (payload) =>
  payload.rows.map((row) => Object.fromEntries(payload.columns.map((c, i) => [c, row[i]])));

function withAlpha(colour, alpha) {
  const hex = colour.replace("#", "");
  const [r, g, b] = [0, 2, 4].map((i) => parseInt(hex.slice(i, i + 2), 16));
  return `rgba(${r}, ${g}, ${b}, ${alpha})`;
}

const escape = (text) =>
  String(text).replace(/[&<>"]/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" })[c]);

// value at the end of each bar, in text colour and never in the series colour
const barValues = {
  id: "barValues",
  afterDatasetsDraw(chart, _args, options) {
    const { ctx } = chart;
    ctx.save();
    ctx.fillStyle = css("--text");
    ctx.font = `500 12px ${font()}`;
    ctx.textBaseline = "middle";
    chart.data.datasets.forEach((set, i) => {
      chart.getDatasetMeta(i).data.forEach((bar, j) => {
        const value = set.data[j];
        if (value) ctx.fillText(`${value}${options.unit ?? ""}`, bar.x + 6, bar.y);
      });
    });
    ctx.restore();
  },
};

// names next to the highlighted dots of the scatter
const dotNames = {
  id: "dotNames",
  afterDatasetsDraw(chart) {
    const set = chart.data.datasets.find((d) => d.names);
    if (!set) return;
    const meta = chart.getDatasetMeta(chart.data.datasets.indexOf(set));
    const { ctx, chartArea } = chart;
    ctx.save();
    ctx.fillStyle = css("--text");
    ctx.font = `500 12px ${font()}`;
    ctx.textBaseline = "middle";
    meta.data.forEach((dot, i) => {
      const text = set.names[i];
      const width = ctx.measureText(text).width;
      const right = dot.x + 8 + width > chartArea.right;
      ctx.textAlign = right ? "right" : "left";
      ctx.fillText(text, right ? dot.x - 8 : dot.x + 8, dot.y);
    });
    ctx.restore();
  },
};

const axis = (title, extra = {}) => ({
  ticks: { color: css("--muted"), maxRotation: 0 },
  grid: { color: css("--line") },
  border: { display: false },
  title: { display: Boolean(title), text: title, color: css("--muted") },
  ...extra,
});

const legend = {
  position: "top",
  align: "start",
  labels: { color: css("--text"), boxWidth: 12, boxHeight: 12, useBorderRadius: true, borderRadius: 2 },
};

/* ---------- the split ---------- */

function fillNumbers(split) {
  document.querySelectorAll("[data-split]").forEach((el) => {
    const [voteType, share] = el.dataset.split.split(".");
    el.textContent = percent(split[voteType][share]);
  });
}

function splitTable(split) {
  const rows = [
    ["The song", "entry_only"],
    ["The two countries", "pair_only"],
    ["Both together", "overlap"],
    ["Cannot be explained", "noise"],
  ];
  const head = '<tr><th></th><th class="num">Juries</th><th class="num">Public</th></tr>';
  const body = rows
    .map(([label, key]) =>
      `<tr><td>${label}</td><td class="num">${percent(split.jury[key])} %</td>` +
      `<td class="num">${percent(split.televote[key])} %</td></tr>`)
    .join("");
  document.getElementById("split-tabelle").innerHTML = head + body;
}

function splitChart(split) {
  const shares = ["entry_only", "pair_only"];
  const bar = { borderRadius: 4, borderSkipped: false, barPercentage: 0.8, categoryPercentage: 0.8 };
  return new Chart(document.getElementById("split"), {
    type: "bar",
    data: {
      labels: ["The song", "The two countries"],
      datasets: [
        { label: "Juries", data: shares.map((s) => percent(split.jury[s])), backgroundColor: css("--akz"), ...bar },
        { label: "Public", data: shares.map((s) => percent(split.televote[s])), backgroundColor: css("--f-sand-flaeche"), ...bar },
      ],
    },
    options: {
      indexAxis: "y",
      maintainAspectRatio: false,
      animation: still ? false : { duration: 400 },
      layout: { padding: { right: 40 } },
      scales: {
        x: axis("", {
          min: 0,
          max: 50,
          ticks: { stepSize: narrow() ? 25 : 10, maxRotation: 0, color: css("--muted"), callback: (v) => `${v} %` },
        }),
        y: { ticks: { color: css("--text") }, grid: { display: false }, border: { display: false } },
      },
      plugins: {
        legend,
        barValues: { unit: " %" },
        tooltip: { callbacks: { label: (c) => `${c.dataset.label}: ${c.parsed.x} %` } },
      },
    },
    plugins: [barValues],
  });
}

/* ---------- juries against public ---------- */

function farEntries(entries) {
  const byGap = [...entries].sort((a, b) => (a.televote - a.jury) - (b.televote - b.jury));
  return [...byGap.slice(0, 2), ...byGap.slice(-3)];
}

function scatterChart(entries, names) {
  const far = new Set(farEntries(entries));
  const top = Math.ceil(Math.max(...entries.map((e) => Math.max(e.jury, e.televote))) / 50) * 50;
  const point = (e) => ({ x: e.jury, y: e.televote, entry: e });
  const highlighted = entries.filter((e) => far.has(e));
  return new Chart(document.getElementById("streuung"), {
    type: "scatter",
    data: {
      datasets: [
        {
          type: "line", label: "Same score", data: [{ x: 0, y: 0 }, { x: top, y: top }],
          borderColor: css("--line"), borderWidth: 2, pointRadius: 0, pointHitRadius: 0,
        },
        {
          label: "Songs", data: entries.filter((e) => !far.has(e)).map(point),
          backgroundColor: withAlpha(css("--muted"), 0.5), borderWidth: 0, pointRadius: 3.5, pointHoverRadius: 5,
        },
        {
          label: "Named", data: highlighted.map(point), names: highlighted.map((e) => `${names[e.country]} ${e.year}`),
          backgroundColor: css("--akz"), borderWidth: 0, pointRadius: 4.5, pointHoverRadius: 6,
        },
      ],
    },
    options: {
      maintainAspectRatio: false,
      animation: still ? false : { duration: 400 },
      scales: {
        x: axis("Points from the juries", { min: 0, max: top }),
        y: axis("Points from the public", { min: 0, max: top }),
      },
      plugins: {
        legend: { display: false },
        tooltip: {
          filter: (item) => item.raw.entry,
          callbacks: {
            title: (items) => {
              const e = items[0].raw.entry;
              return `${names[e.country]} ${e.year}`;
            },
            label: (item) => {
              const e = item.raw.entry;
              return [`${e.artist}, ${e.song}`, `Juries ${e.jury}, public ${e.televote}, place ${e.place}`];
            },
          },
        },
      },
    },
    plugins: [dotNames],
  });
}

function scatterTable(entries, names) {
  const head = '<tr><th>Year</th><th>Country</th><th>Song</th><th class="num">Juries</th><th class="num">Public</th></tr>';
  const body = entries
    .map((e) =>
      `<tr><td class="num">${e.year}</td><td>${escape(names[e.country])}</td>` +
      `<td>${escape(e.artist)}, ${escape(e.song)}</td>` +
      `<td class="num">${e.jury}</td><td class="num">${e.televote}</td></tr>`)
    .join("");
  document.getElementById("streuung-tabelle").innerHTML = head + body;
}

/* ---------- who favours whom ---------- */

function rankList(id, rows, label, empty) {
  const list = document.getElementById(id);
  list.innerHTML = rows.length
    ? rows
        .map((r) => `<li><span>${escape(label(r))}</span><span class="wert">+${r.excess.toFixed(1)}</span></li>`)
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

function explorerChart(rows, names) {
  const bar = { borderRadius: 4, borderSkipped: false, barPercentage: 0.8, categoryPercentage: 0.8 };
  document.getElementById("explorer-flaeche").style.height = `${Math.max(rows.length, 1) * 34 + 70}px`;
  return new Chart(document.getElementById("explorer-diagramm"), {
    type: "bar",
    data: {
      labels: rows.map((r) => names[r.other]),
      datasets: [
        { label: "Juries", data: rows.map((r) => r.jury), backgroundColor: css("--akz"), ...bar },
        { label: "Public", data: rows.map((r) => r.public), backgroundColor: css("--f-sand-flaeche"), ...bar },
      ],
    },
    options: {
      indexAxis: "y",
      maintainAspectRatio: false,
      animation: still ? false : { duration: 300 },
      layout: { padding: { right: 36 } },
      scales: {
        x: axis("Points", { min: 0, max: 12, ticks: { stepSize: narrow() ? 4 : 2, color: css("--muted"), maxRotation: 0 } }),
        y: { ticks: { color: css("--text"), autoSkip: false }, grid: { display: false }, border: { display: false } },
      },
      plugins: { legend, barValues: {} },
    },
    plugins: [barValues],
  });
}

function explorerTable(rows, names) {
  const head = '<tr><th>Country</th><th class="num">Juries</th><th class="num">Public</th></tr>';
  const body = rows
    .map((r) => `<tr><td>${escape(names[r.other])}</td><td class="num">${r.jury}</td><td class="num">${r.public}</td></tr>`)
    .join("");
  document.getElementById("explorer-tabelle").innerHTML = head + body;
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

function setupExplorer(meta, votes, affinity, charts) {
  const names = meta.countries;
  const yearSelect = document.getElementById("wahl-jahr");
  const countrySelect = document.getElementById("wahl-land");
  const gaveButton = document.getElementById("richtung-gab");
  const gotButton = document.getElementById("richtung-bekam");
  const hint = document.getElementById("explorer-hinweis");
  const state = { year: 2024, country: "GRC", gave: true };

  yearSelect.innerHTML = [...meta.years].reverse().map((y) => `<option value="${y}">${y}</option>`).join("");
  const countries = Object.keys(names).sort((a, b) => names[a].localeCompare(names[b]));
  countrySelect.innerHTML = countries.map((c) => `<option value="${c}">${escape(names[c])}</option>`).join("");
  yearSelect.value = String(state.year);
  countrySelect.value = state.country;

  const draw = () => {
    const rows = explorerRows(votes, state);
    charts.explorer?.destroy();
    hint.hidden = rows.length > 0;
    document.getElementById("explorer-flaeche").hidden = rows.length === 0;
    if (rows.length === 0) {
      const name = names[state.country];
      hint.textContent = state.gave
        ? `${name} did not vote in the final in ${state.year}.`
        : `${name} was not in the final in ${state.year}.`;
    } else {
      charts.explorer = explorerChart(rows, names);
    }
    explorerTable(rows, names);
    favourites(affinity, names, state.country);
    gaveButton.setAttribute("aria-pressed", String(state.gave));
    gotButton.setAttribute("aria-pressed", String(!state.gave));
  };

  yearSelect.addEventListener("change", () => { state.year = Number(yearSelect.value); draw(); });
  countrySelect.addEventListener("change", () => { state.country = countrySelect.value; draw(); });
  gaveButton.addEventListener("click", () => { state.gave = true; draw(); });
  gotButton.addEventListener("click", () => { state.gave = false; draw(); });
  draw();
  return draw;
}

/* ---------- start ---------- */

async function main() {
  Chart.defaults.font.family = font();
  Chart.defaults.font.size = 13;
  const [meta, splitData, entryData, voteData, affinityData] = await Promise.all(
    ["meta", "split", "entries", "votes", "affinity"].map(load));
  const { split } = splitData;
  const names = meta.countries;
  const entries = records(entryData);
  const votes = records(voteData);
  const affinity = records(affinityData);

  fillNumbers(split);
  splitTable(split);
  scatterTable(entries, names);
  topPairs(affinity, names);

  const charts = {};
  const drawStatic = () => {
    charts.split?.destroy();
    charts.scatter?.destroy();
    charts.split = splitChart(split);
    charts.scatter = scatterChart(entries, names);
  };
  drawStatic();
  const drawExplorer = setupExplorer(meta, votes, affinity, charts);

  // redraw with the other token set when the theme changes
  const redraw = () => { drawStatic(); drawExplorer(); };
  matchMedia("(prefers-color-scheme: dark)").addEventListener("change", redraw);
  new MutationObserver(redraw).observe(document.documentElement, { attributes: true, attributeFilter: ["data-theme"] });
}

main().catch((error) => {
  console.error(error);
  document.querySelector("main").insertAdjacentHTML(
    "afterbegin", '<p class="meta">The data could not be loaded.</p>');
});
