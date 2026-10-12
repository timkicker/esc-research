// colours come from the css tokens at draw time, so light and dark need no images

const css = (name) => getComputedStyle(document.documentElement).getPropertyValue(name).trim();
const still = matchMedia("(prefers-reduced-motion: reduce)").matches;
const percent = (share) => Math.round(share * 100);

async function load(name) {
  const response = await fetch(`data/${name}.json`);
  if (!response.ok) throw new Error(`data/${name}.json: ${response.status}`);
  return response.json();
}

// value at the end of each bar, in text colour and never in the series colour
const barValues = {
  id: "barValues",
  afterDatasetsDraw(chart) {
    const { ctx } = chart;
    ctx.save();
    ctx.fillStyle = css("--text");
    ctx.font = `500 13px ${getComputedStyle(document.body).fontFamily}`;
    ctx.textBaseline = "middle";
    chart.data.datasets.forEach((set, i) => {
      chart.getDatasetMeta(i).data.forEach((bar, j) => {
        ctx.fillText(`${set.data[j]} %`, bar.x + 6, bar.y);
      });
    });
    ctx.restore();
  },
};

function fillNumbers(split) {
  document.querySelectorAll("[data-split]").forEach((el) => {
    const [voteType, share] = el.dataset.split.split(".");
    el.textContent = percent(split[voteType][share]);
  });
}

function fillTable(split) {
  const rows = [
    ["The song", "entry_only"],
    ["The two countries", "pair_only"],
    ["Both together", "overlap"],
    ["Cannot be explained", "noise"],
  ];
  const head = "<tr><th></th><th class=\"num\">Juries</th><th class=\"num\">Public</th></tr>";
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
        x: {
          min: 0, max: 50,
          ticks: {
            stepSize: innerWidth < 500 ? 25 : 10,
            maxRotation: 0,
            color: css("--muted"),
            callback: (v) => `${v} %`,
          },
          grid: { color: css("--line") },
          border: { display: false },
        },
        y: { ticks: { color: css("--text") }, grid: { display: false }, border: { display: false } },
      },
      plugins: {
        legend: {
          position: "top",
          align: "start",
          labels: { color: css("--text"), boxWidth: 12, boxHeight: 12, useBorderRadius: true, borderRadius: 2 },
        },
        tooltip: { callbacks: { label: (c) => `${c.dataset.label}: ${c.parsed.x} %` } },
      },
    },
    plugins: [barValues],
  });
}

async function main() {
  Chart.defaults.font.family = getComputedStyle(document.body).fontFamily;
  Chart.defaults.font.size = 13;
  const { split } = await load("split");
  fillNumbers(split);
  fillTable(split);
  let chart = splitChart(split);
  // redraw with the other token set when the theme changes
  const redraw = () => { chart.destroy(); chart = splitChart(split); };
  matchMedia("(prefers-color-scheme: dark)").addEventListener("change", redraw);
  new MutationObserver(redraw).observe(document.documentElement, { attributes: true, attributeFilter: ["data-theme"] });
}

main().catch((error) => {
  console.error(error);
  document.querySelector("main").insertAdjacentHTML(
    "afterbegin", "<p class=\"meta\">The data could not be loaded.</p>");
});
