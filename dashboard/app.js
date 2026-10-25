// VVater results dashboard. Every number shown comes from window.RESULTS (results/results.json).
const R = window.RESULTS, A = window.ANALOGS;
const css = (v) => getComputedStyle(document.documentElement).getPropertyValue(v).trim();
const f2 = d3.format(".2f"), f3 = d3.format(".3f"), pct = (v) => `${Math.round(v)}%`;
const DEPTHS = [0, 5, 10, 20, 30, 50, 75, 100, 125, 150, 200, 300, 500, 700, 1000];
const DEPTH_TICKS = [0, 20, 50, 100, 200, 500, 1000];
const tip = document.getElementById("tip");

function showTip(ev, html) {
  tip.innerHTML = html;
  tip.style.opacity = 1;
  const w = tip.offsetWidth, h = tip.offsetHeight;
  let x = ev.clientX + 16, y = ev.clientY + 12;
  if (x + w > innerWidth - 8) x = ev.clientX - w - 16;
  if (y + h > innerHeight - 8) y = innerHeight - h - 8;
  tip.style.left = x + "px"; tip.style.top = y + "px";
}
const hideTip = () => (tip.style.opacity = 0);
const row = (color, label, value) =>
  `<div class="row"><span>${color ? `<i style="background:${color}"></i>` : ""}${label}</span><span>${value}</span></div>`;

function segmented(el, options, initial, onChange) {
  el.innerHTML = "";
  options.forEach(([value, label]) => {
    const b = document.createElement("button");
    b.textContent = label;
    b.setAttribute("aria-pressed", value === initial);
    b.onclick = () => {
      el.querySelectorAll("button").forEach((x) => x.setAttribute("aria-pressed", x === b));
      onChange(value);
    };
    el.appendChild(b);
  });
  onChange(initial);
}

function depthScale(top, bottom) {
  return d3.scaleSymlog().constant(50).domain([0, 1000]).range([top, bottom]);
}
function depthAxis(g, y, x0) {
  g.attr("class", "axis").attr("transform", `translate(${x0},0)`)
    .call(d3.axisLeft(y).tickValues(DEPTH_TICKS).tickFormat((d) => (d === 1000 ? "1,000 m" : `${d} m`)).tickSizeOuter(0));
}

// ---------------------------------------------------------------- methods and colours

const best = R.regression.best_course_model;
const METHODS = [
  { key: "Climatology (floor)", label: "Climatology", color: css("--clim"), width: 2.5 },
  { key: "Simple linear (SST only)", label: "Simple linear (SST only)", color: css("--course-1"), width: 1.6 },
  { key: "Multiple linear", label: "Multiple linear", color: css("--course-2"), width: 1.6 },
  { key: "Polynomial", label: "Polynomial", color: css("--course-3"), width: 1.6 },
  { key: "KNN", label: "KNN", color: css("--course-4"), width: 1.6 },
  { key: "Decision tree", label: "Decision tree", color: css("--course-5"), width: 1.6 },
  { key: "Satelight per-cell ridge", label: "Satelight ridge (per cell)", color: "#b8860b", width: 1.2, dash: "2 3" },
  { key: "Satelight U-Net", label: "Satelight U-Net", color: css("--deep"), width: 1.4, dash: "6 4" },
  { key: "Satelight hybrid", label: "Satelight hybrid", color: css("--deep"), width: 3 },
  { key: "GLORYS (ceiling)", label: "GLORYS", color: css("--ceiling"), width: 2.5 },
];
const byKey = Object.fromEntries(METHODS.map((m) => [m.key, m]));
const shown = new Set(["Climatology (floor)", best, "Satelight hybrid", "GLORYS (ceiling)"]);
let region = "North Indian Ocean";

// ---------------------------------------------------------------- hero: RMSE by depth

function heroAnswer() {
  const g = R.regression.gap_closed_pct["North Indian Ocean"], s = R.regression.argo_summary["North Indian Ocean"];
  const t = R.regression.argo_rmse["North Indian Ocean"]["Satelight hybrid"];
  const worst = DEPTHS.reduce((a, d) => (t[d] > t[a] ? d : a), 0);
  let deepest = 0;
  for (const r of R.prove.test_A) { if (r.verdict.startsWith("Satelight")) deepest = r.depth_m; else break; }
  const same = Math.abs(s[best] - s["Satelight hybrid"]) < 0.005;
  document.getElementById("hero-answer").textContent =
    `To about ${deepest} m, measurably better than the long-term average. Satelight’s deep model closes ${pct(g["Satelight hybrid"])} of the gap ` +
    `between that average and the GLORYS reanalysis, and ${best.toLowerCase()} regression from the course closes ${pct(g[best])}` +
    (same ? `: on average over 15 depths the two are level.` : `.`) +
    ` Every method misses most in the thermocline: Satelight’s largest error is at ${worst} m.`;
}

