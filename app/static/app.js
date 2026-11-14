"use strict";

const $ = (id) => document.getElementById(id);
const state = { payload: null, selected: null, viewer: null };

const ENDPOINT_LABELS = {
  neurotox_moe: "Neurotox",
  tlr7_inhibition: "TLR7",
  tlr8_potentiation: "TLR8",
};

function fmt(value, digits = 2) {
  if (value === null || value === undefined || Number.isNaN(value)) return "—";
  return Number(value).toFixed(digits);
}

function setStatus(message, isError) {
  const node = $("status");
  node.hidden = !message;
  node.textContent = message || "";
  node.classList.toggle("error", Boolean(isError));
}

function query() {
  const params = new URLSearchParams({
    gene: $("gene").value.trim() || "MAPT",
    chemistry: $("chemistry").value,
    step: $("step").value,
    limit: $("limit").value,
    sort: $("sort").value,
  });
  return params;
}

async function run(event) {
  if (event) event.preventDefault();
  const button = $("run");
  button.disabled = true;
  setStatus("Fetching transcript, tiling candidates and scoring…", false);
  try {
    const pasted = $("pasted").value.trim();
    let response;
    if (pasted) {
      response = await fetch("/api/design", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          sequence: pasted,
          gene: $("gene").value.trim() || "PASTED",
          chemistry: $("chemistry").value,
          step: $("step").value,
          limit: $("limit").value,
          sort: $("sort").value,
        }),
      });
    } else {
      response = await fetch(`/api/design?${query()}`);
    }
    const payload = await response.json();
    if (!response.ok) throw new Error(payload.error || response.statusText);
    state.payload = payload;
    render(payload);
    setStatus("", false);
  } catch (error) {
    setStatus(error.message, true);
  } finally {
    button.disabled = false;
  }
}

function render(payload) {
  const t = payload.transcript;
  $("provenance").innerHTML =
    `<strong>${t.gene}</strong> &middot; ${t.transcript_id} &middot; ${t.length} nt` +
    `<br>${t.description || ""}<br>${t.source}`;
  $("download").href = `/api/panel.csv?${query()}`;
  renderHonesty(payload);
  renderTable(payload);
  renderFooter(payload);
  if (payload.rows.length) select(payload.rows[0]);
}

function renderHonesty(payload) {
  const s = payload.summary || {};
  const grid = $("honesty-grid");
  $("honesty").hidden = false;
  const cards = [];
  if (s.candidates_scored) {
    cards.push(`<div class="card"><h3>Candidates scored</h3>
      <div class="big">${s.candidates_scored}</div>
      <p>Every ${payload.step} nt across the transcript, ${payload.design.length}-mer
      ${payload.design.wing5}-${payload.design.length - payload.design.wing5 - payload.design.wing3}-${payload.design.wing3} gapmer.</p></div>`);
    const pct = (100 * s.outside_measured_range) / s.candidates_scored;
    cards.push(`<div class="card flagged"><h3>Outside measured range</h3>
      <div class="big">${pct.toFixed(0)}%</div>
      <p>${s.outside_measured_range} of ${s.candidates_scored} predictions fall outside
      the measured label range (${s.measured_label_range.join("–")}). The model is
      being asked about molecules unlike those it was fitted on.</p></div>`);
    cards.push(`<div class="card flagged"><h3>Median novelty</h3>
      <div class="big">${fmt(s.median_novelty_percentile, 1)}<span style="font-size:13px">th pct</span></div>
      <p>${s.novelty_note}</p></div>`);
  }
  const agreement = s.heuristic_agreement || {};
  if (agreement.guanine_distance_from_3prime !== undefined) {
    cards.push(`<div class="card"><h3>Agrees with published rule</h3>
      <div class="big">ρ ${fmt(agreement.guanine_distance_from_3prime)}</div>
      <p>${agreement.note} Longest G-run ρ ${fmt(agreement.longest_g_run)}.</p></div>`);
  }
  grid.innerHTML = cards.join("");
}

function sequenceHtml(row, design) {
  const s = row.sequence;
  const core = s.length - design.wing5 - design.wing3;
  return (
    `<span class="wing">${s.slice(0, design.wing5)}</span>` +
    `<span class="core">${s.slice(design.wing5, design.wing5 + core)}</span>` +
    `<span class="wing">${s.slice(design.wing5 + core)}</span>`
  );
}

