import * as vscode from "vscode";
import { apiBaseUrl } from "./messages";

export function getWebviewHtml(
  webview: vscode.Webview,
  extensionUri: vscode.Uri,
  mode: "panel" | "sidebar",
  initialTab?: string
): string {
  const apiUrl = apiBaseUrl();
  const media = vscode.Uri.joinPath(extensionUri, "media");
  const styleUri = webview.asWebviewUri(vscode.Uri.joinPath(media, "styles.css"));
  const scriptUri = webview.asWebviewUri(vscode.Uri.joinPath(media, "app.js"));
  const nonce = getNonce();
  const compact = mode === "sidebar" ? "compact" : "";

  return `<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8" />
  <meta http-equiv="Content-Security-Policy" content="default-src 'none'; style-src ${webview.cspSource} 'unsafe-inline'; script-src 'nonce-${nonce}'; font-src ${webview.cspSource};">
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <link rel="stylesheet" href="${styleUri}" />
  <title>Preflight</title>
</head>
<body class="${compact}" data-initial-tab="${initialTab ?? ""}" data-api-url="${apiUrl}">
  <div class="bg-mesh" aria-hidden="true"></div>
  <div class="app">
    <header class="header fade-in">
      <div class="brand">
        <div class="logo-orbit"><span class="logo-core">P</span></div>
        <div>
          <h1>Preflight</h1>
          <p class="subtitle">AI training intelligence for developers</p>
        </div>
      </div>
      <div class="status-pill" id="apiStatus">
        <span class="status-dot"></span>
        <span class="status-text">Checking API…</span>
      </div>
    </header>

    <nav class="tabs fade-in delay-1" role="tablist">
      <button class="tab active" data-tab="gpu" role="tab">GPU</button>
      <button class="tab" data-tab="duration" role="tab">Duration</button>
      <button class="tab" data-tab="dataset" role="tab">Dataset</button>
      <button class="tab" data-tab="training" role="tab">Training</button>
    </nav>

    <main>
      <section class="panel active" id="panel-gpu" role="tabpanel">
        <form class="card form-card fade-in delay-2" id="formGpu" novalidate>
          <div class="form-error" id="formGpuError" role="alert" hidden></div>
          <h2>Recommend GPU</h2>
          <p class="hint">Benchmark-ranked hardware + optional cost estimate</p>
          <div class="grid">
            <label>Parameters (billions)<input name="params" type="text" inputmode="decimal" value="7" placeholder="e.g. 7 or 0.5" /></label>
            <label>Training mode
              <select name="mode"><option value="lora">LoRA</option><option value="full">Full</option><option value="qlora">QLoRA</option></select>
            </label>
            <label>Model type
              <select name="modelType"><option value="transformer">Transformer</option><option value="vision">Vision</option><option value="cnn">CNN</option></select>
            </label>
            <label>Epochs<input name="epochs" type="text" inputmode="numeric" value="5" placeholder="e.g. 10" /></label>
          </div>
          <button type="submit" class="btn primary"><span class="btn-shine"></span>Recommend</button>
        </form>
        <div id="gpuResults" class="results"></div>
      </section>

      <section class="panel" id="panel-duration" role="tabpanel">
        <form class="card form-card fade-in delay-2" id="formDuration" novalidate>
          <div class="form-error" id="formDurationError" role="alert" hidden></div>
          <h2>Predict Duration <span class="badge ml">XGBoost</span></h2>
          <p class="hint">ML model + physics fallback</p>
          <div class="grid">
            <label>Parameters (billions)<input name="params" type="text" inputmode="decimal" value="7" placeholder="e.g. 7" /></label>
            <label>Dataset tokens<span class="field-hint">100B or 100000000000</span>
              <input name="tokens" type="text" inputmode="decimal" value="100B" placeholder="100B, 1e11, or full number" />
            </label>
            <label>GPU
              <select name="gpu">
                <option value="mi300x">MI300X</option>
                <option value="h100-80gb">H100 80GB</option>
                <option value="a100-80gb">A100 80GB</option>
                <option value="rtx-4090">RTX 4090</option>
                <option value="rtx-5090">RTX 5090</option>
              </select>
            </label>
            <label>GPU count<input name="nGpus" type="text" inputmode="numeric" value="4" placeholder="e.g. 4" /></label>
            <label>Epochs<input name="epochs" type="text" inputmode="numeric" value="10" placeholder="e.g. 10" /></label>
            <label>Cloud provider
              <select name="provider">
                <option value="">None</option>
                <option value="azure">Azure</option>
                <option value="runpod">RunPod</option>
                <option value="lambda">Lambda</option>
              </select>
            </label>
          </div>
          <button type="submit" class="btn primary"><span class="btn-shine"></span>Predict</button>
        </form>
        <div id="durationResults" class="results"></div>
      </section>

      <section class="panel" id="panel-dataset" role="tabpanel">
        <form class="card form-card fade-in delay-2" id="formDataset" novalidate>
          <div class="form-error" id="formDatasetError" role="alert" hidden></div>
          <h2>Analyze Dataset <span class="badge rules">Rules</span></h2>
          <p class="hint">Quality score + recommendations from rule engine</p>
          <label>Dataset folder path<input name="path" type="text" placeholder="Click Browse or paste full path…" id="datasetPath" /></label>
          <button type="button" class="btn ghost" id="pickDataset">Browse folder</button>
          <button type="submit" class="btn primary"><span class="btn-shine"></span>Analyze</button>
        </form>
        <div id="datasetResults" class="results"></div>
      </section>

      <section class="panel" id="panel-training" role="tabpanel">
        <form class="card form-card fade-in delay-2" id="formTraining" novalidate>
          <div class="form-error" id="formTrainingError" role="alert" hidden></div>
          <h2>Analyze Training Log <span class="badge rules">Rules</span></h2>
          <p class="hint">Overfitting, GPU bottlenecks, health score</p>
          <label>Log file (CSV/JSON)<input name="path" type="text" placeholder="Click Browse or paste full path…" id="trainingPath" /></label>
          <button type="button" class="btn ghost" id="pickTraining">Browse file</button>
          <button type="submit" class="btn primary"><span class="btn-shine"></span>Analyze</button>
        </form>
        <div id="trainingResults" class="results"></div>
      </section>
    </main>
  </div>
  <script nonce="${nonce}" src="${scriptUri}"></script>
</body>
</html>`;
}

function getNonce(): string {
  const chars = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789";
  let t = "";
  for (let i = 0; i < 32; i++) {
    t += chars.charAt(Math.floor(Math.random() * chars.length));
  }
  return t;
}