function drawDepth() {
  const svg = d3.select("#depth-chart"); svg.selectAll("*").remove();
  const W = 640, H = 560, m = { l: 62, r: 16, t: 14, b: 44 };
  const data = R.regression.argo_rmse[region];
  const vis = METHODS.filter((x) => shown.has(x.key) && data[x.key]);
  const xmax = d3.max(vis, (x) => d3.max(DEPTHS, (d) => data[x.key][d])) * 1.06 || 1;
  const x = d3.scaleLinear().domain([0, xmax]).nice().range([m.l, W - m.r]);
  const y = depthScale(m.t, H - m.b);
  svg.append("g").attr("class", "gridline").attr("transform", `translate(0,${H - m.b})`)
    .call(d3.axisBottom(x).ticks(6).tickSize(-(H - m.t - m.b)).tickFormat("")).call((g) => g.select(".domain").remove());
  svg.append("g").attr("class", "axis").attr("transform", `translate(0,${H - m.b})`).call(d3.axisBottom(x).ticks(6).tickSizeOuter(0));
  depthAxis(svg.append("g"), y, m.l);
  svg.append("text").attr("class", "axis-title").attr("x", W - m.r).attr("y", H - 8).attr("text-anchor", "end").text("RMSE against Argo (°C)");
  const line = d3.line().x((d) => x(d[1])).y((d) => y(d[0]));
  vis.forEach((meth) => {
    const pts = DEPTHS.map((d) => [d, data[meth.key][d]]);
    svg.append("path").attr("d", line(pts)).attr("fill", "none").attr("stroke", meth.color)
      .attr("stroke-width", meth.width).attr("stroke-dasharray", meth.dash || null).attr("stroke-linejoin", "round");
    svg.append("g").selectAll("circle").data(pts).join("circle").attr("cx", (d) => x(d[1])).attr("cy", (d) => y(d[0]))
      .attr("r", meth.width > 2 ? 3.2 : 2.4).attr("fill", meth.color).attr("stroke", "#fff").attr("stroke-width", 1);
  });
  const cross = svg.append("line").attr("x1", m.l).attr("x2", W - m.r).attr("stroke", css("--ink-3")).attr("stroke-dasharray", "3 3").style("opacity", 0);
  svg.append("rect").attr("x", m.l).attr("y", m.t).attr("width", W - m.l - m.r).attr("height", H - m.t - m.b).attr("fill", "transparent")
    .on("mousemove", (ev) => {
      const [, py] = d3.pointer(ev);
      const d = DEPTHS.reduce((a, b) => (Math.abs(y(b) - py) < Math.abs(y(a) - py) ? b : a));
      cross.attr("y1", y(d)).attr("y2", y(d)).style("opacity", 1);
      const rows = vis.map((meth) => [meth, data[meth.key][d]]).sort((a, b) => a[1] - b[1]);
      showTip(ev, `<b>${d.toLocaleString()} m, ${region}</b>` + rows.map(([meth, v]) => row(meth.color, meth.label, `${f3(v)} °C`)).join(""));
    })
    .on("mouseleave", () => { cross.style("opacity", 0); hideTip(); });
}

function drawGap() {
  const svg = d3.select("#gap-chart"); svg.selectAll("*").remove();
  const g = R.regression.gap_closed_pct[region];
  const items = METHODS.filter((mm) => g[mm.key] !== undefined && !["Climatology (floor)", "GLORYS (ceiling)"].includes(mm.key))
    .map((mm) => ({ ...mm, v: g[mm.key] })).sort((a, b) => b.v - a.v);
  const W = 420, rowH = 40, m = { l: 168, r: 44, t: 8 }, H = m.t + items.length * rowH + 26;
  svg.attr("viewBox", `0 0 ${W} ${H}`);
  // Below −40% a bar is cut at the edge and labelled, so one very poor method does not squash the rest.
  const LOW = -40, x = d3.scaleLinear().domain([LOW, 100]).range([m.l, W - m.r]);
  const clip = (v) => Math.max(LOW, v);
  svg.append("line").attr("x1", x(0)).attr("x2", x(0)).attr("y1", m.t).attr("y2", H - 22).attr("stroke", css("--ink-3"));
  svg.append("line").attr("x1", x(100)).attr("x2", x(100)).attr("y1", m.t).attr("y2", H - 22).attr("stroke", css("--rule")).attr("stroke-dasharray", "3 3");
  svg.append("text").attr("class", "axis-title").attr("x", x(100)).attr("y", H - 6).attr("text-anchor", "end").text("100%: as good as GLORYS");
  svg.append("text").attr("class", "axis-title").attr("x", x(0)).attr("y", H - 6).attr("text-anchor", "middle").text("0%");
  const gg = svg.selectAll("g.b").data(items).join("g").attr("transform", (d, i) => `translate(0,${m.t + i * rowH})`);
  gg.append("text").attr("x", m.l - 10).attr("y", rowH / 2).attr("dy", "0.35em").attr("text-anchor", "end").attr("font-size", 13).attr("fill", css("--ink")).text((d) => d.label);
  gg.append("rect").attr("x", (d) => x(Math.min(0, clip(d.v)))).attr("y", rowH / 2 - 7).attr("height", 14).attr("rx", 3)
    .attr("width", (d) => Math.abs(x(clip(d.v)) - x(0))).attr("fill", (d) => d.color);
  gg.filter((d) => d.v < LOW).append("path").attr("d", `M${x(LOW) + 5},${rowH / 2 - 9} l-6,9 l6,9`).attr("fill", "none").attr("stroke", "#fff").attr("stroke-width", 2.5);
  gg.append("text").attr("x", (d) => (d.v < 0 ? x(0) + 6 : x(d.v) + 6)).attr("y", rowH / 2).attr("dy", "0.35em").attr("font-size", 13).attr("fill", css("--ink-2")).text((d) => pct(d.v));
  const s = R.regression.argo_summary[region];
  document.getElementById("gap-note").textContent =
    `Mean RMSE over the 15 depths in ${region === "North Indian Ocean" ? "the whole box" : "the " + region}: climatology ${f3(s["Climatology (floor)"])} °C, ` +
    `${best.toLowerCase()} ${f3(s[best])} °C, Satelight ${f3(s["Satelight hybrid"])} °C, GLORYS ${f3(s["GLORYS (ceiling)"])} °C, ` +
    `on the same ${R.regression.argo_points.toLocaleString()} measurements for every method.`;
}