function renderTable(payload) {
  const endpoints = Object.keys(payload.endpoints.applicable);
  const head = ["#", "ASO 5'→3'", "pos"]
    .map((h) => `<th class="${h.includes("ASO") ? "seq" : ""}">${h}</th>`)
    .join("");
  const endpointHead = endpoints
    .map((e) => `<th>${ENDPOINT_LABELS[e] || e}</th><th>novelty</th>`)
    .join("");
  $("results-head").innerHTML =
    `<tr>${head}${endpointHead}<th>CpG</th><th>3'G</th><th>Grun</th><th>access</th></tr>`;

  $("results-body").innerHTML = payload.rows
    .map((row, index) => {
      const cells = endpoints
        .map((e) => {
          const p = row.predictions[e] || {};
          const novelty = p.novelty_percentile;
          const klass = novelty >= 99 ? "bad" : novelty >= 90 ? "warn" : "ok";
          return (
            `<td class="num">${fmt(p.value)} <span class="pill info">±${fmt(p.uncertainty)}</span></td>` +
            `<td class="num"><span class="pill ${klass}">${fmt(novelty, 0)}</span></td>`
          );
        })
        .join("");
      const g = row.guanine_distance_from_3prime;
      return `<tr data-index="${index}">
        <td class="num">${index + 1}</td>
        <td class="seq">${sequenceHtml(row, payload.design)}</td>
        <td class="num">${row.start}</td>
        ${cells}
        <td class="num">${row.cpg_count}</td>
        <td class="num">${g === null ? "none" : g}</td>
        <td class="num">${row.longest_g_run}</td>
        <td class="num">${fmt(row.target_accessibility)}</td>
      </tr>`;
    })
    .join("");

  Array.from($("results-body").querySelectorAll("tr")).forEach((tr) => {
    tr.addEventListener("click", () => select(payload.rows[Number(tr.dataset.index)], tr));
  });
}

function flagsFor(row, payload) {
  const flags = [];
  const g = row.guanine_distance_from_3prime;
  if (g !== null && g <= 2)
    flags.push(["bad", `guanine ${g} from 3' end — published neurotox association`]);
  if (row.longest_g_run >= 4) flags.push(["bad", `G-run of ${row.longest_g_run}`]);
  if (row.cpg_count >= 2) flags.push(["warn", `${row.cpg_count} CpG motifs`]);
  if (row.cpg_count === 0 && (g === null || g > 4)) flags.push(["ok", "no CpG, no 3' guanine"]);
  if (row.gc_fraction > 0.65) flags.push(["warn", `GC ${(100 * row.gc_fraction).toFixed(0)}%`]);
  if (row.gc_fraction < 0.3) flags.push(["warn", `GC ${(100 * row.gc_fraction).toFixed(0)}%`]);
  if (row.hairpin_dg !== null && row.hairpin_dg <= -3)
    flags.push(["warn", `self-structure ΔG ${fmt(row.hairpin_dg, 1)}`]);
  const primary = payload.primary_endpoint && row.predictions[payload.primary_endpoint];
  if (primary && primary.novelty_percentile >= 99)
    flags.push(["bad", "extrapolation: beyond the labelled neighbourhood"]);
  return flags;
}

