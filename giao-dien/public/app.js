const defaultApiBase = window.location.port === "5500"
  ? "http://127.0.0.1:8000"
  : window.location.origin;

const isWebServiceMode = window.location.port !== "5500";
if (isWebServiceMode) {
  document.body.classList.add("webservice-mode");
}

const state = {
  apiBase: localStorage.getItem("adsApiBase") || defaultApiBase,
  charts: {},
  authToken: localStorage.getItem("adsAuthToken") || "",
  authUser: localStorage.getItem("adsAuthUser") || "",
  authRole: localStorage.getItem("adsAuthRole") || "guest",
};

const el = {
  apiBase: document.getElementById("apiBase"),
  btnApplyApi: document.getElementById("btnApplyApi"),
  btnApplyFilters: document.getElementById("btnApplyFilters"),
  btnResetFilters: document.getElementById("btnResetFilters"),
  btnUploadCsv: document.getElementById("btnUploadCsv"),
  btnLoadCampaignChart: document.getElementById("btnLoadCampaignChart"),
  btnLoadRecommendations: document.getElementById("btnLoadRecommendations"),
  btnExportSegmentsCsv: document.getElementById("btnExportSegmentsCsv"),
  btnExportBudgetCsv: document.getElementById("btnExportBudgetCsv"),
  btnLoadExperiments: document.getElementById("btnLoadExperiments"),
  btnExportExperimentMetricsCsv: document.getElementById("btnExportExperimentMetricsCsv"),
  btnExportTopFeaturesCsv: document.getElementById("btnExportTopFeaturesCsv"),
  btnLoadDefenseSummary: document.getElementById("btnLoadDefenseSummary"),
  btnSimulateBudget: document.getElementById("btnSimulateBudget"),
  btnRefreshHealth: document.getElementById("btnRefreshHealth"),
  btnLoadUploadLogs: document.getElementById("btnLoadUploadLogs"),
  fCampaign: document.getElementById("fCampaign"),
  fAge: document.getElementById("fAge"),
  fGender: document.getElementById("fGender"),
  fQuality: document.getElementById("fQuality"),
  fMinCtr: document.getElementById("fMinCtr"),
  fMaxCpa: document.getElementById("fMaxCpa"),
  kpis: document.getElementById("kpis"),
  uploadCsvFile: document.getElementById("uploadCsvFile"),
  uploadMeta: document.getElementById("uploadMeta"),
  campaignGroupBy: document.getElementById("campaignGroupBy"),
  recommendationRows: document.getElementById("recommendationRows"),
  bTotalBudget: document.getElementById("bTotalBudget"),
  bTopN: document.getElementById("bTopN"),
  budgetRows: document.getElementById("budgetRows"),
  budgetMeta: document.getElementById("budgetMeta"),
  segmentExplain: document.getElementById("segmentExplain"),
  experimentMeta: document.getElementById("experimentMeta"),
  experimentDecision: document.getElementById("experimentDecision"),
  experimentObjective: document.getElementById("experimentObjective"),
  featureRows: document.getElementById("featureRows"),
  modelEvidenceAssumption: document.getElementById("modelEvidenceAssumption"),
  confusionRows: document.getElementById("confusionRows"),
  thresholdRows: document.getElementById("thresholdRows"),
  thresholdRecommendation: document.getElementById("thresholdRecommendation"),
  defenseHeadline: document.getElementById("defenseHeadline"),
  defenseWinnerRows: document.getElementById("defenseWinnerRows"),
  defensePoints: document.getElementById("defensePoints"),
  toast: document.getElementById("toast"),
  authForm: document.getElementById("authForm"),
  authStatus: document.getElementById("authStatus"),
  authUserInfo: document.getElementById("authUserInfo"),
  authRoleBadge: document.getElementById("authRoleBadge"),
  authUsername: document.getElementById("authUsername"),
  authPassword: document.getElementById("authPassword"),
  btnLogin: document.getElementById("btnLogin"),
  btnLogout: document.getElementById("btnLogout"),
  systemStatusBadge: document.getElementById("systemStatusBadge"),
  systemSummary: document.getElementById("systemSummary"),
  systemAssetRows: document.getElementById("systemAssetRows"),
  pipelineTimeline: document.getElementById("pipelineTimeline"),
  pipelineNote: document.getElementById("pipelineNote"),
  uploadLogsMeta: document.getElementById("uploadLogsMeta"),
  uploadLogsRows: document.getElementById("uploadLogsRows"),
};

function showToast(message) {
  el.toast.textContent = message;
  el.toast.classList.add("show");
  setTimeout(() => el.toast.classList.remove("show"), 2200);
}