function initHero() {
  heroAnswer();
  const chips = document.getElementById("methods");
  METHODS.forEach((mm) => {
    const b = document.createElement("button");
    b.className = "chip"; b.setAttribute("aria-pressed", shown.has(mm.key));
    b.innerHTML = `<i style="background:${mm.color}"></i>${mm.label}`;
    b.onclick = () => { shown.has(mm.key) ? shown.delete(mm.key) : shown.add(mm.key); b.setAttribute("aria-pressed", shown.has(mm.key)); drawDepth(); };
    chips.appendChild(b);
  });
  segmented(document.getElementById("region"), [["North Indian Ocean", "Whole box"], ["Bay of Bengal", "Bay of Bengal"], ["Arabian Sea", "Arabian Sea"]],
    region, (v) => { region = v; drawDepth(); drawGap(); });
}

// ---------------------------------------------------------------- hypothesis tests

function verdictCounts(T) {
  const sig = T.filter((r) => r["p (Holm)"] < 0.05);
  return { better: sig.filter((r) => r.difference < 0).length, worse: sig.filter((r) => r.difference > 0).length };
}

function initTests() {
  const a = verdictCounts(R.prove.test_A), b = verdictCounts(R.prove.test_B);
  const where = (T, sign) => T.filter((r) => r["p (Holm)"] < 0.05 && Math.sign(r.difference) === sign).map((r) => `${r.depth_m.toLocaleString()} m`).join(", ");
  const tie = 15 - b.better - b.worse;
  document.getElementById("real-answer").textContent =
    `Against climatology, Satelight’s advantage is real at ${a.better} of 15 depths` + (a.worse ? `; at ${where(R.prove.test_A, 1)} it is significantly worse` : "") +
    `. Against ${best.toLowerCase()} regression the data cannot tell the two apart at ${tie} of 15 depths` +
    (b.worse ? `; ${best.toLowerCase()} is significantly better at ${where(R.prove.test_B, 1)}` : "") +
    (b.better ? `; Satelight is significantly better at ${where(R.prove.test_B, -1)}` : "") +
    `. ${R.prove.floats.toLocaleString()} floats, α = 0.05 after correction for 15 tests.`;
  segmented(document.getElementById("test-pick"), [["A", "Satelight vs climatology"], ["B", `Satelight vs ${best.toLowerCase()}`]], "A", drawTest);
}

function drawTest(which) {
  const T = which === "A" ? R.prove.test_A : R.prove.test_B;
  const other = which === "A" ? "climatology" : best.toLowerCase();
  document.getElementById("test-title").textContent = `Satelight minus ${other}: left of zero means Satelight is better`;
  const svg = d3.select("#test-chart"); svg.selectAll("*").remove();
  const W = 620, H = 520, m = { l: 62, r: 16, t: 10, b: 44 };
  const ext = d3.extent(T.flatMap((r) => [r["CI low"], r["CI high"], 0]));
  const x = d3.scaleLinear().domain(ext).nice().range([m.l, W - m.r]);
  const y = depthScale(m.t + 8, H - m.b - 8);
  svg.append("g").attr("class", "axis").attr("transform", `translate(0,${H - m.b})`).call(d3.axisBottom(x).ticks(7).tickSizeOuter(0));
  depthAxis(svg.append("g"), y, m.l);
  svg.append("text").attr("class", "axis-title").attr("x", W - m.r).attr("y", H - 8).attr("text-anchor", "end").text("RMSE difference (°C)");
  svg.append("line").attr("x1", x(0)).attr("x2", x(0)).attr("y1", m.t).attr("y2", H - m.b).attr("stroke", css("--ink"));
  const g = svg.selectAll("g.r").data(T).join("g");
  g.append("line").attr("x1", (r) => x(r["CI low"])).attr("x2", (r) => x(r["CI high"])).attr("y1", (r) => y(r.depth_m)).attr("y2", (r) => y(r.depth_m))
    .attr("stroke", css("--ink-3")).attr("stroke-width", 2).attr("stroke-linecap", "round");
  g.append("circle").attr("cx", (r) => x(r.difference)).attr("cy", (r) => y(r.depth_m)).attr("r", 5.5)
    .attr("fill", (r) => (r["p (Holm)"] < 0.05 ? (r.difference < 0 ? css("--deep") : css("--bad")) : "#fff"))
    .attr("stroke", (r) => (r["p (Holm)"] < 0.05 ? "#fff" : css("--ink"))).attr("stroke-width", 1.5);
  g.append("rect").attr("x", m.l).attr("width", W - m.l - m.r).attr("y", (r) => y(r.depth_m) - 9).attr("height", 18).attr("fill", "transparent")
    .on("mousemove", (ev, r) => showTip(ev, `<b>${r.depth_m.toLocaleString()} m</b>` + row(null, "difference", `${f3(r.difference)} °C`) +
      row(null, "95% CI", `${f3(r["CI low"])} to ${f3(r["CI high"])}`) + row(null, "p (Holm)", r["p (Holm)"] < 0.001 ? "< 0.001" : f3(r["p (Holm)"])) + `<div style="margin-top:4px">${r.verdict}</div>`))
    .on("mouseleave", hideTip);
  const tb = d3.select("#test-table").html("");
  tb.append("thead").html("<tr><th>Depth</th><th>Difference (°C)</th><th>95% CI</th><th>p (Holm)</th></tr>");
  tb.append("tbody").selectAll("tr").data(T).join("tr").html((r) =>
    `<td>${r.depth_m.toLocaleString()} m</td><td class="${r["p (Holm)"] < 0.05 ? "best" : ""}">${f3(r.difference)}</td><td>${f3(r["CI low"])} to ${f3(r["CI high"])}</td><td>${r["p (Holm)"] < 0.001 ? "< 0.001" : f3(r["p (Holm)"])}</td>`);
}

