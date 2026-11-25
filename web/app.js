const qs = (selector) => document.querySelector(selector);
const formatNumber = (value) => new Intl.NumberFormat("en-US", {
  notation: "compact",
  maximumFractionDigits: 1,
}).format(value);

let report = null;
let uploadedCsv = null;

function showToast(message) {
  const toast = qs("#toast");
  toast.textContent = message;
  toast.classList.add("show");
  window.clearTimeout(showToast.timer);
  showToast.timer = window.setTimeout(() => toast.classList.remove("show"), 3200);
}

async function loadReport(platform = "All", csv = uploadedCsv) {
  const endpoint = csv === null
    ? `/api/analyze?platform=${encodeURIComponent(platform)}`
    : "/api/analyze";
  const options = csv === null
    ? { method: "GET" }
    : {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ csv, platform }),
    };

  try {
    const response = await fetch(endpoint, options);
    const data = await response.json();
    if (!response.ok) throw new Error(data.error || "Could not analyze this data");
    report = data;
    uploadedCsv = csv;
    render(data, platform);
    return true;
  } catch (error) {
    showToast(error instanceof Error ? error.message : "Could not analyze this data");
    return false;
  }
}

function render(data, selectedPlatform) {
  const summary = data.summary;
  qs("#avg-engagement").textContent = `${summary.average_engagement}%`;
  qs("#total-likes").textContent = formatNumber(summary.total_likes);
  qs("#total-comments").textContent = formatNumber(summary.total_comments);
  qs("#total-shares").textContent = formatNumber(summary.total_shares);
  qs("#total-followers").textContent = summary.followers === undefined
    ? "—"
    : formatNumber(summary.followers);
  renderPlatformOptions(data.available_platforms || [], selectedPlatform);
  renderDateRange(data.timeline);
  renderSpark(data.timeline);
  renderChart(data.timeline);
  renderContent(data.content_types);
  renderPosts(data.top_posts);
  renderRecommendations(data.recommendations || []);
  renderBestTime(data.best_time);
  qs("#updated-at").textContent = `${uploadedCsv === null ? "SAMPLE DATA" : "IMPORTED CSV"} · ${summary.posts} POSTS ANALYZED`;
}

function renderPlatformOptions(platforms, selectedPlatform) {
  const select = qs("#platform-filter");
  select.replaceChildren(new Option("All platforms", "All"));
  platforms.forEach((platform) => select.add(new Option(platform, platform)));
  select.value = platforms.some((platform) => platform.toLowerCase() === selectedPlatform.toLowerCase())
    ? platforms.find((platform) => platform.toLowerCase() === selectedPlatform.toLowerCase())
    : "All";
}

function renderDateRange(items) {
  const range = qs("#date-range");
  if (!items.length) {
    range.textContent = "No dates";
    return;
  }
  const first = items[0].date;
  const last = items[items.length - 1].date;
  const formatDate = (value, includeYear) => new Intl.DateTimeFormat("en-US", {
    month: "short",
    day: "numeric",
    ...(includeYear ? { year: "numeric" } : {}),
  }).format(new Date(`${value}T12:00:00`));
  const sameYear = first.slice(0, 4) === last.slice(0, 4);
  range.textContent = first === last
    ? formatDate(first, true)
    : `${formatDate(first, !sameYear)} — ${formatDate(last, true)}`;
}

function renderSpark(items) {
  const mount = qs("#engagement-spark");
  const max = Math.max(...items.map((item) => item.engagement), 1);
  mount.replaceChildren(...items.slice(-14).map((item) => {
    const bar = document.createElement("i");
    bar.style.height = `${Math.max(7, item.engagement / max * 38)}px`;
    bar.title = `${item.date}: ${item.engagement}%`;
    return bar;
  }));
}

