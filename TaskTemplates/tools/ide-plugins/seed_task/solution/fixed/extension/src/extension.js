const path = require("path");
const vscode = require("vscode");
const {
  buildBriefings,
  getReleaseIndex,
  normalizeLocale,
  resolveOutputRoot,
  renderReleaseNote
} = require("./core");

class ReleaseTreeProvider {
  constructor(dataRoot) {
    this.dataRoot = dataRoot;
    this._onDidChangeTreeData = new vscode.EventEmitter();
    this.onDidChangeTreeData = this._onDidChangeTreeData.event;
  }

  getChildren() {
    const releases = getReleaseIndex(this.dataRoot);
    return releases.map((release) => {
      const item = new vscode.TreeItem(
        `VS Code ${release.version}`,
        vscode.TreeItemCollapsibleState.None
      );
      item.description = vscode.l10n.t("{0} highlights", release.highlightCount);
      item.command = {
        command: "releaseBriefing.openReleaseNote",
        title: vscode.l10n.t("Open release note"),
        arguments: [release.version]
      };
      return item;
    });
  }

  refresh() {
    this._onDidChangeTreeData.fire();
  }
}

function activate(context) {
  const extensionRoot = path.resolve(__dirname, "..");
  const dataRoot = process.env.RELEASE_BRIEFING_DATA_ROOT || "/app/data";
  const outputRoot = process.env.RELEASE_BRIEFING_OUTPUT_ROOT || "/app/workspace/output";
  const treeProvider = new ReleaseTreeProvider(dataRoot);

  context.subscriptions.push(
    vscode.window.registerTreeDataProvider("releaseBriefing.releases", treeProvider)
  );

  context.subscriptions.push(
    vscode.commands.registerCommand("releaseBriefing.exportBriefings", async () => {
      const workspaceRoot =
        vscode.workspace.workspaceFolders?.[0]?.uri.fsPath || path.resolve(extensionRoot, "..");
      const outputFolder = vscode.workspace
        .getConfiguration("releaseBriefing")
        .get("outputFolder", "output");
      const outputRoot = resolveOutputRoot({ workspaceRoot, outputFolder });

      vscode.window.setStatusBarMessage(vscode.l10n.t("Export started."), 3000);
      const files = buildBriefings({ extensionRoot, dataRoot, outputRoot });
      const message = vscode.l10n.t(
        "Exported {0} briefing files to {1}.",
        files.length,
        outputRoot
      );
      vscode.window.showInformationMessage(message);
    })
  );

  context.subscriptions.push(
    vscode.commands.registerCommand("releaseBriefing.refreshReleaseIndex", async () => {
      treeProvider.refresh();
      vscode.window.setStatusBarMessage(vscode.l10n.t("Release list refreshed."), 2500);
    })
  );

  context.subscriptions.push(
    vscode.commands.registerCommand("releaseBriefing.openReleaseNote", async (version) => {
      const locale = normalizeLocale(
        vscode.workspace
          .getConfiguration("releaseBriefing")
          .get("defaultLocale", vscode.env.language)
      );
      const content = renderReleaseNote(version, locale, dataRoot, extensionRoot);
      const document = await vscode.workspace.openTextDocument({
        content,
        language: "markdown"
      });
      await vscode.window.showTextDocument(document, { preview: false });
    })
  );
}

function deactivate() {}

module.exports = {
  activate,
  deactivate
};