function updateAuthUI() {
  if (state.authToken) {
    el.authForm.classList.add("hidden");
    el.authStatus.classList.remove("hidden");
    el.authUserInfo.textContent = state.authUser || "–";
    el.authRoleBadge.textContent = state.authRole || "guest";
    el.authRoleBadge.className = `role-badge role-${state.authRole || "guest"}`;
  } else {
    el.authForm.classList.remove("hidden");
    el.authStatus.classList.add("hidden");
  }
}

function shortenLabel(label, maxLength = 14) {
  const text = String(label ?? "");
  if (text.length <= maxLength) {
    return text;
  }
  return `${text.slice(0, maxLength - 1)}…`;
}

function withUiAction(action, errorMessage) {
  return async (event) => {
    const trigger = event?.currentTarget;
    const canLock = trigger && typeof trigger.disabled === "boolean";
    if (canLock) {
      trigger.disabled = true;
      trigger.classList.add("is-loading");
    }
    try {
      await action();
    } catch (err) {
      console.error(err);
      const message = err && typeof err.message === "string" && err.message.trim()
        ? err.message.trim()
        : (errorMessage || "Action failed");
      showToast(message);
    } finally {
      if (canLock) {
        trigger.disabled = false;
        trigger.classList.remove("is-loading");
      }
    }
  };
}

function number(v, digits = 2) {
  if (v === null || v === undefined || Number.isNaN(Number(v))) return "-";
  return Number(v).toLocaleString("en-US", { maximumFractionDigits: digits });
}

function buildQuery(params) {
  const search = new URLSearchParams();
  Object.entries(params).forEach(([k, v]) => {
    if (v !== "" && v !== null && v !== undefined) search.set(k, v);
  });
  return search.toString();
}

function authHeaders(requireAuth = false) {
  if (!requireAuth) return {};
  if (!state.authToken) {
    throw new Error("Chưa đăng nhập. Hãy đăng nhập analyst/admin để dùng tính năng này.");
  }
  return { Authorization: `Bearer ${state.authToken}` };
}

async function ensureLogin() {
  if (state.authToken) return;
  el.authUsername.focus();
  const authContainer = el.authUsername.closest(".topnav-right") || el.authUsername;
  authContainer.scrollIntoView({ behavior: "smooth", block: "center" });
  throw new Error("Vui lòng đăng nhập (analyst hoặc admin) để dùng tính năng này.");
}

function ensureRole(allowedRoles) {
  if (!Array.isArray(allowedRoles) || !allowedRoles.length) return;
  if (!allowedRoles.includes(state.authRole)) {
    throw new Error(`Tài khoản '${state.authRole || "guest"}' không có quyền thực hiện thao tác này.`);
  }
}

function parseApiErrorMessage(rawText, status) {
  const fallback = rawText && rawText.trim() ? rawText.trim() : `Yêu cầu thất bại (HTTP ${status})`;
  try {
    const parsed = JSON.parse(rawText);
    if (parsed && typeof parsed.detail === "string" && parsed.detail.trim()) {
      const detail = parsed.detail.trim();
      if (detail.includes("Forbidden for role")) {
        const roleMatch = detail.match(/'([^']+)'/);
        const role = roleMatch && roleMatch[1] ? roleMatch[1] : "guest";
        return `Tài khoản '${role}' không có quyền cho chức năng này.`;
      }
      if (detail.includes("Unauthorized") || detail.includes("Missing Authorization")) {
        return "Bạn chưa đăng nhập hoặc phiên đã hết hạn. Vui lòng đăng nhập lại.";
      }
      return detail;
    }
  } catch (_) {
    // Ignore JSON parse errors and use fallback text.
  }
  return fallback;
}

function formatActionLabel(action) {
  const mapping = {
    increase_budget: "Tăng ngân sách",
    keep_and_test: "Giữ và thử nghiệm",
    reduce_budget: "Giảm ngân sách",
  };
  return mapping[action] || action || "-";
}

function formatWinnerName(name) {
  if (name === "rule_baseline") return "Rule baseline";
  if (name === "logistic_regression") return "Logistic regression";
  return name || "-";
}

function formatObjectiveLabel(name) {
  const mapping = {
    balanced: "Cân bằng tổng thể",
    precision: "Ưu tiên Precision",
    recall: "Ưu tiên Recall",
    auc: "Ưu tiên ROC AUC",
  };
  return mapping[name] || name || "-";
}

function formatAssetLabel(key) {
  const mapping = {
    scored_ads_csv: "Dữ liệu scored ads",
    budget_recommendations_csv: "Dữ liệu khuyến nghị ngân sách",
    model_metrics_json: "Báo cáo metrics mô hình",
    top_features_csv: "Bảng top đặc trưng",
    conversion_model_joblib: "Model artifact (.joblib)",
  };
  return mapping[key] || key;
}

