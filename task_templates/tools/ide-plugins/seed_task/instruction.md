You are completing a VS Code extension that turns a release-notes workspace into a localized briefing tool. The repository already includes official update snapshots, locale assets, and a partial extension scaffold. Your job is to finish the extension and its packaging flow without changing the provided input data.

Input data is in:
- `/app/workspace/extension`: the extension scaffold, including commands, a view container, onboarding placeholders, and packaging scripts
- `/app/data/releases/`: official VS Code update snapshots for versions 1.87, 1.88, and 1.89
- `/app/data/locales/`: locale assets for `en`, `pt-br`, and `zh-cn`
- `/app/data/briefing_request.json`: the versions, focus areas, and output contract for this briefing run

Your task
1. Complete the extension so users can browse the provided update snapshots from the existing Activity Bar entry and open per-release notes inside VS Code.
2. Complete the extension's multi-language delivery for `en`, `pt-br`, and `zh-cn` across browsing, export, and packaging.
3. Add or finish the export flow so the workspace writes the required Markdown briefings into `/app/workspace/output/`.
4. Keep the extension buildable and locally distributable so the repository can generate one `.vsix` package from the provided codebase.

Output:
- Update the extension code under `/app/workspace/extension`
- Produce `/app/workspace/output/release-briefing.en.md`
- Produce `/app/workspace/output/release-briefing.pt-br.md`
- Produce `/app/workspace/output/release-briefing.zh-cn.md`
- Produce one `.vsix` package under `/app/workspace/output/`

Notes:
- Use the provided local update snapshots and locale assets.
- Keep the delivered language content aligned with the provided locale assets and the extension's shipped language resources, including section headings, release-note labels, footer/generator copy, and onboarding guidance.
- Keep exported briefings and opened release notes driven by those provided language assets so summary wording, scoped highlight labels, and localized UI wording stay in step across locales.
- Keep the current extension entrypoints, workspace layout, and packaging flow.
- You may add dependencies if they support the extension workflow.
- Do not modify files under `/app/data/`.
- Do not rely on sign-in, publish tokens, online translation services, or external APIs during solve.
- Do not turn the task into a standalone website, a terminal-only exporter, or hand-written static output files.
- Do not reduce the task to a single locale, a single release, or a single request shape.