// ---------------------------------------------------------------- fairness

function initFair() {
  const C = R.prove.test_C.filter((r) => r.model === "Satelight hybrid");
  const top = C.filter((r) => r.depth_m <= 300);
  const mb = d3.mean(top, (r) => r["skill Bay"]), ma = d3.mean(top, (r) => r["skill Arabian"]);
  const sig = C.filter((r) => r["p (Holm)"] < 0.05);
  const rep = R.prove.representation, fewer = rep["Bay of Bengal"].floats < rep["Arabian Sea"].floats;
  document.getElementById("fair-answer").textContent =
    `Measured as skill, Satelight’s average over 0–300 m is ${f2(mb)} in the Bay of Bengal and ${f2(ma)} in the Arabian Sea` +
    (mb > ma && fewer ? `: better in the Bay, even though the Bay has fewer floats to learn from and be judged on. ` : `. `) +
    (sig.length ? `The difference is significant at ${sig.length} of 15 depths (${sig.map((r) => r.depth_m.toLocaleString() + " m").join(", ")}).` : "No depth shows a significant difference after correction.");
  segmented(document.getElementById("fair-pick"), [["Satelight hybrid", "Satelight hybrid"], [best, best]], "Satelight hybrid", drawFair);
  d3.select("#rep-table").html(`<thead><tr><th>Sea</th><th>Floats</th><th>Casts</th><th>Casts per 100 deg²</th></tr></thead>` +
    `<tbody>${Object.entries(rep).map(([k, v]) => `<tr><td>${k}</td><td>${v.floats}</td><td>${v.casts.toLocaleString()}</td><td>${v["casts per 100 deg²"]}</td></tr>`).join("")}</tbody>`);
}

function drawFair(model) {
  const T = R.prove.test_C.filter((r) => r.model === model);
  const svg = d3.select("#fair-chart"); svg.selectAll("*").remove();
  const W = 620, H = 520, m = { l: 62, r: 110, t: 10, b: 44 };
  const x = d3.scaleLinear().domain([Math.min(0, d3.min(T, (r) => Math.min(r["skill Bay"], r["skill Arabian"]))), 1]).nice().range([m.l, W - m.r]);
  const y = depthScale(m.t + 6, H - m.b - 6);
  svg.append("g").attr("class", "axis").attr("transform", `translate(0,${H - m.b})`).call(d3.axisBottom(x).ticks(6).tickSizeOuter(0));
  depthAxis(svg.append("g"), y, m.l);
  svg.append("line").attr("x1", x(0)).attr("x2", x(0)).attr("y1", m.t).attr("y2", H - m.b).attr("stroke", css("--ink-3"));
  svg.append("text").attr("class", "axis-title").attr("x", W - m.r).attr("y", H - 8).attr("text-anchor", "end").text("Skill vs climatology");
  [["skill Bay", "Bay of Bengal", css("--bay")], ["skill Arabian", "Arabian Sea", css("--arabian")]].forEach(([k, label, color]) => {
    const pts = T.map((r) => [r.depth_m, r[k]]);
    svg.append("path").attr("d", d3.line().x((d) => x(d[1])).y((d) => y(d[0]))(pts)).attr("fill", "none").attr("stroke", color).attr("stroke-width", 2.2);
    svg.append("g").selectAll("circle").data(pts).join("circle").attr("cx", (d) => x(d[1])).attr("cy", (d) => y(d[0])).attr("r", 3.4).attr("fill", color).attr("stroke", "#fff");
  });
  [["Bay of Bengal", css("--bay")], ["Arabian Sea", css("--arabian")]].forEach(([label, color], i) => {
    const g = svg.append("g").attr("transform", `translate(${W - m.r + 14},${m.t + 14 + i * 22})`);
    g.append("rect").attr("width", 16).attr("height", 3).attr("y", -1.5).attr("rx", 1.5).attr("fill", color);
    g.append("text").attr("x", 22).attr("dy", "0.35em").attr("font-size", 13).attr("fill", css("--ink")).text(label);
  });
  svg.append("rect").attr("x", m.l).attr("y", m.t).attr("width", W - m.l - m.r).attr("height", H - m.t - m.b).attr("fill", "transparent")
    .on("mousemove", (ev) => {
      const [, py] = d3.pointer(ev);
      const r = T.reduce((a, b) => (Math.abs(y(b.depth_m) - py) < Math.abs(y(a.depth_m) - py) ? b : a));
      showTip(ev, `<b>${r.depth_m.toLocaleString()} m</b>` + row(css("--bay"), "Bay of Bengal", f3(r["skill Bay"])) + row(css("--arabian"), "Arabian Sea", f3(r["skill Arabian"])) +
        row(null, "p (Holm)", r["p (Holm)"] < 0.001 ? "< 0.001" : f3(r["p (Holm)"])));
    })
    .on("mouseleave", hideTip);
}

// ---------------------------------------------------------------- cyclone fuel

