const LOADER_MSGS = [
  "Collecting signals from global news sources…",
  "Querying ReliefWeb and Reddit…",
  "Parsing Google News RSS…",
  "Sending signals to the AI for analysis…",
  "Building your risk report…",
];

let loaderInterval = null;

function startLoader() {
  let i = 0;
  document.getElementById("loader-msg").textContent = LOADER_MSGS[0];
  loaderInterval = setInterval(() => {
    i = (i + 1) % LOADER_MSGS.length;
    document.getElementById("loader-msg").textContent = LOADER_MSGS[i];
  }, 2800);
}

function stopLoader() {
  clearInterval(loaderInterval);
}

function levelColor(level) {
  return { low: "#22c55e", medium: "#f59e0b", high: "#f97316", critical: "#ef4444" }[level] || "#8a8fa8";
}

function renderScoreRing(score, level) {
  const r = 28, cx = 36, cy = 36;
  const circ = 2 * Math.PI * r;
  const dash = (score / 100) * circ;
  const color = levelColor(level);
  return `
    <div class="score-ring">
      <svg width="72" height="72" viewBox="0 0 72 72">
        <circle cx="${cx}" cy="${cy}" r="${r}" fill="none" stroke="rgba(255,255,255,0.06)" stroke-width="5"/>
        <circle cx="${cx}" cy="${cy}" r="${r}" fill="none" stroke="${color}" stroke-width="5"
          stroke-dasharray="${dash} ${circ}" stroke-linecap="round"/>
      </svg>
      <div class="score-val" style="color:${color}">${score}</div>
    </div>`;
}

function renderReport(data) {
  const sources = (data.key_sources || []).map(s => {
    const display = s.length > 50 ? s.slice(0, 50) + "…" : s;
    return `<li><a href="${s}" target="_blank" rel="noopener noreferrer">${display}</a></li>`;
  }).join("");

  const categories = (data.categories || []).map(cat => `
    <div class="category-card">
      <h3>
        <span>${cat.name}</span>
        <span class="badge ${cat.level}">${cat.level}</span>
      </h3>
      <div class="progress-bar">
        <div class="progress-fill ${cat.level}" style="width:${cat.score}%"></div>
      </div>
      <p class="category-summary">${cat.summary}</p>
      <ul class="signals-list">
        ${(cat.signals || []).map(s => `<li>${s}</li>`).join("")}
      </ul>
    </div>
  `).join("");

  return `
    <div class="report-header">
      <h2>${data.city}</h2>
      <div class="score-row">
        ${renderScoreRing(data.overall_score, data.overall_level)}
        <div>
          <span class="badge ${data.overall_level}">${data.overall_level} risk</span>
          <p class="exec-summary" style="margin-top:8px">${data.executive_summary}</p>
        </div>
      </div>
      <p class="meta">${data.signals_collected} signals collected · ${new Date().toLocaleString()}</p>
    </div>

    <div class="categories-grid">${categories}</div>

    ${sources ? `
    <div class="sources-card">
      <h3>Key sources</h3>
      <ul class="sources-list">${sources}</ul>
    </div>` : ""}

    <p class="disclaimer">${data.disclaimer}</p>
  `;
}

async function assess() {
  const city = document.getElementById("city-input").value.trim();
  if (!city) return;

  const btn = document.getElementById("assess-btn");
  const loader = document.getElementById("loader");
  const report = document.getElementById("report");
  const errorBox = document.getElementById("error-box");

  btn.disabled = true;
  errorBox.style.display = "none";
  loader.style.display = "flex";
  report.style.display = "none";
  startLoader();

  try {
    const res = await fetch("/api/assess", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ city }),
    });

    const data = await res.json();

    if (!res.ok) {
      throw new Error(data.detail || "Server error");
    }

    report.innerHTML = renderReport(data);
    report.style.display = "flex";
  } catch (err) {
    errorBox.textContent = "Error: " + err.message;
    errorBox.style.display = "block";
  } finally {
    stopLoader();
    loader.style.display = "none";
    btn.disabled = false;
  }
}

document.getElementById("city-input").addEventListener("keydown", e => {
  if (e.key === "Enter") assess();
});