function formatDateTime(value) {
  if (!value) return "-";
  const dt = new Date(value);
  if (Number.isNaN(dt.getTime())) return value;
  return dt.toLocaleString("vi-VN", { hour12: false });
}

function formatAgeMinutes(value) {
  if (value === null || value === undefined || Number.isNaN(Number(value))) return "-";
  const minutes = Number(value);
  if (minutes < 60) return `${number(minutes, 1)} phút`;
  if (minutes < 1440) return `${number(minutes / 60, 1)} giờ`;
  return `${number(minutes / 1440, 1)} ngày`;
}

function renderHealthBadge(ok) {
  if (ok) return '<span class="status-chip status-ok">Sẵn sàng</span>';
  return '<span class="status-chip status-bad">Thiếu dữ liệu</span>';
}

function renderPipelineStep(label, ok, detail) {
  const cls = ok ? "step-ok" : "step-pending";
  const icon = ok ? "✓" : "…";
  return `
    <div class="pipeline-step ${cls}">
      <span class="pipeline-dot">${icon}</span>
      <div class="pipeline-text">
        <p class="pipeline-label">${label}</p>
        <p class="pipeline-detail">${detail}</p>
      </div>
    </div>
  `;
}

function renderPipelineTimeline(health) {
  const assets = health?.data_assets || {};
  const apiOk = health?.status === "ok";
  const dbOk = !!health?.postgres_ready;
  const scoredOk = !!assets.scored_ads_csv?.exists;
  const recOk = !!assets.budget_recommendations_csv?.exists;
  const modelOk = !!assets.conversion_model_joblib?.exists && !!assets.model_metrics_json?.exists;

  const steps = [
    renderPipelineStep("API service", apiOk, apiOk ? "Đang phản hồi /health" : "Không phản hồi"),
    renderPipelineStep("PostgreSQL", dbOk, dbOk ? "Kết nối sẵn sàng" : "Chưa sẵn sàng"),
    renderPipelineStep("Spark xử lý chất lượng", scoredOk, scoredOk ? "Có output ad_quality" : "Thiếu output"),
    renderPipelineStep("Spark khuyến nghị", recOk, recOk ? "Có output budget_recommendations" : "Thiếu output"),
    renderPipelineStep("Mô hình và metrics", modelOk, modelOk ? "Artifact đầy đủ" : "Thiếu model/metrics"),
  ];

  el.pipelineTimeline.innerHTML = steps.join("");
}

async function loadUploadLogs() {
  if (!state.authToken) {
    el.uploadLogsMeta.textContent = "Đăng nhập admin để xem nhật ký upload dữ liệu.";
    el.uploadLogsRows.innerHTML = "";
    return;
  }

  if (state.authRole !== "admin") {
    el.uploadLogsMeta.textContent = "Bạn đang đăng nhập nhưng không có quyền admin để xem nhật ký upload.";
    el.uploadLogsRows.innerHTML = "";
    return;
  }

  const data = await apiGet("/api/data/upload-logs", { page: 1, page_size: 10 }, true);
  el.uploadLogsMeta.textContent = `Tổng log: ${number(data.total || 0, 0)} | Hiển thị: ${number((data.items || []).length, 0)} bản ghi mới nhất`;

  el.uploadLogsRows.innerHTML = (data.items || [])
    .map(
      (item, i) => `<tr>
        <td>${i + 1}</td>
        <td>${formatDateTime(item.uploaded_at)}</td>
        <td>${item.file_name || "-"}</td>
        <td>${number(item.scored_rows, 0)}</td>
        <td>${number(item.segment_rows, 0)}</td>
        <td>${item.uploader_name || "-"}</td>
        <td>${item.uploader_role || "-"}</td>
      </tr>`
    )
    .join("");
}

async function loadSystemHealth() {
  const data = await apiGet("/health");
  const isApiOk = data.status === "ok";
  const isDbOk = !!data.postgres_ready;
  const isDataReady = !!data.all_required_assets_ready;
  const allOk = isApiOk && isDbOk && isDataReady;

  el.systemStatusBadge.className = `status-chip ${allOk ? "status-ok" : "status-bad"}`;
  el.systemStatusBadge.textContent = allOk ? "Sẵn sàng demo" : "Cần kiểm tra";

  el.systemSummary.textContent = `API: ${isApiOk ? "Ổn định" : "Lỗi"} | PostgreSQL: ${isDbOk ? "Sẵn sàng" : "Chưa sẵn sàng"} | Dữ liệu/Model: ${isDataReady ? "Đầy đủ" : "Thiếu"}`;
  el.pipelineNote.textContent = `Cập nhật lúc: ${formatDateTime(new Date().toISOString())}`;
  renderPipelineTimeline(data);

  const assets = Object.entries(data.data_assets || {});
  el.systemAssetRows.innerHTML = assets
    .map(([key, item], i) => {
      const status = renderHealthBadge(!!item?.exists);
      const modified = formatDateTime(item?.last_modified_utc);
      const age = formatAgeMinutes(item?.age_minutes);
      return `<tr>
        <td>${i + 1}</td>
        <td>${formatAssetLabel(key)}</td>
        <td>${status}</td>
        <td>${modified}</td>
        <td>${age}</td>
      </tr>`;
    })
    .join("");
}