const FUEL_COLORS = { "Logistic regression": css("--course-3"), "KNN": css("--course-2"), "Decision tree": css("--course-5"),
  "Satelight hybrid → TCHP": css("--deep"), "Climatology → TCHP": css("--clim"), "GLORYS → TCHP": css("--ceiling") };

function initFuel() {
  const T = R.classify.test, bestC = R.classify.best, base = R.classify.majority_baseline;
  const sat = T["Satelight hybrid → TCHP"];
  const f1s = ["Logistic regression", "KNN", "Decision tree"].map((k) => T[k].F1);
  document.getElementById("fuel-answer").textContent =
    `Yes, mostly. All three course classifiers score an F1 between ${f2(d3.min(f1s))} and ${f2(d3.max(f1s))}; the best, ${bestC}, labels ${pct(T[bestC].accuracy * 100)} of the held-out floats correctly (ROC AUC ${f2(T[bestC]["ROC AUC"])}). ` +
    `Reconstructing the whole profile with Satelight and then computing the fuel gives F1 ${f2(sat.F1)}. Always answering the majority class would score ${pct(base.accuracy * 100)} accuracy, which is why accuracy alone is not enough.`;
  const cols = ["accuracy", "precision", "recall", "F1", "ROC AUC"];
  const rows = [...Object.entries(T), ["Always ‘fuel’ (baseline)", base]];
  const tb = d3.select("#fuel-table").html("");
  tb.append("thead").html(`<tr><th>Method</th>${cols.map((c) => `<th>${c}</th>`).join("")}</tr>`);
  tb.append("tbody").selectAll("tr").data(rows).join("tr")
    .attr("class", ([k]) => (R.classify.confusion[k] ? "pick" : ""))
    .html(([k, v]) => `<td>${k}</td>${cols.map((c) => `<td>${v[c] === undefined || v[c] === null ? "–" : f3(v[c])}</td>`).join("")}`)
    .on("click", function (ev, [k]) { if (R.classify.confusion[k]) selectCM(k); });
  selectCM(bestC);
  drawROC();
  document.getElementById("fuel-note").textContent =
    `Precision answers “when it says fuel, how often is it right?”; recall answers “of all the fuelled ocean, how much did it find?”. ` +
    `For a cyclone warning a missed fuel patch costs more than a false alarm, so recall matters most here. The test labels come from the floats themselves: ` +
    `${R.classify.casts_labelled.toLocaleString()} casts where the heat potential could be measured.`;
}

function selectCM(k) {
  d3.selectAll("#fuel-table tbody tr").classed("sel", ([key]) => key === k);
  const [[tn, fp], [fn, tp]] = R.classify.confusion[k];
  document.getElementById("cm-title").textContent = `Confusion matrix: ${k}`;
  const max = Math.max(tn, fp, fn, tp);
  const shade = (v, good) => `background:${d3.interpolateRgb("#f4f6f7", good ? "#9ec5f4" : "#f2b8a2")(v / max)}`;
  document.getElementById("cm").innerHTML =
    `<div class="h"></div><div class="h">said no fuel</div><div class="h">said fuel</div>` +
    `<div class="h">no fuel</div><div class="cell" style="${shade(tn, true)}"><b>${tn.toLocaleString()}</b>correct</div><div class="cell" style="${shade(fp, false)}"><b>${fp.toLocaleString()}</b>false alarm</div>` +
    `<div class="h">fuel</div><div class="cell" style="${shade(fn, false)}"><b>${fn.toLocaleString()}</b>missed</div><div class="cell" style="${shade(tp, true)}"><b>${tp.toLocaleString()}</b>correct</div>`;
}

function drawROC() {
  const svg = d3.select("#roc-chart"); svg.selectAll("*").remove();
  const W = 440, H = 400, m = { l: 48, r: 12, t: 10, b: 40 };
  const x = d3.scaleLinear().range([m.l, W - m.r]), y = d3.scaleLinear().range([H - m.b, m.t]);
  svg.append("g").attr("class", "axis").attr("transform", `translate(0,${H - m.b})`).call(d3.axisBottom(x).ticks(5).tickSizeOuter(0));
  svg.append("g").attr("class", "axis").attr("transform", `translate(${m.l},0)`).call(d3.axisLeft(y).ticks(5).tickSizeOuter(0));
  svg.append("line").attr("x1", x(0)).attr("y1", y(0)).attr("x2", x(1)).attr("y2", y(1)).attr("stroke", css("--rule")).attr("stroke-dasharray", "4 4");
  svg.append("text").attr("class", "axis-title").attr("x", W - m.r).attr("y", H - 6).attr("text-anchor", "end").text("False positive rate");
  svg.append("text").attr("class", "axis-title").attr("transform", "rotate(-90)").attr("x", -m.t).attr("y", 12).attr("text-anchor", "end").text("True positive rate");
  const entries = Object.entries(R.classify.roc);
  entries.forEach(([k, v]) => {
    svg.append("path").attr("d", d3.line().x((d) => x(d[0])).y((d) => y(d[1]))(v.fpr.map((f, i) => [f, v.tpr[i]])))
      .attr("fill", "none").attr("stroke", FUEL_COLORS[k] || css("--ink-3")).attr("stroke-width", k.startsWith("Satelight") ? 2.6 : 1.7);
  });
  const lg = svg.append("g").attr("transform", `translate(${x(0.42)},${y(0.36)})`);
  entries.forEach(([k, v], i) => {
    const g = lg.append("g").attr("transform", `translate(0,${i * 19})`);
    g.append("rect").attr("width", 14).attr("height", 3).attr("y", -2).attr("rx", 1.5).attr("fill", FUEL_COLORS[k] || css("--ink-3"));
    g.append("text").attr("x", 20).attr("dy", "0.35em").attr("font-size", 12).attr("fill", css("--ink-2")).text(`${k} (${f3(v.auc)})`);
  });
}