function renderChart(items) {
  const svg = qs("#timeline-chart");
  if (!items.length) {
    svg.replaceChildren();
    return;
  }

  const width = 720;
  const height = 250;
  const padX = 18;
  const chartBottom = height - 24;
  const maxValue = Math.max(...items.map((item) => item.engagement), 1);
  const max = Math.max(1, Math.ceil(maxValue / 5) * 5);
  const points = items.map((item, index) => {
    const x = items.length === 1
      ? width / 2
      : padX + index * ((width - padX * 2) / (items.length - 1));
    const y = chartBottom - (item.engagement / max) * (chartBottom - 18);
    return { x, y, value: item.engagement, date: item.date };
  });
  const line = points.map((point, index) => `${index ? "L" : "M"} ${point.x} ${point.y}`).join(" ");
  const area = `${line} L ${points[points.length - 1].x} ${chartBottom} L ${points[0].x} ${chartBottom} Z`;
  const ticks = Array.from({ length: 5 }, (_, index) => max * (4 - index) / 4);
  qs(".chart-y").replaceChildren(...ticks.map((value) => {
    const label = document.createElement("span");
    label.textContent = `${Number.isInteger(value) ? value : value.toFixed(1)}%`;
    return label;
  }));

  svg.setAttribute("aria-label", `Engagement rate over ${items.length} posts, from ${items[0].date} to ${items[items.length - 1].date}`);
  const dots = points.map((point) => (
    `<circle cx="${point.x}" cy="${point.y}" r="4" fill="#090c12" stroke="#b9f04a" stroke-width="2"><title>${point.date}: ${point.value}%</title></circle>`
  )).join("");
  svg.innerHTML = `
    <defs><linearGradient id="area" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#b9f04a" stop-opacity=".22"/><stop offset="1" stop-color="#b9f04a" stop-opacity="0"/></linearGradient></defs>
    <g stroke="rgba(192,207,229,.07)" stroke-width="1">${ticks.map((_, index) => `<line x1="0" y1="${18 + index * ((chartBottom - 18) / 4)}" x2="${width}" y2="${18 + index * ((chartBottom - 18) / 4)}"/>`).join("")}</g>
    <path d="${area}" fill="url(#area)"/><path d="${line}" fill="none" stroke="#b9f04a" stroke-width="2.5"/>
    ${dots}`;
}

function renderContent(items) {
  const mount = qs("#content-list");
  if (!items.length) {
    mount.textContent = "No content types to display.";
    return;
  }
  const max = Math.max(...items.map((item) => item.engagement), 1);
  mount.innerHTML = items.map((item) => `
    <div class="content-row">
      <div class="content-meta"><span>${escapeHtml(item.name)}</span><span>${item.engagement}%</span></div>
      <div class="content-bar"><i style="width:${Math.max(8, item.engagement / max * 100)}%"></i></div>
    </div>`).join("");
}

function renderPosts(posts) {
  const mount = qs("#posts-list");
  if (!posts.length) {
    mount.textContent = "No posts to display.";
    return;
  }
  mount.innerHTML = posts.map((post, index) => `
    <div class="post-row" role="row">
      <div class="post-main"><span class="post-thumb" aria-hidden="true">${["◇", "▥", "▶", "◎", "↗"][index % 5]}</span><div><strong>${escapeHtml(post.caption)}</strong><small>${escapeHtml(post.content_type)} · ${escapeHtml(post.date)}</small></div></div>
      <span><span class="platform-pill">${escapeHtml(post.platform)}</span></span>
      <span>${formatNumber(post.likes)}</span>
      <span>${formatNumber(post.comments)}</span>
      <span>${formatNumber(post.shares)}</span>
      <strong class="engagement-value">${post.engagement}%</strong>
    </div>`).join("");
}

function renderRecommendations(items) {
    const mount = qs("#recommendation-list");
    if (!items.length) {
      mount.textContent = "Recommendations are not available for this report.";
      return;
    }
    mount.replaceChildren(...items.map((item) => {
      const row = document.createElement("article");
      row.className = "recommendation-item";
      const title = document.createElement("strong");
      title.textContent = item.title;
      const detail = document.createElement("p");
      detail.textContent = item.detail;
      row.append(title, detail);
      return row;
    }));
}

function renderBestTime(bestTime) {
    qs("#best-time").textContent = bestTime?.label || "Add post times";
    qs("#best-time-detail").textContent = bestTime
      ? `${bestTime.engagement}% average engagement across ${bestTime.posts} post(s). Treat this as a test, not a guarantee.`
      : "Import a CSV with a time column to find your strongest hour.";
}