function select(row, tr) {
  state.selected = row;
  const payload = state.payload;
  $("detail").hidden = false;
  Array.from($("results-body").querySelectorAll("tr")).forEach((node) =>
    node.classList.toggle("active", node === tr)
  );
  $("detail-title").textContent = `${payload.transcript.gene} : ${row.start}–${row.end}`;

  const rows = [
    ["ASO 5'→3'", sequenceHtml(row, payload.design), "mono"],
    ["Target window", row.target_window, "mono"],
    ["GC", `${(100 * row.gc_fraction).toFixed(0)}%`],
    ["CpG motifs", row.cpg_count],
    ["3' guanine distance", row.guanine_distance_from_3prime ?? "none"],
    ["Longest G run", row.longest_g_run],
    ["Self-structure ΔG", fmt(row.hairpin_dg, 1)],
    ["Target accessibility", fmt(row.target_accessibility)],
  ];
  Object.entries(row.predictions).forEach(([key, p]) => {
    const spec = payload.endpoints.applicable[key];
    rows.push([`${spec.title}`, `${fmt(p.value)} ± ${fmt(p.uncertainty)}`]);
    rows.push([`↳ units`, spec.units, "mono"]);
    rows.push([`↳ held-out r`, `${spec.held_out_r} (${spec.held_out_note})`, "mono"]);
  });
  rows.push(["HELM", row.helm, "mono"]);
  $("detail-facts").innerHTML = rows
    .map(([k, v, cls]) => `<dt>${k}</dt><dd class="${cls || ""}">${v}</dd>`)
    .join("");

  $("detail-flags").innerHTML = flagsFor(row, payload)
    .map(([k, text]) => `<span class="pill ${k}">${text}</span>`)
    .join("");

  const url = `/api/structure?sequence=${row.sequence}&chemistry=${row.chemistry}&title=${payload.transcript.gene}`;
  $("pdb-link").href = url;
  $("pdb-link").setAttribute("download", `${payload.transcript.gene}-${row.start}.pdb`);
  showStructure(url, row, payload.design);
}

async function showStructure(url, row, design) {
  const element = $("viewer");
  if (!window.$3Dmol) {
    element.innerHTML = '<p style="padding:10px;font-size:12px">3D viewer unavailable offline.</p>';
    return;
  }
  const pdb = await (await fetch(url)).text();
  if (!state.viewer) {
    state.viewer = window.$3Dmol.createViewer(element, { backgroundAlpha: 0 });
  }
  const viewer = state.viewer;
  viewer.clear();
  viewer.addModel(pdb, "pdb");
  // Chain B (the target RNA) recedes; chain A carries the chemistry colouring.
  viewer.setStyle({ chain: "B" }, { sphere: { radius: 0.5, color: "#9aa0a6", opacity: 0.55 } });
  viewer.addStyle({ chain: "B" }, { line: { color: "#9aa0a6", opacity: 0.4 } });
  const core = row.sequence.length - design.wing5 - design.wing3;
  viewer.setStyle({ chain: "A", resi: `1-${design.wing5}` },
    { sphere: { radius: 0.8, color: "#1f5fa9" }, stick: { radius: 0.18, color: "#1f5fa9" } });
  viewer.addStyle({ chain: "A", resi: `${design.wing5 + 1}-${design.wing5 + core}` },
    { sphere: { radius: 0.8, color: "#b3561d" }, stick: { radius: 0.18, color: "#b3561d" } });
  viewer.addStyle({ chain: "A", resi: `${design.wing5 + core + 1}-${row.sequence.length}` },
    { sphere: { radius: 0.8, color: "#1f5fa9" }, stick: { radius: 0.18, color: "#1f5fa9" } });
  // Highlight guanines in the 3' third: the published neurotoxicity association.
  const tail = [];
  for (let i = Math.floor((2 * row.sequence.length) / 3); i < row.sequence.length; i += 1) {
    if (row.sequence[i] === "G") tail.push(i + 1);
  }
  if (tail.length) {
    viewer.addStyle({ chain: "A", resi: tail.join(",") },
      { sphere: { radius: 1.15, color: "#a12d2d" } });
  }
  viewer.zoomTo();
  viewer.render();
}

window.addEventListener("DOMContentLoaded", () => {
  $("design-form").addEventListener("submit", run);
  $("sort").addEventListener("change", run);
  $("chemistry").addEventListener("change", () => {
    const moe = $("chemistry").value === "ps_moe_gapmer";
    $("chemistry-note").textContent = moe
      ? "Applies the MOE neurotox model; TLR models are withheld (fitted on 2'OMe)"
      : "Applies both TLR models; the neurotox model is withheld (fitted on 2'-MOE)";
  });
  run();
});

function renderFooter(payload) {
  $("non-claims").innerHTML = payload.non_claims.map((c) => `<li>${c}</li>`).join("");
  const withheld = Object.entries(payload.endpoints.not_applicable)
    .map(([k, v]) => `${v.title} (${v.reason})`)
    .join("; ");
  const missing = Object.values(payload.endpoints.not_modelled).join(" ");
  $("endpoints-note").textContent = `Withheld for this chemistry: ${withheld}. ${missing}`;
}