async function apiGet(path, params = {}, requireAuth = false) {
  const query = buildQuery(params);
  const url = `${state.apiBase}${path}${query ? `?${query}` : ""}`;
  const res = await fetch(url, { headers: authHeaders(requireAuth) });
  if (!res.ok) {
    const txt = await res.text();
    throw new Error(parseApiErrorMessage(txt, res.status));
  }
  return res.json();
}

async function apiUpload(path, file, requireAuth = false) {
  const url = `${state.apiBase}${path}`;
  const formData = new FormData();
  formData.append("file", file);

  const res = await fetch(url, {
    method: "POST",
    headers: authHeaders(requireAuth),
    body: formData,
  });

  if (!res.ok) {
    const txt = await res.text();
    throw new Error(parseApiErrorMessage(txt, res.status));
  }

  return res.json();
}

function downloadUrl(path, params = {}) {
  const query = buildQuery(params);
  const url = `${state.apiBase}${path}${query ? `?${query}` : ""}`;
  window.open(url, "_blank");
}

async function downloadProtectedCsv(path, params = {}) {
  const query = buildQuery(params);
  const url = `${state.apiBase}${path}${query ? `?${query}` : ""}`;
  const res = await fetch(url, { headers: authHeaders(true) });
  if (!res.ok) {
    const txt = await res.text();
    throw new Error(parseApiErrorMessage(txt, res.status));
  }
  const blob = await res.blob();
  const tmpUrl = URL.createObjectURL(blob);
  window.open(tmpUrl, "_blank");
  setTimeout(() => URL.revokeObjectURL(tmpUrl), 5000);
}

function fillSelect(selectEl, values, includeAll = true) {
  selectEl.innerHTML = "";
  if (includeAll) {
    const opt = document.createElement("option");
    opt.value = "";
    opt.textContent = "Tất cả";
    selectEl.appendChild(opt);
  }
  values.forEach((v) => {
    const opt = document.createElement("option");
    opt.value = v;
    opt.textContent = v;
    selectEl.appendChild(opt);
  });
}

function getFilters() {
  return {
    campaign_id: el.fCampaign.value,
    age: el.fAge.value,
    gender: el.fGender.value,
    quality_label: el.fQuality.value,
    min_ctr: el.fMinCtr.value || null,
    max_cpa: el.fMaxCpa.value || null,
  };
}

function saveFiltersToStorage() {
  localStorage.setItem("adsFilterState", JSON.stringify(getFilters()));
}

function restoreFiltersFromStorage() {
  try {
    const raw = localStorage.getItem("adsFilterState");
    if (!raw) return;
    const cached = JSON.parse(raw);
    if (cached.campaign_id !== undefined) el.fCampaign.value = cached.campaign_id || "";
    if (cached.age !== undefined) el.fAge.value = cached.age || "";
    if (cached.gender !== undefined) el.fGender.value = cached.gender || "";
    if (cached.quality_label !== undefined) el.fQuality.value = cached.quality_label || "";
    if (cached.min_ctr !== undefined) el.fMinCtr.value = cached.min_ctr || "";
    if (cached.max_cpa !== undefined) el.fMaxCpa.value = cached.max_cpa || "";
  } catch (_) {
    localStorage.removeItem("adsFilterState");
  }
}

function renderKpis(summary) {
  const cards = [
    ["Tổng quảng cáo", number(summary.total_ads, 0)],
    ["Tổng chi tiêu", number(summary.total_spent)],
    ["Chuyển đổi được duyệt", number(summary.total_approved_conversion, 0)],
    ["CTR trung bình", number(summary.avg_ctr, 4)],
    ["CVR trung bình", number(summary.avg_cvr, 4)],
    ["CPC trung bình", number(summary.avg_cpc, 4)],
    ["CPA trung bình", number(summary.avg_cpa, 4)],
  ];

  el.kpis.innerHTML = cards
    .map(([k, v]) => `<div class="kpi"><p>${k}</p><h4>${v}</h4></div>`)
    .join("");
}

