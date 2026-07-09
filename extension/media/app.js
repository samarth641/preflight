/* Preflight webview — talks to FastAPI backend */
(function () {
  const vscode = acquireVsCodeApi();
  const apiUrl = document.body.dataset.apiUrl || "http://127.0.0.1:8000";

  let pickRequestId = 0;
  let apiRequestId = 0;
  const pendingPicks = new Map();
  const pendingApi = new Map();

  // ── Tabs ──────────────────────────────────────────────────────────
  const tabs = document.querySelectorAll(".tab");
  const panels = document.querySelectorAll(".panel");

  function switchTab(name) {
    tabs.forEach((t) => t.classList.toggle("active", t.dataset.tab === name));
    panels.forEach((p) => p.classList.toggle("active", p.id === "panel-" + name));
  }

  tabs.forEach((tab) => {
    tab.addEventListener("click", () => switchTab(tab.dataset.tab));
  });

  const initial = document.body.dataset.initialTab;
  if (initial) switchTab(initial);

  window.addEventListener("message", (e) => {
    const msg = e.data;
    if (msg.type === "switchTab" && msg.tab) switchTab(msg.tab);
    if (msg.type === "configChanged") {
      location.reload();
    }
    if (msg.type === "folderPicked" || msg.type === "filePicked") {
      const cb = pendingPicks.get(msg.requestId);
      if (cb) {
        pendingPicks.delete(msg.requestId);
        cb(msg.path);
      }
    }
    if (msg.type === "apiResult") {
      const cb = pendingApi.get(msg.requestId);
      if (cb) {
        pendingApi.delete(msg.requestId);
        if (msg.error) cb.reject(new Error(msg.error));
        else cb.resolve(msg.data);
      }
    }
  });

  function pickFolder() {
    return new Promise((resolve) => {
      const id = ++pickRequestId;
      pendingPicks.set(id, resolve);
      vscode.postMessage({ type: "pickFolder", requestId: id });
    });
  }

  function pickFile() {
    return new Promise((resolve) => {
      const id = ++pickRequestId;
      pendingPicks.set(id, resolve);
      vscode.postMessage({ type: "pickFile", requestId: id });
    });
  }

  document.getElementById("pickDataset")?.addEventListener("click", async () => {
    const p = await pickFolder();
    if (p) document.getElementById("datasetPath").value = p;
  });

  document.getElementById("pickTraining")?.addEventListener("click", async () => {
    const p = await pickFile();
    if (p) document.getElementById("trainingPath").value = p;
  });

  // ── API (proxied via extension host — webviews cannot fetch localhost) ──
  function api(path, body) {
    return new Promise((resolve, reject) => {
      const id = ++apiRequestId;
      pendingApi.set(id, { resolve, reject });
      vscode.postMessage({ type: "api", requestId: id, path, body });
    });
  }

  async function checkHealth() {
    const el = document.getElementById("apiStatus");
    try {
      const h = await api("/health");
      el.className = "status-pill online";
      el.querySelector(".status-text").textContent = "API online · v" + (h.version || "?");
    } catch {
      el.className = "status-pill offline";
      el.querySelector(".status-text").textContent = "API offline — start uvicorn in backend/";
    }
  }

  checkHealth();
  setInterval(checkHealth, 30000);

  function showLoading(container) {
    container.innerHTML = `
      <div class="loading-card">
        <div class="spinner"></div>
        <div>
          <div class="skeleton" style="width:140px"></div>
          <div class="skeleton" style="width:200px"></div>
        </div>
      </div>`;
  }

  function showFormError(formId, message, fieldName) {
    const el = document.getElementById(formId + "Error");
    const form = document.getElementById(formId);
    form?.querySelectorAll(".field-invalid").forEach((n) => n.classList.remove("field-invalid"));
    if (fieldName && form) {
      const input = form.querySelector(`[name="${fieldName}"]`);
      input?.classList.add("field-invalid");
      input?.focus();
    }
    if (el) {
      el.hidden = false;
      el.innerHTML = `<strong>Fix this field</strong>${escapeHtml(message)}`;
      el.scrollIntoView({ behavior: "smooth", block: "nearest" });
    }
  }

  function clearFormError(formId) {
    const el = document.getElementById(formId + "Error");
    if (el) {
      el.hidden = true;
      el.innerHTML = "";
    }
    document.getElementById(formId)?.querySelectorAll(".field-invalid").forEach((n) => {
      n.classList.remove("field-invalid");
    });
  }

  function showError(container, msg, title) {
    container.innerHTML = `<div class="error-banner"><strong>${escapeHtml(title || "Request failed")}</strong>${escapeHtml(msg)}</div>`;
    container.scrollIntoView({ behavior: "smooth", block: "nearest" });
  }

  function parsePositiveFloat(raw, label, fieldName) {
    const s = String(raw ?? "").trim().replace(/,/g, "");
    if (!s) {
      const err = new Error(`${label} is empty. Example: 7 or 0.5`);
      err.fieldName = fieldName;
      throw err;
    }
    const n = Number(s);
    if (!Number.isFinite(n) || n <= 0) {
      const err = new Error(`${label} must be a positive number. You entered "${raw}".`);
      err.fieldName = fieldName;
      throw err;
    }
    return n;
  }

  function parsePositiveInt(raw, label, fieldName) {
    const n = parsePositiveFloat(raw, label, fieldName);
    if (!Number.isInteger(n)) {
      const err = new Error(`${label} must be a whole number (no decimals). You entered "${raw}".`);
      err.fieldName = fieldName;
      throw err;
    }
    return n;
  }

  function parseTokens(raw) {
    const s = String(raw ?? "").trim().replace(/,/g, "");
    if (!s) {
      const err = new Error("Dataset tokens is empty. Try 100B, 1e11, or 100000000000.");
      err.fieldName = "tokens";
      throw err;
    }
    const sci = s.match(/^[+-]?(\d+(\.\d+)?|\.\d+)[eE][+-]?\d+$/);
    if (sci) {
      const n = Number(s);
      if (Number.isFinite(n) && n > 0) return n;
    }
    const suffix = s.match(/^([\d.]+)\s*([kKmMbBtT])$/);
    if (suffix) {
      const mult = { k: 1e3, m: 1e6, b: 1e9, t: 1e12 };
      const n = parseFloat(suffix[1]) * mult[suffix[2].toLowerCase()];
      if (Number.isFinite(n) && n > 0) return n;
    }
    return parsePositiveFloat(raw, "Dataset tokens", "tokens");
  }

  function parsePath(raw, label, fieldName) {
    const s = String(raw ?? "").trim();
    if (!s) {
      const err = new Error(`${label}: click Browse or paste the full folder/file path.`);
      err.fieldName = fieldName;
      throw err;
    }
    return s;
  }

  function handleValidationError(formId, out, err) {
    const msg = err.message || "Invalid input";
    showFormError(formId, msg, err.fieldName);
    showError(out, msg, "Check the form");
  }

  function handleApiError(out, err) {
    let msg = err.message || "Could not reach the Preflight API.";
    if (msg.includes("Cannot reach Preflight API")) {
      msg = "Backend not running. In a terminal run: cd backend && uvicorn app.main:app --port 8000";
    }
    showError(out, msg, "Request failed");
  }

  function escapeHtml(s) {
    const d = document.createElement("div");
    d.textContent = s;
    return d.innerHTML;
  }

  function formatCost(n) {
    if (n == null) return "—";
    return "$" + n.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 });
  }

  function scoreRing(score01, uid) {
    const pct = Math.min(100, Math.max(0, score01 * 100));
    const offset = 126 - (126 * pct) / 100;
    const gradId = "scoreGrad" + uid;
    return `
      <svg class="score-ring" viewBox="0 0 48 48">
        <defs>
          <linearGradient id="${gradId}" x1="0%" y1="0%" x2="100%" y2="100%">
            <stop offset="0%" stop-color="#6366f1"/>
            <stop offset="100%" stop-color="#22d3ee"/>
          </linearGradient>
        </defs>
        <circle class="bg" cx="24" cy="24" r="20"/>
        <circle class="fg" cx="24" cy="24" r="20" style="--offset:${offset};stroke:url(#${gradId})"/>
        <text x="24" y="28" text-anchor="middle" fill="#e8eaf6" font-size="11" font-weight="700">${Math.round(pct)}</text>
      </svg>`;
  }

  // ── GPU Recommend ─────────────────────────────────────────────────
  document.getElementById("formGpu")?.addEventListener("submit", async (e) => {
    e.preventDefault();
    const form = e.target;
    const fd = new FormData(form);
    const out = document.getElementById("gpuResults");
    clearFormError("formGpu");

    let params;
    let epochs;
    try {
      params = parsePositiveFloat(fd.get("params"), "Parameters (billions)", "params");
      epochs = parsePositiveInt(fd.get("epochs"), "Epochs", "epochs");
    } catch (err) {
      handleValidationError("formGpu", out, err);
      return;
    }

    showLoading(out);
    const btn = form.querySelector('button[type="submit"]');
    btn.disabled = true;

    try {
      const data = await api("/gpu/recommend", {
        parameter_count_billion: params,
        training_mode: fd.get("mode") === "qlora" ? "lora" : fd.get("mode"),
        model_type: fd.get("modelType"),
        epochs,
        include_cost: true,
        max_results: 5,
      });
      renderGpuResults(out, data);
    } catch (err) {
      handleApiError(out, err);
    } finally {
      btn.disabled = false;
    }
  });

  function renderGpuResults(container, data) {
    if (!data.candidates?.length) {
      container.innerHTML = '<p class="empty-hint">No matching GPUs found.</p>';
      return;
    }

    let html = "";
    if (data.required_vram_gb) {
      html += `<div class="stat-card highlight" style="animation-delay:0s">
        <div class="stat-label">Required VRAM</div>
        <div class="stat-value small">${data.required_vram_gb.toFixed(1)} GB</div>
      </div>`;
    }

    data.candidates.forEach((c, i) => {
      const rank = i + 1;
      const cost = c.cost_estimate;
      const costStr = cost ? formatCost(cost.total_usd) + " · " + (cost.estimated_hours?.toFixed(1) || "?") + "h" : "";
      html += `
        <div class="gpu-card rank-${rank}" style="animation-delay:${i * 0.08}s">
          <div class="rank-badge">${rank}</div>
          ${scoreRing(c.score, i)}
          <div class="gpu-info">
            <div class="gpu-name">${escapeHtml(c.gpu.name)}</div>
            <div class="gpu-meta">${c.gpu.vram_gb}GB VRAM · ${c.fit_rating} · ${c.headroom_gb.toFixed(0)}GB headroom</div>
            ${costStr ? `<div class="gpu-meta">${costStr}</div>` : ""}
          </div>
        </div>`;
    });

    if (data.warnings?.length) {
      html += '<ul class="findings">';
      data.warnings.forEach((w, i) => {
        html += `<li class="finding warn" style="animation-delay:${0.4 + i * 0.05}s">
          <span class="finding-icon">⚠</span><span>${escapeHtml(w.title)}: ${escapeHtml(w.message)}</span></li>`;
      });
      html += "</ul>";
    }

    container.innerHTML = html;
  }

  // ── Duration Predict ──────────────────────────────────────────────
  document.getElementById("formDuration")?.addEventListener("submit", async (e) => {
    e.preventDefault();
    const form = e.target;
    const fd = new FormData(form);
    const out = document.getElementById("durationResults");
    clearFormError("formDuration");

    let body;
    try {
      body = {
        parameter_count_billion: parsePositiveFloat(fd.get("params"), "Parameters (billions)", "params"),
        dataset_tokens: parseTokens(fd.get("tokens")),
        gpu_id: fd.get("gpu"),
        n_gpus: parsePositiveInt(fd.get("nGpus"), "GPU count", "nGpus"),
        epochs: parsePositiveInt(fd.get("epochs"), "Epochs", "epochs"),
        domain: "language",
      };
      const provider = String(fd.get("provider") || "").trim();
      if (provider) body.cloud_provider = provider;
    } catch (err) {
      handleValidationError("formDuration", out, err);
      return;
    }

    showLoading(out);
    const btn = form.querySelector('button[type="submit"]');
    btn.disabled = true;

    try {
      const data = await api("/predict/duration", body);
      renderDurationResults(out, data);
    } catch (err) {
      handleApiError(out, err);
    } finally {
      btn.disabled = false;
    }
  });

  function renderDurationResults(container, data) {
    container.innerHTML = `
      <div class="stat-grid">
        <div class="stat-card highlight" style="animation-delay:0s">
          <div class="stat-label">Estimated duration</div>
          <div class="stat-value">${escapeHtml(data.estimated_duration_human)}</div>
        </div>
        <div class="stat-card" style="animation-delay:0.06s">
          <div class="stat-label">Hours (ML)</div>
          <div class="stat-value small">${data.estimated_hours.toFixed(2)}</div>
        </div>
        <div class="stat-card" style="animation-delay:0.12s">
          <div class="stat-label">Physics formula</div>
          <div class="stat-value small">${data.theoretical_hours.toFixed(2)}h</div>
        </div>
        <div class="stat-card" style="animation-delay:0.18s">
          <div class="stat-label">GPU</div>
          <div class="stat-value small">${escapeHtml(data.gpu_id)} ×${data.n_gpus}</div>
        </div>
        ${data.estimated_cost_usd != null ? `
        <div class="stat-card" style="animation-delay:0.24s">
          <div class="stat-label">Est. cost (${escapeHtml(data.cost_provider || "")})</div>
          <div class="stat-value small">${formatCost(data.estimated_cost_usd)}</div>
        </div>` : ""}
        <div class="stat-card" style="animation-delay:0.3s">
          <div class="stat-label">Model</div>
          <div class="stat-value small" style="font-size:0.75rem">${escapeHtml(data.model_version)}</div>
        </div>
      </div>`;
  }

  // ── Dataset Analyze ───────────────────────────────────────────────
  document.getElementById("formDataset")?.addEventListener("submit", async (e) => {
    e.preventDefault();
    const form = e.target;
    const fd = new FormData(form);
    const out = document.getElementById("datasetResults");
    clearFormError("formDataset");

    let path;
    try {
      path = parsePath(fd.get("path"), "Dataset folder", "path");
    } catch (err) {
      handleValidationError("formDataset", out, err);
      return;
    }

    showLoading(out);
    const btn = form.querySelector('button[type="submit"]');
    btn.disabled = true;

    try {
      const data = await api("/dataset/analyze", { path });
      renderAnalysisResults(out, data, "dataset");
    } catch (err) {
      handleApiError(out, err);
    } finally {
      btn.disabled = false;
    }
  });

  // ── Training Analyze ──────────────────────────────────────────────
  document.getElementById("formTraining")?.addEventListener("submit", async (e) => {
    e.preventDefault();
    const form = e.target;
    const fd = new FormData(form);
    const out = document.getElementById("trainingResults");
    clearFormError("formTraining");

    let path;
    try {
      path = parsePath(fd.get("path"), "Training log file", "path");
    } catch (err) {
      handleValidationError("formTraining", out, err);
      return;
    }

    showLoading(out);
    const btn = form.querySelector('button[type="submit"]');
    btn.disabled = true;

    try {
      const data = await api("/training/analyze", { path });
      renderAnalysisResults(out, data, "training");
    } catch (err) {
      handleApiError(out, err);
    } finally {
      btn.disabled = false;
    }
  });

  function renderAnalysisResults(container, data, kind) {
    let metricsHtml = "";
    if (kind === "dataset" && data.metrics) {
      const m = data.metrics;
      metricsHtml = `
        <div class="stat-grid">
          <div class="stat-card"><div class="stat-label">Images</div><div class="stat-value small">${m.image_count}</div></div>
          <div class="stat-card"><div class="stat-label">Classes</div><div class="stat-value small">${m.class_count}</div></div>
          <div class="stat-card"><div class="stat-label">Duplicates</div><div class="stat-value small">${m.duplicate_percent?.toFixed(1) || 0}%</div></div>
          <div class="stat-card"><div class="stat-label">Blurry</div><div class="stat-value small">${m.blur_percent?.toFixed(1) || 0}%</div></div>
        </div>`;
    }
    if (kind === "training" && data.metrics) {
      const m = data.metrics;
      metricsHtml = `
        <div class="stat-grid">
          <div class="stat-card"><div class="stat-label">Epochs</div><div class="stat-value small">${m.epoch_count}</div></div>
          <div class="stat-card"><div class="stat-label">Overfitting</div><div class="stat-value small">${m.overfitting_detected ? "Yes" : "No"}</div></div>
          <div class="stat-card"><div class="stat-label">Val loss</div><div class="stat-value small">${m.latest_val_loss?.toFixed(4) ?? "—"}</div></div>
          <div class="stat-card"><div class="stat-label">GPU util</div><div class="stat-value small">${m.avg_gpu_utilization != null ? m.avg_gpu_utilization.toFixed(0) + "%" : "—"}</div></div>
        </div>`;
    }

    let findings = "";
    const items = [
      ...(data.warnings || []).map((w) => ({ ...w, kind: "warn", text: w.message || w.title })),
      ...(data.recommendations || []).map((r) => ({ ...r, kind: "info", text: r.recommendation || r.title })),
    ];
    if (data.trends?.length) {
      data.trends.forEach((t) => items.push({ kind: t.severity === "high" ? "error" : "warn", text: t.description, title: t.name }));
    }

    if (items.length) {
      findings = '<ul class="findings">';
      items.forEach((item, i) => {
        const icon = item.kind === "error" ? "✕" : item.kind === "warn" ? "⚠" : "ℹ";
        findings += `<li class="finding ${item.kind}" style="animation-delay:${0.2 + i * 0.05}s">
          <span class="finding-icon">${icon}</span>
          <span>${escapeHtml(item.title ? item.title + ": " : "")}${escapeHtml(item.text)}</span></li>`;
      });
      findings += "</ul>";
    }

    container.innerHTML = `
      <div class="score-hero">
        <div class="score-big">${Math.round(data.score)}</div>
        <div>
          <div class="stat-label">Quality score</div>
          <div style="font-size:1.2rem;font-weight:700;margin-top:4px">Grade ${escapeHtml(data.grade)}</div>
          ${data.accuracy_impact ? `<div class="gpu-meta" style="margin-top:6px">Est. accuracy impact: −${data.accuracy_impact.estimated_loss_percent?.toFixed(1) || 0}pp</div>` : ""}
        </div>
      </div>
      ${metricsHtml}
      ${findings}`;
  }
})();