// ---------------------------------------------------------------- water types

function initTypes() {
  const c = R.cluster, mt = c.match, bay = c.by_basin_pct["Bay of Bengal"], arab = c.by_basin_pct["Arabian Sea"];
  const ks = d3.range(c.k).map(String);
  const bayHome = ks.reduce((a, k) => (bay[k] > bay[a] ? k : a)), arabOnly = ks.reduce((a, k) => (bay[k] < bay[a] ? k : a));
  document.getElementById("types-answer").textContent =
    `The silhouette score picked ${c.k} water types from ${c.profiles_used.toLocaleString()} float profiles. The algorithm never saw a position, yet ` +
    `${bay[bayHome]}% of Bay of Bengal floats fall into one type (cluster ${bayHome}), and cluster ${arabOnly} holds ${arab[arabOnly]}% of Arabian Sea floats but ${bay[arabOnly]}% of the Bay’s. ` +
    `Taken as a whole the types only partly follow the seas (adjusted Rand index ${f2(mt.basin.ARI)}, against ${f2(mt["shuffled control (basin)"].ARI)} for shuffled labels) ` +
    `and hardly follow the season (${f2(mt.season.ARI)}). k-means and agglomerative clustering agree with each other at ${f2(c.methods.ari_kmeans_vs_agglomerative)}.`;
  segmented(document.getElementById("cluster-pick"), [["kmeans", "k-means"], ["agglomerative", "Agglomerative"]], "kmeans", drawClusters);
  drawClusterMap();
  const t = c.by_basin_pct;
  const basins = Object.keys(t).filter((b) => b !== "Other");
  d3.select("#cluster-table").html(`<thead><tr><th>Cluster</th>${basins.map((b) => `<th>% of ${b} floats</th>`).join("")}</tr></thead><tbody>` +
    d3.range(c.k).map((k) => `<tr><td><i style="display:inline-block;width:10px;height:10px;border-radius:5px;margin-right:6px;background:${clusterColor(k)}"></i>${k}</td>${basins.map((b) => `<td>${t[b][k] ?? 0}%</td>`).join("")}</tr>`).join("") + "</tbody>");
}
// Clusters are numbered from warmest surface to coolest; colours follow that order.
const clusterColor = (k) => ["#cf4a32", "#2a9d8f", "#1f4e86", "#e8a33d", "#8c5bb5", "#6b7a8f", "#d1708f", "#3f8f3f"][k];

function drawClusters(method) {
  const P = R.cluster.profiles[method], L = R.cluster.levels;
  const svg = d3.select("#cluster-profiles"); svg.selectAll("*").remove();
  const W = 440, H = 460, m = { l: 56, r: 12, t: 10, b: 40 };
  const x = d3.scaleLinear().domain([d3.min(P, (p) => d3.min(p.p10)) - 0.5, d3.max(P, (p) => d3.max(p.p90)) + 0.5]).range([m.l, W - m.r]);
  const y = d3.scaleSymlog().constant(50).domain([0, 700]).range([m.t, H - m.b]);
  svg.append("g").attr("class", "axis").attr("transform", `translate(0,${H - m.b})`).call(d3.axisBottom(x).ticks(6).tickSizeOuter(0));
  svg.append("g").attr("class", "axis").attr("transform", `translate(${m.l},0)`).call(d3.axisLeft(y).tickValues([0, 20, 50, 100, 200, 500, 700]).tickFormat((d) => `${d} m`).tickSizeOuter(0));
  svg.append("text").attr("class", "axis-title").attr("x", W - m.r).attr("y", H - 6).attr("text-anchor", "end").text("Temperature (°C)");
  P.forEach((p) => {
    const col = clusterColor(p.cluster);
    svg.append("path").attr("d", d3.area().y((d, i) => y(L[i])).x0((d, i) => x(p.p10[i])).x1((d, i) => x(p.p90[i]))(L)).attr("fill", col).attr("opacity", 0.16);
    svg.append("path").attr("d", d3.line().x((d, i) => x(p.mean[i])).y((d, i) => y(L[i]))(L)).attr("fill", "none").attr("stroke", col).attr("stroke-width", 2.4);
    svg.append("text").attr("x", x(p.mean[0])).attr("y", y(0) + 2).attr("dy", "-0.4em").attr("text-anchor", "middle").attr("font-size", 12).attr("fill", css("--ink"))
      .text(`${p.cluster}`);
  });
  svg.append("rect").attr("x", m.l).attr("y", m.t).attr("width", W - m.l - m.r).attr("height", H - m.t - m.b).attr("fill", "transparent")
    .on("mousemove", (ev) => {
      const [, py] = d3.pointer(ev);
      const i = L.reduce((a, b, j) => (Math.abs(y(b) - py) < Math.abs(y(L[a]) - py) ? j : a), 0);
      showTip(ev, `<b>${L[i]} m</b>` + P.map((p) => row(clusterColor(p.cluster), `cluster ${p.cluster} (${p.n.toLocaleString()})`, `${f2(p.mean[i])} °C`)).join(""));
    })
    .on("mouseleave", hideTip);
}

