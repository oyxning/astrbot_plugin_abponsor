/* ============================================================
   赞助计划页面 — 主逻辑
   — 通过 bridge.apiGet 调用后端 Python 插件代理 API
   — 使用 AstrBot Plugin Page Bridge 做国际化 / 上下文监听
   ============================================================ */

const bridge = window.AstrBotPluginPage;

// ── DOM 引用 ──
const $loading = document.getElementById("loading-overlay");
const $error = document.getElementById("error-banner");
const $main = document.getElementById("main-content");
const $periodTitle = document.getElementById("period-title");
const $periodBadge = document.getElementById("period-badge");
const $announcement = document.getElementById("announcement-text");
const $statRegistrant = document.getElementById("stat-registrant");
const $statAmount = document.getElementById("stat-amount");
const $statReviewer = document.getElementById("stat-reviewer");
const $btnVote = document.getElementById("btn-vote");
const $btnVotePlaceholder = document.getElementById("btn-vote-placeholder");
const $btnRegister = document.getElementById("btn-register");
const $btnSummary = document.getElementById("btn-summary");
const $historyList = document.getElementById("history-list");
const $historyCount = document.getElementById("history-count");
const $footerRefresh = document.getElementById("footer-refresh");
const $btnRefresh = document.getElementById("btn-refresh");

// ── 初始化 ──
async function init() {
  try {
    await bridge.ready();
    await loadData();
    bridge.onContext(() => loadData());
  } catch (err) {
    showError("插件初始化失败：" + err.message);
  }
}

// ── 数据加载（bridge 代理 → Python 后端 → 公司 API）──
async function loadData() {
  showLoading(true);
  hideError();

  try {
    const resp = await bridge.apiGet("sponsor-all", {});
    console.log("[赞助计划] bridge 返回:", JSON.stringify(resp));
    // 兼容 bridge 可能的多层包裹
    const data = resp.data || (resp.status === "ok" ? resp.data : null);
    if (data) {
      render(data);
    } else if (resp.code === 200 || resp.code === 0) {
      render(resp.data);
    } else {
      throw new Error(resp.message || resp.msg || "响应格式异常: " + JSON.stringify(resp).substring(0, 100));
    }
    updateRefreshTime();
  } catch (err) {
    showError("数据加载失败：" + err.message);
  } finally {
    showLoading(false);
  }
}

// ── 渲染 ──
function render(data) {
  showMain(true);

  const { current = {}, previousDevelopers = [] } = data;

  // 本期标题
  $periodTitle.textContent =
    bridge.t("pages.sponsor.period_title", `第 ${current.period || "—"} 期赞助计划`);

  // 状态徽标
  if (current.registrationEnabled) {
    $periodBadge.textContent = bridge.t("pages.sponsor.status_open", "报名中");
    $periodBadge.className = "badge badge-active";
  } else {
    $periodBadge.textContent = bridge.t("pages.sponsor.status_closed", "已截止");
    $periodBadge.className = "badge";
  }

  // 公告
  $announcement.textContent = current.announcement || "暂无公告";

  // 统计数据
  $statRegistrant.textContent = formatNumber(current.registrantCount);
  $statAmount.textContent = "¥" + formatNumber(current.sponsorAmount);
  $statReviewer.textContent = formatNumber(current.reviewerCount);

  // 投票入口：有 URL 显示按钮，无 URL 显示"暂未开放"
  if (current.voteUrl) {
    $btnVote.href = current.voteUrl;
    $btnVote.classList.remove("hidden");
    $btnVotePlaceholder.classList.add("hidden");
  } else {
    $btnVote.classList.add("hidden");
    $btnVotePlaceholder.classList.remove("hidden");
  }
  renderButton($btnRegister, current.registrationEnabled ? current.registrationUrl : null, "去报名");
  renderButton($btnSummary, current.summaryEnabled ? current.summaryUrl : null, "查看总表");

  // 往期开发者
  renderHistory(previousDevelopers);
}

function renderButton(el, url, label) {
  if (url) {
    el.href = url;
    el.textContent = label;
    el.classList.remove("hidden");
  } else {
    el.classList.add("hidden");
  }
}

function renderHistory(developers) {
  $historyList.innerHTML = "";
  $historyCount.textContent = `${developers.length} 位`;

  if (!developers || developers.length === 0) {
    $historyList.innerHTML = '<p class="empty-hint">暂无往期记录</p>';
    return;
  }

  developers.forEach(function (dev) {
    var item = document.createElement("div");
    item.className = "dev-item";
    item.innerHTML =
      '<div class="dev-info">' +
      '<span class="dev-name">' + escapeHtml(dev.name || "—") + '</span>' +
      '<span class="dev-meta">第 ' + (dev.period || "—") +
      ' 期 · ' + escapeHtml(dev.project || "—") + '</span>' +
      '</div>' +
      '<span class="dev-amount">¥' + formatNumber(dev.amount) + '</span>';
    $historyList.appendChild(item);
  });
}

// ── UI 辅助 ──
function showLoading(visible) {
  $loading.classList.toggle("hidden", !visible);
}

function showMain(visible) {
  $main.classList.toggle("hidden", !visible);
}

function showError(message) {
  $error.textContent = message;
  $error.classList.remove("hidden");
}

function hideError() {
  $error.classList.add("hidden");
}

function updateRefreshTime() {
  var now = new Date();
  $footerRefresh.textContent = "最后更新：" + now.toLocaleTimeString("zh-CN");
}

function formatNumber(val) {
  if (val == null) return "0";
  var num = Number(val);
  if (isNaN(num)) return "0";
  if (num >= 10000) {
    return (num / 10000).toFixed(1) + "万";
  }
  return num.toLocaleString("zh-CN");
}

function escapeHtml(str) {
  var div = document.createElement("div");
  div.textContent = str;
  return div.innerHTML;
}

// ── 事件绑定 ──
$btnRefresh.addEventListener("click", function (e) {
  e.preventDefault();
  loadData();
});

// ── 启动 ──
init();