function renderChart(key, canvasId, config) {
  if (state.charts[key]) {
    state.charts[key].destroy();
  }
  const ctx = document.getElementById(canvasId).getContext("2d");
  state.charts[key] = new Chart(ctx, config);
}

async function loadSummaryAndCharts() {
  const filters = getFilters();

  const [summary, quality, ageKpi, genderKpi] = await Promise.all([
    apiGet("/api/summary", filters),
    apiGet("/api/charts/quality-distribution", filters),
    apiGet("/api/charts/age-kpi", { campaign_id: filters.campaign_id, gender: filters.gender }),
    apiGet("/api/charts/gender-kpi", { campaign_id: filters.campaign_id, age: filters.age }),
  ]);

  renderKpis(summary);

  renderChart("quality", "qualityChart", {
    type: "doughnut",
    data: {
      labels: quality.labels,
      datasets: [{ data: quality.values, backgroundColor: ["#2a9d8f", "#005f73", "#bb3e03"] }],
    },
    options: { responsive: true, maintainAspectRatio: false },
  });

  renderChart("age", "ageChart", {
    type: "bar",
    data: {
      labels: ageKpi.labels,
      datasets: [
        { label: "CTR", data: ageKpi.ctr, backgroundColor: "#0a9396" },
        { label: "CVR", data: ageKpi.cvr, backgroundColor: "#ee9b00" },
      ],
    },
    options: { responsive: true, maintainAspectRatio: false },
  });

  renderChart("gender", "genderChart", {
    type: "bar",
    data: {
      labels: genderKpi.labels,
      datasets: [
        { label: "CTR", data: genderKpi.ctr, backgroundColor: "#0a9396" },
        { label: "CVR", data: genderKpi.cvr, backgroundColor: "#ca6702" },
      ],
    },
    options: { responsive: true, maintainAspectRatio: false },
  });

  await loadCampaignChart();
}

async function loadCampaignChart() {
  const quality_label = el.fQuality.value || null;
  const group_by = el.campaignGroupBy.value;
  const data = await apiGet("/api/charts/campaign-kpi", { quality_label, group_by, top_n: 12 });
  const shortLabels = data.labels.map((label) => shortenLabel(label, 16));

  renderChart("campaign", "campaignChart", {
    type: "bar",
    data: {
      labels: shortLabels,
      datasets: [
        { label: "CTR", data: data.ctr, backgroundColor: "rgba(0,95,115,0.78)" },
        { label: "CVR", data: data.cvr, backgroundColor: "rgba(187,62,3,0.78)" },
      ],
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      indexAxis: "y",
      plugins: {
        tooltip: {
          callbacks: {
            title(items) {
              const idx = items[0].dataIndex;
              return data.labels[idx];
            },
          },
        },
      },
    },
  });
}

async function loadRecommendations() {
  const filters = getFilters();
  const data = await apiGet("/api/recommendations/segments", {
    campaign_id: filters.campaign_id,
    age: filters.age,
    gender: filters.gender,
    limit: 20,
  });

  el.segmentExplain.textContent = "Bấm vào một phân khúc để xem giải thích khuyến nghị.";

  el.recommendationRows.innerHTML = data.items
    .map(
      (r, i) => `<tr data-segment-id="${r.segment_id}">
        <td>${i + 1}</td><td>${r.segment_id}</td>
        <td><span class="badge ${r.suggested_action}">${formatActionLabel(r.suggested_action)}</span></td>
        <td>${number(r.recommendation_score, 4)}</td>
        <td>${r.campaign_id}</td>
        <td>${r.age}</td>
        <td>${r.gender}</td>
        <td>${number(r.avg_cpa, 4)}</td>
        <td>${number(r.good_ratio, 4)}</td>
      </tr>`
    )
    .join("");

  const rows = el.recommendationRows.querySelectorAll("tr[data-segment-id]");
  rows.forEach((row) => {
    row.style.cursor = "pointer";
    row.addEventListener("click", async () => {
      const segmentId = row.getAttribute("data-segment-id");
      const detail = await apiGet("/api/recommendations/explain", { segment_id: segmentId });
      el.segmentExplain.textContent = `Phân khúc: ${detail.segment_id} | ${detail.explanation}`;
    });
  });
}

