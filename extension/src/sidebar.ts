import * as vscode from "vscode";
import { getWebviewHtml } from "./webviewHtml";
import { wireWebviewMessages } from "./messages";

export class PreflightSidebarProvider implements vscode.WebviewViewProvider {
  constructor(private readonly extensionUri: vscode.Uri) {}

  resolveWebviewView(
    webviewView: vscode.WebviewView,
    _context: vscode.WebviewViewResolveContext,
    _token: vscode.CancellationToken
  ): void {
    webviewView.webview.options = {
      enableScripts: true,
      localResourceRoots: [vscode.Uri.joinPath(this.extensionUri, "media")],
    };
    webviewView.webview.html = getWebviewHtml(webviewView.webview, this.extensionUri, "sidebar");
    this.wireMessages(webviewView.webview);
  }

  private wireMessages(webview: vscode.Webview): void {
    wireWebviewMessages(webview);
  }
}
