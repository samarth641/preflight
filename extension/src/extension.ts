import * as vscode from "vscode";
import { PreflightPanel } from "./panel";
import { PreflightSidebarProvider } from "./sidebar";

export function activate(context: vscode.ExtensionContext): void {
  const open = (tab?: string) => {
    PreflightPanel.createOrShow(context.extensionUri, tab);
  };

  context.subscriptions.push(
    vscode.commands.registerCommand("preflight.openDashboard", () => open()),
    vscode.commands.registerCommand("preflight.recommendGpu", () => open("gpu")),
    vscode.commands.registerCommand("preflight.predictDuration", () => open("duration")),
    vscode.window.registerWebviewViewProvider(
      "preflight.sidebar",
      new PreflightSidebarProvider(context.extensionUri),
      { webviewOptions: { retainContextWhenHidden: true } }
    )
  );

  context.subscriptions.push(
    vscode.workspace.onDidChangeConfiguration((e) => {
      if (e.affectsConfiguration("preflight.apiUrl")) {
        PreflightPanel.refresh();
      }
    })
  );
}

export function deactivate(): void {
  PreflightPanel.dispose();
}