function escapeHtml(value) {
  const div = document.createElement("div");
  div.textContent = String(value);
  return div.innerHTML;
}

function csvCell(value) {
  let text = String(value);
  if (/^[=+\-@\t\r]/.test(text)) text = `'${text}`;
  return `"${text.replaceAll('"', '""')}"`;
}

qs("#platform-filter").addEventListener("change", (event) => loadReport(event.target.value));
qs("#csv-file").addEventListener("change", async (event) => {
  const file = event.target.files[0];
  if (!file) return;
  if (file.size > 2 * 1024 * 1024) {
    showToast("CSV must be no larger than 2 MB");
    event.target.value = "";
    return;
  }
  try {
    const csv = await file.text();
    if (await loadReport(qs("#platform-filter").value, csv)) {
      showToast(`${file.name} imported`);
    }
  } catch {
    showToast("Could not read the selected file");
  } finally {
    event.target.value = "";
  }
});
qs("#sidebar-upload").addEventListener("click", () => qs("#csv-file").click());
qs("#header-upload").addEventListener("click", () => qs("#csv-file").click());
qs("#import-account").addEventListener("click", () => qs("#csv-file").click());
qs("#profile-form").addEventListener("submit", (event) => {
  event.preventDefault();
  const status = qs("#account-status");
  const link = qs("#profile-link");
  const supportedHosts = [
    ["instagram.com", "Instagram"],
    ["tiktok.com", "TikTok"],
    ["linkedin.com", "LinkedIn"],
    ["x.com", "X"],
    ["twitter.com", "X"],
    ["youtube.com", "YouTube"],
    ["youtu.be", "YouTube"],
    ["facebook.com", "Facebook"],
    ["threads.net", "Threads"],
  ];

  try {
    const profile = new URL(qs("#profile-url").value.trim());
    const platform = supportedHosts.find(([domain]) => (
      profile.hostname === domain || profile.hostname.endsWith(`.${domain}`)
    ));
    if (profile.protocol !== "https:" || profile.username || profile.password || !platform) {
      throw new Error("Use an HTTPS profile link from Instagram, TikTok, LinkedIn, X, YouTube, Facebook, or Threads.");
    }

    link.href = profile.href;
    link.hidden = false;
    status.textContent = `${platform[1]} link recognized. Import your account export to see its real analytics; Social Pulse does not scrape profiles.`;
    const availablePlatform = report?.available_platforms?.find(
      (name) => name.toLowerCase() === platform[1].toLowerCase(),
    );
    if (availablePlatform) {
      qs("#platform-filter").value = availablePlatform;
      loadReport(availablePlatform);
    }
  } catch (error) {
    link.hidden = true;
    status.textContent = error instanceof Error ? error.message : "Enter a supported HTTPS profile link.";
  }
});
qs("#theme-button").addEventListener("click", (event) => {
  const enabled = document.body.classList.toggle("light");
  event.currentTarget.setAttribute("aria-pressed", String(enabled));
});
qs("#download-button").addEventListener("click", () => {
  if (!report) return;
  const rows = [["Post", "Platform", "Type", "Date", "Likes", "Comments", "Shares", "Engagement rate"]];
  report.top_posts.forEach((post) => rows.push([
    post.caption,
    post.platform,
    post.content_type,
    post.date,
    post.likes,
    post.comments,
    post.shares,
    post.engagement,
  ]));
  const csv = rows.map((row) => row.map(csvCell).join(",")).join("\r\n");
  const url = URL.createObjectURL(new Blob([csv], { type: "text/csv;charset=utf-8" }));
  const link = document.createElement("a");
  link.href = url;
  link.download = "social-pulse-top-posts.csv";
  link.click();
  window.setTimeout(() => URL.revokeObjectURL(url), 1000);
  showToast("Top posts exported");
});

document.querySelectorAll(".nav-item").forEach((item) => item.addEventListener("click", () => {
  document.querySelectorAll(".nav-item").forEach((link) => {
    link.classList.remove("active");
    link.removeAttribute("aria-current");
  });
  item.classList.add("active");
  item.setAttribute("aria-current", "page");
}));

loadReport();