async function simulateBudget() {
  const total_budget = Number(el.bTotalBudget.value || 0);
  const top_n = Number(el.bTopN.value || 8);
  const campaign_id = el.fCampaign.value || null;

  const data = await apiGet("/api/recommendations/budget-plan", { total_budget, top_n, campaign_id });

  el.budgetMeta.textContent = `Số phân khúc sử dụng: ${data.segments_used} | Tổng chuyển đổi kỳ vọng: ${number(data.expected_total_conversions, 2)}`;

  el.budgetRows.innerHTML = data.allocations
    .map(
      (r, i) => `<tr>
        <td>${i + 1}</td><td>${r.segment_id}</td>
        <td><span class="badge ${r.suggested_action}">${formatActionLabel(r.suggested_action)}</span></td>
        <td>${number(r.recommendation_score, 4)}</td>
        <td>${number(r.weight, 4)}</td>
        <td>${number(r.allocated_budget, 2)}</td>
        <td>${number(r.expected_conversions, 2)}</td>
      </tr>`
    )
    .join("");
}

async function loadExperiments() {
  const objective = el.experimentObjective.value || "balanced";
  const [metrics, features, evidence] = await Promise.all([
    apiGet("/api/experiments/metrics", {}, true),
    apiGet("/api/experiments/top-features", { limit: 15 }, true),
    apiGet("/api/experiments/model-evidence", {}, true),
  ]);
  const decision = await apiGet("/api/experiments/decision", { objective }, true);

  const rule = metrics.rule_baseline;
  const model = metrics.logistic_regression;
  const labels = ["accuracy", "precision", "recall", "f1", "roc_auc"];

  renderChart("experiment", "experimentChart", {
    type: "bar",
    data: {
      labels,
      datasets: [
        { label: "Rule baseline", data: labels.map((k) => rule[k]), backgroundColor: "#94d2bd" },
        { label: "Logistic regression", data: labels.map((k) => model[k]), backgroundColor: "#ee9b00" },
      ],
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      scales: {
        y: {
          min: 0,
          max: 1,
        },
      },
    },
  });

  const ds = metrics.dataset;
  el.experimentMeta.textContent = `Thời điểm sinh dữ liệu: ${metrics.generated_at} | Số dòng test: ${ds.test_rows} | Tỷ lệ dương tính: ${number(ds.positive_rate, 4)}`;
  el.experimentDecision.innerHTML = `
    Mục tiêu: ${formatObjectiveLabel(decision.objective)}
    <span class="winner-tag">Mô hình thắng: ${formatWinnerName(decision.winner)}</span>
    <div>Chênh lệch có trọng số: ${number(decision.weighted_delta, 6)} | ${decision.explanation}</div>
  `;

  el.featureRows.innerHTML = features.items
    .map(
      (f, i) => `<tr>
        <td>${i + 1}</td><td>${f.feature}</td>
        <td>${number(f.coefficient, 6)}</td>
        <td>${number(f.abs_coefficient, 6)}</td>
      </tr>`
    )
    .join("");

  const assumptions = evidence.assumptions || {};
  el.modelEvidenceAssumption.textContent = `${assumptions.note || "Bằng chứng ước lượng"} | Số dòng test: ${assumptions.test_rows || 0} | Tỷ lệ dương tính: ${number(assumptions.positive_rate, 4)}`;

  const confusion = evidence.confusion_matrices || {};
  const confusionPairs = [
    ["Rule baseline", confusion.rule_baseline || {}],
    ["Logistic regression", confusion.logistic_regression || {}],
  ];
  el.confusionRows.innerHTML = confusionPairs
    .map(
      ([name, c]) => `<tr>
        <td>${name}</td>
        <td>${number(c.tp, 0)}</td>
        <td>${number(c.fp, 0)}</td>
        <td>${number(c.tn, 0)}</td>
        <td>${number(c.fn, 0)}</td>
        <td>${number(c.estimated_precision, 4)}</td>
        <td>${number(c.estimated_recall, 4)}</td>
        <td>${number(c.estimated_f1, 4)}</td>
      </tr>`
    )
    .join("");

  const thresholdRows = evidence.threshold_tradeoff || [];
  el.thresholdRows.innerHTML = thresholdRows
    .map(
      (row, i) => `<tr>
        <td>${i + 1}</td>
        <td>${number(row.threshold, 2)}</td>
        <td>${number(row.estimated_precision, 4)}</td>
        <td>${number(row.estimated_recall, 4)}</td>
        <td>${number(row.estimated_f1, 4)}</td>
      </tr>`
    )
    .join("");

  const recommended = evidence.recommended_threshold_by_f1 || {};
  el.thresholdRecommendation.textContent = `Ngưỡng khuyến nghị theo F1 ước lượng: ${number(recommended.threshold, 2)} (F1: ${number(recommended.estimated_f1, 4)})`;
}