function drawClusterMap() {
  const svg = d3.select("#cluster-map"); svg.selectAll("*").remove();
  const W = 480, H = 300, m = { l: 36, r: 8, t: 8, b: 26 };
  const x = d3.scaleLinear().domain([45, 105]).range([m.l, W - m.r]);
  const yh = (x(105) - x(45)) * 25 / 60;
  const y = d3.scaleLinear().domain([5, 30]).range([m.t + yh, m.t]);
  svg.attr("viewBox", `0 0 ${W} ${m.t + yh + m.b}`);
  svg.append("rect").attr("x", m.l).attr("y", m.t).attr("width", W - m.l - m.r).attr("height", yh).attr("fill", "#eef2f4");
  svg.append("g").attr("class", "axis").attr("transform", `translate(0,${m.t + yh})`).call(d3.axisBottom(x).ticks(6).tickFormat((d) => `${d}°E`).tickSizeOuter(0));
  svg.append("g").attr("class", "axis").attr("transform", `translate(${m.l},0)`).call(d3.axisLeft(y).ticks(5).tickFormat((d) => `${d}°N`).tickSizeOuter(0));
  svg.append("g").selectAll("circle").data(R.cluster.points).join("circle")
    .attr("cx", (d) => x(d[0])).attr("cy", (d) => y(d[1])).attr("r", 1.8).attr("fill", (d) => clusterColor(d[2])).attr("opacity", 0.8);
}

// ---------------------------------------------------------------- twin days

function initTwins() {
  const ev = R.recommend.evaluation;
  const get = (s) => ev.find((r) => r.Strategy.startsWith(s));
  const rec = get("Cosine"), cal = get("Same calendar"), rnd = get("Random");
  const key = "Subsurface RMSE of recommended days (°C)";
  document.getElementById("twins-answer").textContent =
    `Pick a day in 2023–2024. The recommender compares that day’s satellite picture with every day from 2010 to 2022 and returns the most similar, by cosine similarity. ` +
    `Below the surface, which it never saw, its picks are ${f2(rec[key])} °C from the chosen day on average, against ${f2(cal[key])} °C for the same date in another year and ${f2(rnd[key])} °C for a random day.`;
  const input = document.getElementById("qday");
  input.addEventListener("change", () => showAnalogs(input.value));
  document.querySelectorAll(".analog-form button").forEach((b) => (b.onclick = () => { input.value = b.dataset.day; showAnalogs(b.dataset.day); }));
  showAnalogs(input.value);
  drawRec(rec, cal, rnd, key);
}

function showAnalogs(day) {
  const list = A[day], ul = document.getElementById("analogs");
  if (!list) { ul.innerHTML = `<li>No satellite data for ${day}. Choose a day between 1 January 2023 and 15 December 2024.</li>`; return; }
  const maxR = d3.max(Object.values(A).flat(), (d) => d.rmse);
  const fmt = d3.timeFormat("%e %B %Y"), parse = d3.timeParse("%Y-%m-%d");
  ul.innerHTML = `<li class="lab"><span>Recommended day</span><span>Similarity at the surface (cosine)</span><span>Difference below, 50–200 m (°C)</span></li>` +
    list.map((d) => `<li><span>${fmt(parse(d.day))}</span>` +
      `<span><div class="bar" title="${f3(d.cos)}"><span style="width:${Math.max(0, d.cos) * 100}%;background:${css("--course-3")}"></span></div><span class="lab">${f3(d.cos)}</span></span>` +
      `<span><div class="bar" title="${f3(d.rmse)} °C"><span style="width:${(d.rmse / maxR) * 100}%;background:${css("--deep")}"></span></div><span class="lab">${f2(d.rmse)} °C</span></span></li>`).join("");
}

function drawRec(rec, cal, rnd, key) {
  const svg = d3.select("#rec-chart"); svg.selectAll("*").remove();
  const items = [["Recommender", rec[key], css("--course-3")], ["Same date, other year", cal[key], css("--clim")], ["Random day", rnd[key], "#c9ced3"]];
  const W = 420, m = { l: 150, r: 50, t: 6 }, rh = 46;
  const x = d3.scaleLinear().domain([0, d3.max(items, (d) => d[1])]).range([m.l, W - m.r]);
  const g = svg.selectAll("g").data(items).join("g").attr("transform", (d, i) => `translate(0,${m.t + i * rh})`);
  g.append("text").attr("x", m.l - 10).attr("y", rh / 2).attr("dy", "0.35em").attr("text-anchor", "end").attr("font-size", 13).attr("fill", css("--ink")).text((d) => d[0]);
  g.append("rect").attr("x", m.l).attr("y", rh / 2 - 8).attr("height", 16).attr("rx", 3).attr("width", (d) => x(d[1]) - m.l).attr("fill", (d) => d[2]);
  g.append("text").attr("x", (d) => x(d[1]) + 6).attr("y", rh / 2).attr("dy", "0.35em").attr("font-size", 13).attr("fill", css("--ink-2")).text((d) => `${f2(d[1])} °C`);
  const oracle = rec["Best possible (oracle) RMSE (°C)"];
  svg.append("line").attr("x1", x(oracle)).attr("x2", x(oracle)).attr("y1", m.t).attr("y2", m.t + items.length * rh).attr("stroke", css("--ink")).attr("stroke-dasharray", "3 3");
  svg.append("text").attr("x", x(oracle) + 4).attr("y", m.t + items.length * rh + 14).attr("font-size", 12).attr("fill", css("--ink-2")).text(`best possible ${f2(oracle)} °C`);
  const w = R.recommend.within_2023_2024;
  document.getElementById("rec-note").textContent =
    `The recommender beats “same date” on ${pct(R.recommend.beats_calendar_pct_of_days)} of days. Precision@5 (share of picks among the 5% truly most similar days below the surface): ` +
    `${pct(rec["Precision@5"] * 100)}, against ${pct(rnd["Precision@5"] * 100)} by chance. Within 2023–2024 alone, the plain surface PCA (${f2(w["Surface PCA (30)"])} °C) ` +
    `${w["Surface PCA (30)"] < w["Satelight embedding (192)"] ? "beats" : "loses to"} Satelight’s learned embedding (${f2(w["Satelight embedding (192)"])} °C) as a description of a day.`;
}

