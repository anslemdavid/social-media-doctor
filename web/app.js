const qs = (selector) => document.querySelector(selector);
const formatNumber = (value) => new Intl.NumberFormat("en-US", { notation: "compact", maximumFractionDigits: 1 }).format(value);

let report = null;
let uploadedCsv = null;

function showToast(message) {
  const toast = qs("#toast");
  toast.textContent = message;
  toast.classList.add("show");
  window.clearTimeout(showToast.timer);
  showToast.timer = window.setTimeout(() => toast.classList.remove("show"), 2600);
}

async function loadReport(platform = "All") {
  const endpoint = uploadedCsv ? "/api/analyze" : `/api/analyze?platform=${encodeURIComponent(platform)}`;
  const options = uploadedCsv
    ? { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ csv: uploadedCsv, platform }) }
    : { method: "GET" };
  try {
    const response = await fetch(endpoint, options);
    const data = await response.json();
    if (!response.ok) throw new Error(data.error || "Could not analyze this data");
    report = data;
    render(report);
  } catch (error) {
    showToast(error.message);
  }
}

function render(data) {
  const summary = data.summary;
  qs("#avg-engagement").textContent = `${summary.average_engagement}%`;
  qs("#total-likes").textContent = formatNumber(summary.total_likes);
  qs("#total-comments").textContent = formatNumber(summary.total_comments);
  qs("#total-shares").textContent = formatNumber(summary.total_shares);
  renderSpark(data.timeline);
  renderChart(data.timeline);
  renderContent(data.content_types);
  renderPosts(data.top_posts);
  qs("#updated-at").textContent = `LOCAL DEMO · ${summary.posts} POSTS ANALYZED`;
}

function renderSpark(items) {
  const mount = qs("#engagement-spark");
  mount.innerHTML = items.slice(-14).map((item) => {
    const height = Math.max(7, Math.min(38, item.engagement * 1.8));
    return `<i style="height:${height}px"></i>`;
  }).join("");
}

function renderChart(items) {
  const svg = qs("#timeline-chart");
  const width = 720;
  const height = 250;
  const padX = 18;
  const max = 40;
  const points = items.slice(-12).map((item, index) => {
    const x = padX + index * ((width - padX * 2) / Math.max(items.length - 1, 11));
    const y = height - 18 - (Math.min(item.engagement, max) / max) * (height - 36);
    return { x, y, value: item.engagement };
  });
  if (!points.length) { svg.innerHTML = ""; return; }
  const line = points.map((point, index) => `${index ? "L" : "M"} ${point.x} ${point.y}`).join(" ");
  const area = `${line} L ${points[points.length - 1].x} ${height - 18} L ${points[0].x} ${height - 18} Z`;
  const dots = points.map((point) => `<circle cx="${point.x}" cy="${point.y}" r="4" fill="#090c12" stroke="#b9f04a" stroke-width="2"><title>${point.value}%</title></circle>`).join("");
  svg.innerHTML = `
    <defs><linearGradient id="area" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#b9f04a" stop-opacity=".22"/><stop offset="1" stop-color="#b9f04a" stop-opacity="0"/></linearGradient></defs>
    <g stroke="rgba(192,207,229,.07)" stroke-width="1">${[18,67,116,165,214].map(y => `<line x1="0" y1="${y}" x2="720" y2="${y}"/>`).join("")}</g>
    <path d="${area}" fill="url(#area)"/><path d="${line}" fill="none" stroke="#b9f04a" stroke-width="2.5"/>
    ${dots}`;
}

function renderContent(items) {
  const max = Math.max(...items.map((item) => item.engagement), 1);
  qs("#content-list").innerHTML = items.map((item) => `
    <div class="content-row">
      <div class="content-meta"><span>${item.name}</span><span>${item.engagement}%</span></div>
      <div class="content-bar"><i style="width:${Math.max(8, item.engagement / max * 100)}%"></i></div>
    </div>`).join("");
}

function renderPosts(posts) {
  qs("#posts-list").innerHTML = posts.map((post, index) => `
    <div class="post-row" role="row">
      <div class="post-main"><span class="post-thumb">${["◇","▥","▶","◎","↗"][index % 5]}</span><div><strong>${escapeHtml(post.caption)}</strong><small>${post.content_type} · ${post.date}</small></div></div>
      <span><span class="platform-pill">${escapeHtml(post.platform)}</span></span>
      <span>${formatNumber(post.likes)}</span>
      <span>${formatNumber(post.comments)}</span>
      <strong class="engagement-value">${post.engagement}%</strong>
    </div>`).join("");
}

function escapeHtml(value) {
  const div = document.createElement("div");
  div.textContent = value;
  return div.innerHTML;
}

qs("#platform-filter").addEventListener("change", (event) => loadReport(event.target.value));
qs("#csv-file").addEventListener("change", async (event) => {
  const file = event.target.files[0];
  if (!file) return;
  uploadedCsv = await file.text();
  await loadReport(qs("#platform-filter").value);
  showToast(`${file.name} imported`);
});
qs("#sidebar-upload").addEventListener("click", () => qs("#csv-file").click());
qs("#theme-button").addEventListener("click", () => document.body.classList.toggle("light"));
qs("#download-button").addEventListener("click", () => {
  if (!report) return;
  const rows = [["Post","Platform","Type","Likes","Comments","Shares","Engagement"]];
  report.top_posts.forEach((post) => rows.push([post.caption,post.platform,post.content_type,post.likes,post.comments,post.shares,post.engagement]));
  const csv = rows.map((row) => row.map((cell) => `"${String(cell).replaceAll('"','""')}"`).join(",")).join("\n");
  const link = document.createElement("a");
  link.href = URL.createObjectURL(new Blob([csv], { type: "text/csv" }));
  link.download = "social-pulse-report.csv";
  link.click();
  URL.revokeObjectURL(link.href);
  showToast("Report exported");
});

document.querySelectorAll(".nav-item").forEach((item) => item.addEventListener("click", () => {
  document.querySelectorAll(".nav-item").forEach((link) => link.classList.remove("active"));
  item.classList.add("active");
}));

loadReport();