async function loadDefenseSummary() {
  const data = await apiGet("/api/experiments/defense-summary", {}, true);
  el.defenseHeadline.textContent = data.headline;

  const winners = Object.entries(data.winners || {});
  el.defenseWinnerRows.innerHTML = winners
    .map(([objective, winner]) => `<tr><td>${formatObjectiveLabel(objective)}</td><td>${formatWinnerName(winner)}</td></tr>`)
    .join("");

  el.defensePoints.textContent = (data.key_points || []).join("\n");
}

function resetFilters() {
  el.fCampaign.value = "";
  el.fAge.value = "";
  el.fGender.value = "";
  el.fQuality.value = "";
  el.fMinCtr.value = "";
  el.fMaxCpa.value = "";
  saveFiltersToStorage();
}

async function loadFilterOptions() {
  const data = await apiGet("/api/filters/options");
  fillSelect(el.fCampaign, data.campaign_ids || []);
  fillSelect(el.fAge, data.ages || []);
  fillSelect(el.fGender, data.genders || []);
  fillSelect(el.fQuality, data.quality_labels || []);
}

async function boot() {
  try {
    el.apiBase.value = state.apiBase;
    updateAuthUI();
    await loadSystemHealth();
    await loadUploadLogs();
    await loadFilterOptions();
    restoreFiltersFromStorage();
    await loadSummaryAndCharts();
    await loadRecommendations();
    await simulateBudget();
    if (state.authToken) {
      await loadExperiments();
      await loadDefenseSummary();
    } else {
      el.experimentMeta.textContent = "Đang ở chế độ khách. Bấm 'Tải lại' ở phần Thực nghiệm để đăng nhập.";
      el.defenseHeadline.textContent = "Chưa đăng nhập để xem kết quả thực nghiệm.";
    }
    showToast("Đã tải dashboard thành công");
  } catch (err) {
    console.error(err);
    showToast("Không thể tải dashboard. Vui lòng kiểm tra API.");
  }
}

el.btnApplyApi.addEventListener("click", withUiAction(async () => {
  state.apiBase = el.apiBase.value.trim().replace(/\/$/, "");
  localStorage.setItem("adsApiBase", state.apiBase);
  await boot();
}, "Không thể kết nối API"));

el.btnUploadCsv.addEventListener("click", withUiAction(async () => {
  await ensureLogin();
  ensureRole(["analyst", "admin"]);
  const file = el.uploadCsvFile.files && el.uploadCsvFile.files[0];
  if (!file) {
    showToast("Hãy chọn file CSV trước");
    return;
  }

  const result = await apiUpload("/api/data/upload", file, true);
  el.uploadMeta.textContent = `Đã tải lên: ${file.name} | Số dòng scored: ${result.scored_rows} | Số dòng phân khúc: ${result.segment_rows}`;

  await loadFilterOptions();
  resetFilters();
  await loadSystemHealth();
  await loadUploadLogs();
  await loadSummaryAndCharts();
  await loadRecommendations();
  await simulateBudget();
  await loadExperiments();
  await loadDefenseSummary();
  showToast("Tải lên và phân tích thành công");
}, "Tải lên thất bại, vui lòng kiểm tra đúng định dạng CSV"));

el.btnApplyFilters.addEventListener("click", withUiAction(async () => {
  saveFiltersToStorage();
  await loadSummaryAndCharts();
  await loadRecommendations();
  await simulateBudget();
  if (state.authToken) {
    await loadExperiments();
    await loadDefenseSummary();
  }
  showToast("Đã áp dụng bộ lọc");
}, "Lọc dữ liệu thất bại"));

el.btnResetFilters.addEventListener("click", withUiAction(async () => {
  resetFilters();
  await loadSummaryAndCharts();
  await loadRecommendations();
  await simulateBudget();
  if (state.authToken) {
    await loadExperiments();
    await loadDefenseSummary();
  }
  showToast("Đã đặt lại bộ lọc");
}, "Đặt lại bộ lọc thất bại"));

[el.fCampaign, el.fAge, el.fGender, el.fQuality, el.fMinCtr, el.fMaxCpa].forEach((field) => {
  field.addEventListener("change", saveFiltersToStorage);
});

el.btnRefreshHealth.addEventListener("click", withUiAction(async () => {
  await loadSystemHealth();
  showToast("Đã cập nhật tình trạng hệ thống");
}, "Không thể tải tình trạng hệ thống"));

el.btnLoadUploadLogs.addEventListener("click", withUiAction(async () => {
  await loadUploadLogs();
  showToast("Đã cập nhật nhật ký upload");
}, "Không thể tải nhật ký upload"));

el.btnLoadCampaignChart.addEventListener("click", withUiAction(async () => {
  await loadCampaignChart();
  showToast("Đã cập nhật biểu đồ chiến dịch");
}, "Không thể tải biểu đồ chiến dịch"));