// ---------------------------------------------------------------- data quality

function initTrust() {
  const s = R.see, o = s.outliers, ag = s.agreement.rmse_by_band;
  const stats = [
    [`${s.missing_share_pct}<small>%</small>`, `of the INCOIS grid is empty. The map shows why: land and sea floor, where there is no water to measure.`],
    [`${o.range_test_failed}`, `cells hotter than any sea on Earth, up to ${f2(o.max_temp)} °C at ${o.max_temp_depth_m} m, in an official product. Another ${o.pass_range_but_above_35_below_50m} pass the test but are impossible at their depth.`],
    [`${f2(ag.Glider["0–300 m"])}<small>°C</small>`, `error against the independent glider in the top 300 m, the layer cyclones feed on. Below 300 m: ${f2(ag.Glider["300–950 m"])} °C.`],
  ];
  document.getElementById("trust-stats").innerHTML = stats.map(([v, l]) => `<div class="stat"><div class="v">${v}</div><div class="l">${l}</div></div>`).join("");
  document.getElementById("trust-note").textContent =
    `A box-plot rule (1.5 × IQR) flags ${o.iqr_flagged.toLocaleString()} of ${o.cells_checked.toLocaleString()} cells as unusual, mostly real variation in the thermocline. ` +
    `The published Argo range test (−2.5 to 40 °C) flags only the impossible. Of ${s.argo.levels_in_box.toLocaleString()} Argo levels in the Bay, ` +
    `${s.argo.levels_rejected} (${s.argo.rejected_pct}%) failed their own quality flags: they are counted and excluded, never silently dropped.`;
  const bands = Object.keys(ag.Argo), srcs = [["Argo", css("--course-3")], ["Glider", css("--deep")]];
  const svg = d3.select("#trust-chart"), W = 440, H = 260, m = { l: 44, r: 10, t: 10, b: 52 };
  const x0 = d3.scaleBand().domain(bands).range([m.l, W - m.r]).padding(0.28), x1 = d3.scaleBand().domain(srcs.map((d) => d[0])).range([0, x0.bandwidth()]).padding(0.12);
  const y = d3.scaleLinear().domain([0, d3.max(srcs, ([k]) => d3.max(bands, (b) => ag[k][b] || 0))]).nice().range([H - m.b, m.t]);
  svg.append("g").attr("class", "axis").attr("transform", `translate(0,${H - m.b})`).call(d3.axisBottom(x0).tickSizeOuter(0));
  svg.append("g").attr("class", "axis").attr("transform", `translate(${m.l},0)`).call(d3.axisLeft(y).ticks(5).tickSizeOuter(0));
  bands.forEach((b) => srcs.forEach(([k, col]) => {
    const v = ag[k][b]; if (v === null || v === undefined) return;
    svg.append("rect").attr("x", x0(b) + x1(k)).attr("width", x1.bandwidth()).attr("y", y(v)).attr("height", y(0) - y(v)).attr("rx", 3).attr("fill", col);
    svg.append("text").attr("x", x0(b) + x1(k) + x1.bandwidth() / 2).attr("y", y(v) - 5).attr("text-anchor", "middle").attr("font-size", 12).attr("fill", css("--ink-2")).text(f2(v));
  }));
  srcs.forEach(([k, col], i) => {
    const g = svg.append("g").attr("transform", `translate(${m.l + i * 90},${H - 14})`);
    g.append("rect").attr("width", 12).attr("height", 12).attr("y", -9).attr("rx", 2).attr("fill", col);
    g.append("text").attr("x", 18).attr("font-size", 12.5).attr("fill", css("--ink-2")).text(k);
  });
}

// ---------------------------------------------------------------- the depth rail

function initRail() {
  const secs = [...document.querySelectorAll("section[data-rail]")];
  const nav = document.querySelector(".rail nav"), marker = document.querySelector(".rail .marker"), column = document.querySelector(".rail .column");
  const links = secs.map((s) => { const a = document.createElement("a"); a.href = "#" + s.id; a.textContent = s.dataset.rail; nav.appendChild(a); return a; });
  const place = () => {
    const max = document.documentElement.scrollHeight - innerHeight, h = column.offsetHeight;
    secs.forEach((s, i) => (links[i].style.top = `${Math.min(1, s.offsetTop / max) * h}px`));
  };
  const onScroll = () => {
    const max = document.documentElement.scrollHeight - innerHeight, f = max > 0 ? scrollY / max : 0;
    marker.style.top = `${28 + f * column.offsetHeight}px`;
    let on = 0; secs.forEach((s, i) => { if (s.getBoundingClientRect().top < innerHeight * 0.4) on = i; });
    links.forEach((a, i) => a.classList.toggle("on", i === on));
  };
  addEventListener("scroll", onScroll, { passive: true });
  addEventListener("resize", () => { place(); onScroll(); });
  place(); onScroll();
}

initHero(); initTests(); initFair(); initFuel(); initTypes(); initTwins(); initTrust(); initRail();
