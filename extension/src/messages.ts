import * as vscode from "vscode";

export function apiBaseUrl(): string {
  return vscode.workspace
    .getConfiguration("preflight")
    .get<string>("apiUrl", "http://127.0.0.1:8000")
    .replace(/\/$/, "");
}

export async function proxyApi(
  path: string,
  body?: unknown
): Promise<{ data?: unknown; error?: string }> {
  const url = `${apiBaseUrl()}/api/v1${path}`;
  try {
    const res = await fetch(url, {
      method: body !== undefined ? "POST" : "GET",
      headers: body !== undefined ? { "Content-Type": "application/json" } : {},
      body: body !== undefined ? JSON.stringify(body) : undefined,
    });
    const data = (await res.json().catch(() => ({}))) as { detail?: unknown };
    if (!res.ok) {
      const detail = data.detail ?? res.statusText;
      return {
        error: typeof detail === "string" ? detail : JSON.stringify(detail),
      };
    }
    return { data };
  } catch (err) {
    const message = err instanceof Error ? err.message : String(err);
    return { error: `Cannot reach Preflight API at ${apiBaseUrl()}: ${message}` };
  }
}

export function wireWebviewMessages(webview: vscode.Webview): void {
  webview.onDidReceiveMessage(async (msg: { type: string; requestId?: number; path?: string; body?: unknown }) => {
    if (msg.type === "api" && msg.requestId !== undefined && msg.path) {
      const result = await proxyApi(msg.path, msg.body);
      webview.postMessage({ type: "apiResult", requestId: msg.requestId, ...result });
      return;
    }

    if (msg.type === "pickFolder") {
      const folder = await vscode.window.showOpenDialog({
        canSelectFolders: true,
        canSelectFiles: false,
        openLabel: "Select dataset folder",
      });
      webview.postMessage({
        type: "folderPicked",
        requestId: msg.requestId,
        path: folder?.[0]?.fsPath ?? null,
      });
      return;
    }

    if (msg.type === "pickFile") {
      const file = await vscode.window.showOpenDialog({
        canSelectFiles: true,
        canSelectFolders: false,
        filters: { "Training logs": ["csv", "json"] },
        openLabel: "Select training log",
      });
      webview.postMessage({
        type: "filePicked",
        requestId: msg.requestId,
        path: file?.[0]?.fsPath ?? null,
      });
    }
  });
}