el.btnLoadRecommendations.addEventListener("click", withUiAction(async () => {
  await loadRecommendations();
  showToast("Đã cập nhật khuyến nghị");
}, "Không thể tải dữ liệu khuyến nghị"));

el.btnExportSegmentsCsv.addEventListener("click", () => {
  const filters = getFilters();
  downloadUrl("/api/recommendations/segments/export.csv", {
    campaign_id: filters.campaign_id,
    age: filters.age,
    gender: filters.gender,
    limit: 500,
  });
  showToast("Đang tải xuống CSV khuyến nghị");
});

el.btnSimulateBudget.addEventListener("click", withUiAction(async () => {
  await simulateBudget();
  showToast("Đã cập nhật kế hoạch ngân sách");
}, "Không thể mô phỏng ngân sách"));

el.btnExportBudgetCsv.addEventListener("click", () => {
  const total_budget = Number(el.bTotalBudget.value || 0);
  const top_n = Number(el.bTopN.value || 8);
  const campaign_id = el.fCampaign.value || null;
  downloadUrl("/api/recommendations/budget-plan/export.csv", {
    total_budget,
    top_n,
    campaign_id,
  });
  showToast("Đang tải xuống CSV kế hoạch ngân sách");
});

el.btnLoadExperiments.addEventListener("click", withUiAction(async () => {
  await ensureLogin();
  await loadExperiments();
  showToast("Đã cập nhật chỉ số thực nghiệm");
}, "Không thể tải chỉ số thực nghiệm"));

el.btnExportExperimentMetricsCsv.addEventListener("click", withUiAction(async () => {
  await ensureLogin();
  await downloadProtectedCsv("/api/experiments/metrics/export.csv");
  showToast("Đang tải xuống CSV chỉ số thực nghiệm");
}, "Không thể tải file chỉ số"));

el.btnExportTopFeaturesCsv.addEventListener("click", withUiAction(async () => {
  await ensureLogin();
  await downloadProtectedCsv("/api/experiments/top-features/export.csv", { limit: 50 });
  showToast("Đang tải xuống CSV top đặc trưng");
}, "Không thể tải file top-features"));

el.btnLoadDefenseSummary.addEventListener("click", withUiAction(async () => {
  await ensureLogin();
  await loadDefenseSummary();
  showToast("Đã cập nhật tóm tắt bảo vệ");
}, "Không thể tải tóm tắt bảo vệ"));

el.experimentObjective.addEventListener("change", withUiAction(async () => {
  await ensureLogin();
  await loadExperiments();
  await loadDefenseSummary();
  showToast("Đã cập nhật mục tiêu thực nghiệm");
}, "Không thể đổi mục tiêu"));

el.btnLogin.addEventListener("click", withUiAction(async () => {
  const username = el.authUsername.value.trim();
  const password = el.authPassword.value;
  if (!username || !password) {
    showToast("Nhập tên đăng nhập và mật khẩu");
    return;
  }
  const res = await fetch(`${state.apiBase}/api/auth/login`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ username, password }),
  });
  if (!res.ok) {
    const txt = await res.text();
    throw new Error(txt || `Đăng nhập thất bại: ${res.status}`);
  }
  const payload = await res.json();
  state.authToken = payload.access_token || "";
  state.authUser = payload.username || "";
  state.authRole = payload.role || "guest";
  localStorage.setItem("adsAuthToken", state.authToken);
  localStorage.setItem("adsAuthUser", state.authUser);
  localStorage.setItem("adsAuthRole", state.authRole);
  updateAuthUI();
  showToast(`Đã đăng nhập: ${state.authUser} (${state.authRole})`);
  await loadExperiments();
  await loadDefenseSummary();
}, "Đăng nhập thất bại"));

el.authPassword.addEventListener("keydown", (e) => {
  if (e.key === "Enter") el.btnLogin.click();
});

el.btnLogout.addEventListener("click", withUiAction(async () => {
  try {
    await fetch(`${state.apiBase}/api/auth/logout`, {
      method: "POST",
      headers: authHeaders(true),
    });
  } catch (_) { /* ignore network error on logout */ }
  state.authToken = "";
  state.authUser = "";
  state.authRole = "guest";
  localStorage.removeItem("adsAuthToken");
  localStorage.removeItem("adsAuthUser");
  localStorage.removeItem("adsAuthRole");
  updateAuthUI();
  await loadUploadLogs();
  el.experimentMeta.textContent = "Đã đăng xuất. Bấm 'Tải lại' ở phần Thực nghiệm để đăng nhập lại.";
  el.defenseHeadline.textContent = "Chưa đăng nhập.";
  showToast("Đã đăng xuất");
}, "Đăng xuất thất bại"));

boot();
