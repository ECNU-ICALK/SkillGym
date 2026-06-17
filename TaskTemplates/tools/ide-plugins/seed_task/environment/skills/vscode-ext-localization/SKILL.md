---
name: vscode-ext-localization
description: Localize VS Code extension contributions, walkthrough content, and runtime strings across supported languages.
---

# VS Code Extension Localization

Use this skill when you need to localize new or existing VS Code extension contributions such as settings, commands, menus, views, walkthroughs, or user-visible strings in source files.

When localizing a VS Code extension, keep these resource surfaces aligned:

1. `package.json` contributions through `package.nls.json` and `package.nls.<locale>.json`
2. walkthrough markdown content through locale-specific markdown files
3. runtime user-visible strings through `bundle.l10n.json` and `bundle.l10n.<locale>.json`

For runtime strings, keep the base English `bundle.l10n.json` keys identical to the English source strings used in code, and mirror that same keyset in every locale file.

Each time you add or update a localizable resource, update every supported language in the extension.
