import * as vscode from "vscode";
import { getWebviewHtml } from "./webviewHtml";
import { wireWebviewMessages } from "./messages";

export class PreflightPanel {
  public static currentPanel: PreflightPanel | undefined;
  private static readonly viewType = "preflightDashboard";
  private readonly panel: vscode.WebviewPanel;
  private initialTab: string | undefined;

  public static createOrShow(extensionUri: vscode.Uri, tab?: string): void {
    const column = vscode.window.activeTextEditor?.viewColumn ?? vscode.ViewColumn.One;

    if (PreflightPanel.currentPanel) {
      PreflightPanel.currentPanel.panel.reveal(column);
      if (tab) {
        PreflightPanel.currentPanel.panel.webview.postMessage({ type: "switchTab", tab });
      }
      return;
    }

    const panel = vscode.window.createWebviewPanel(
      PreflightPanel.viewType,
      "Preflight",
      column,
      { enableScripts: true, retainContextWhenHidden: true }
    );

    PreflightPanel.currentPanel = new PreflightPanel(panel, extensionUri, tab);
  }

  public static refresh(): void {
    PreflightPanel.currentPanel?.panel.webview.postMessage({ type: "configChanged" });
  }

  public static dispose(): void {
    PreflightPanel.currentPanel?.panel.dispose();
    PreflightPanel.currentPanel = undefined;
  }

  private constructor(panel: vscode.WebviewPanel, extensionUri: vscode.Uri, tab?: string) {
    this.panel = panel;
    this.initialTab = tab;
    panel.webview.options = {
      enableScripts: true,
      localResourceRoots: [vscode.Uri.joinPath(extensionUri, "media")],
    };
    panel.webview.html = getWebviewHtml(panel.webview, extensionUri, "panel", tab);
    this.wireMessages(panel.webview);

    panel.onDidDispose(() => {
      PreflightPanel.currentPanel = undefined;
    });
  }

  private wireMessages(webview: vscode.Webview): void {
    wireWebviewMessages(webview);
  }
}
