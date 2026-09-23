from __future__ import annotations

import json
import os
import shutil
import subprocess
import tempfile
import zipfile
from pathlib import Path

WORKSPACE_ROOT = Path(os.environ.get("WORKSPACE_ROOT", "/app/workspace"))
EXTENSION_ROOT = WORKSPACE_ROOT / "extension"
OUTPUT_ROOT = WORKSPACE_ROOT / "output"
DATA_ROOT = Path(os.environ.get("DATA_ROOT", "/app/data"))
TESTS_ROOT = Path(os.environ.get("TESTS_ROOT", "/tests"))
SUPPORTED_LOCALES = ["en", "pt-br", "zh-cn"]


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, payload: dict) -> None:
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def locale_manifest(extension_root: Path, locale: str) -> dict:
    file_name = "package.nls.json" if locale == "en" else f"package.nls.{locale}.json"
    return read_json(extension_root / file_name)


def walkthrough_markdown_path(extension_root: Path, payload: dict, key: str) -> Path:
    relative_path = payload[key].removeprefix("./")
    return extension_root / relative_path


def locale_copy_path(data_root: Path, locale: str) -> Path:
    return data_root / "locales" / locale / "extension_copy.json"


def prepare_variant_copy(temp_dir: str) -> tuple[Path, Path, Path]:
    temp_root = Path(temp_dir)
    variant_root = temp_root / "data"
    variant_extension_root = temp_root / "extension"
    output_root = temp_root / "output"

    shutil.copytree(DATA_ROOT, variant_root)
    shutil.copytree(
        EXTENSION_ROOT,
        variant_extension_root,
        ignore=shutil.ignore_patterns("node_modules"),
    )
    node_modules = EXTENSION_ROOT / "node_modules"
    if node_modules.exists():
        os.symlink(node_modules, variant_extension_root / "node_modules", target_is_directory=True)

    output_root.mkdir(parents=True, exist_ok=True)

    return variant_root, variant_extension_root, output_root


def run_node(script: str, *, cwd: Path, env: dict[str, str]) -> str:
    completed = subprocess.run(
        ["node", "-e", script],
        check=True,
        cwd=cwd,
        env=env,
        capture_output=True,
        text=True,
    )
    return completed.stdout


def run_npm_pipeline(extension_root: Path, data_root: Path, output_root: Path) -> None:
    env = os.environ.copy()
    env["RELEASE_BRIEFING_DATA_ROOT"] = data_root.as_posix()
    env["RELEASE_BRIEFING_OUTPUT_ROOT"] = output_root.as_posix()
    for command in ["build", "export", "package"]:
        subprocess.run(["npm", "run", command], check=True, cwd=extension_root, env=env)


def expected_vsix_members(extension_root: Path) -> set[str]:
    members = {
        "extension/package.nls.json",
        "extension/package.nls.pt-br.json",
        "extension/package.nls.zh-cn.json",
        "extension/l10n/bundle.l10n.json",
        "extension/l10n/bundle.l10n.pt-br.json",
        "extension/l10n/bundle.l10n.zh-cn.json",
    }
    for locale in SUPPORTED_LOCALES:
        payload = locale_manifest(extension_root, locale)
        for key in [
            "walkthrough.step.browse.markdown",
            "walkthrough.step.export.markdown",
            "walkthrough.step.package.markdown",
        ]:
            members.add(f"extension/{payload[key].removeprefix('./')}")
    return members


def test_default_outputs_exist() -> None:
    expected = [
        OUTPUT_ROOT / "release-briefing.en.md",
        OUTPUT_ROOT / "release-briefing.pt-br.md",
        OUTPUT_ROOT / "release-briefing.zh-cn.md",
        OUTPUT_ROOT / "release-briefing-extension.vsix",
    ]
    missing = [str(path) for path in expected if not path.exists()]
    assert not missing, f"missing output artifacts: {missing}"


def test_markdown_outputs_are_localized() -> None:
    en = read_text(OUTPUT_ROOT / "release-briefing.en.md")
    pt = read_text(OUTPUT_ROOT / "release-briefing.pt-br.md")
    zh = read_text(OUTPUT_ROOT / "release-briefing.zh-cn.md")

    assert "# VS Code Release Briefing" in en
    assert "## Overview" in en and "## Highlights" in en and "## Action items" in en
    assert "Local workspace extensions preview" in en
    assert "> Generated with: Release Briefing Explorer" in en

    assert "# Resumo de Atualizações do VS Code" in pt
    assert "## Visão geral" in pt and "## Destaques" in pt and "## Ações" in pt
    assert "Prévia de extensões locais de workspace" in pt
    assert "Gerado com" in pt

    assert "# VS Code 更新简报" in zh
    assert "## 概览" in zh and "## 重点" in zh and "## 行动项" in zh
    assert "本地工作区扩展预览" in zh
    assert "生成工具" in zh


def test_manifest_uses_tokenized_localization_surfaces() -> None:
    manifest = read_json(EXTENSION_ROOT / "package.json")
    command_ids = {command["command"] for command in manifest["contributes"]["commands"]}
    activation_events = set(manifest["activationEvents"])
    view_title_commands = {
        item["command"] for item in manifest["contributes"].get("menus", {}).get("view/title", [])
    }

    assert manifest["displayName"].startswith("%")
    assert manifest["description"].startswith("%")
    assert command_ids == {
        "releaseBriefing.exportBriefings",
        "releaseBriefing.refreshReleaseIndex",
        "releaseBriefing.openReleaseNote",
    }
    assert manifest["contributes"]["commands"][0]["title"].startswith("%")
    assert manifest["contributes"]["viewsContainers"]["activitybar"][0]["title"].startswith("%")
    assert manifest["contributes"]["views"]["releaseBriefing"][0]["name"].startswith("%")
    assert "onCommand:releaseBriefing.refreshReleaseIndex" in activation_events
    assert manifest["contributes"]["walkthroughs"][0]["steps"][0]["media"]["markdown"].startswith("%")
    assert manifest["contributes"]["walkthroughs"][0]["steps"][1]["media"]["markdown"].startswith("%")
    assert manifest["contributes"]["walkthroughs"][0]["steps"][2]["media"]["markdown"].startswith("%")
    assert "releaseBriefing.refreshReleaseIndex" in view_title_commands


def test_packaged_vsix_contains_localization_assets() -> None:
    vsix_path = OUTPUT_ROOT / "release-briefing-extension.vsix"
    with zipfile.ZipFile(vsix_path) as archive:
        members = set(archive.namelist())

    missing = sorted(expected_vsix_members(EXTENSION_ROOT) - members)
    assert not missing, f"vsix is missing localized assets: {missing}"


def test_variant_request_changes_selected_content() -> None:
    variant_request = TESTS_ROOT / "fixtures" / "briefing_request_variant.json"
    with tempfile.TemporaryDirectory() as temp_dir:
        env = os.environ.copy()
        env["RELEASE_BRIEFING_DATA_ROOT"] = DATA_ROOT.as_posix()
        env["RELEASE_BRIEFING_OUTPUT_ROOT"] = temp_dir
        node_script = f"""
const {{ buildBriefings }} = require("{(EXTENSION_ROOT / 'src' / 'core.js').as_posix()}");
buildBriefings({{
  extensionRoot: "{EXTENSION_ROOT.as_posix()}",
  dataRoot: "{DATA_ROOT.as_posix()}",
  outputRoot: "{Path(temp_dir).as_posix()}",
  requestPath: "{variant_request.as_posix()}"
}});
"""
        run_node(node_script, cwd=EXTENSION_ROOT, env=env)
        content = read_text(Path(temp_dir) / "release-briefing.en.md")

    assert "VS Code Workspace Extension Briefing" in content
    assert "VS Code 1.87" not in content
    assert "Webview and custom editor support for floating windows" in content
    assert "Accessibility help for extension-contributed views" in content
    assert "Language model access control for extensions" not in content


def test_locale_term_assets_drive_localized_outputs() -> None:
    with tempfile.TemporaryDirectory() as temp_dir:
        variant_root, variant_extension_root, output_root = prepare_variant_copy(temp_dir)

        pt_terms_path = variant_root / "locales" / "pt-br" / "briefing_terms.json"
        zh_terms_path = variant_root / "locales" / "zh-cn" / "briefing_terms.json"
        pt_terms = read_json(pt_terms_path)
        zh_terms = read_json(zh_terms_path)

        pt_terms["summary_template"] = "Resumo validado para {audience}"
        pt_terms["focus_names"]["views"] = "Views em validacao"
        zh_terms["summary_template"] = "这是面向{audience}的校验简报"
        zh_terms["focus_names"]["views"] = "视图校验项"
        write_json(pt_terms_path, pt_terms)
        write_json(zh_terms_path, zh_terms)

        env = os.environ.copy()
        env["RELEASE_BRIEFING_DATA_ROOT"] = variant_root.as_posix()
        env["RELEASE_BRIEFING_OUTPUT_ROOT"] = output_root.as_posix()
        node_script = f"""
const {{ buildBriefings }} = require("{(variant_extension_root / 'src' / 'core.js').as_posix()}");
buildBriefings({{
  extensionRoot: "{variant_extension_root.as_posix()}",
  dataRoot: "{variant_root.as_posix()}",
  outputRoot: "{output_root.as_posix()}"
}});
"""
        run_node(node_script, cwd=variant_extension_root, env=env)

        pt_output = read_text(output_root / "release-briefing.pt-br.md")
        zh_output = read_text(output_root / "release-briefing.zh-cn.md")
        en_output = read_text(output_root / "release-briefing.en.md")

    assert "Resumo validado para" in pt_output
    assert "Views em validacao" in pt_output
    assert "这是面向" in zh_output
    assert "视图校验项" in zh_output
    assert "Resumo validado para" not in en_output
    assert "这是面向" not in en_output


def test_locale_copy_assets_drive_synced_extension_resources() -> None:
    with tempfile.TemporaryDirectory() as temp_dir:
        variant_root, variant_extension_root, output_root = prepare_variant_copy(temp_dir)

        pt_copy_path = locale_copy_path(variant_root, "pt-br")
        zh_copy_path = locale_copy_path(variant_root, "zh-cn")
        pt_copy = read_json(pt_copy_path)
        zh_copy = read_json(zh_copy_path)

        pt_copy["package"]["command.export.title"] = "Exportar entregas validadas"
        pt_copy["package"]["walkthrough.step.package.title"] = "Entrega VSIX validada"
        pt_copy["package"]["walkthrough.step.package.markdown"] = "./resources/walkthrough/pt-br/package-check.md"
        pt_copy["bundle"]["Generated with"] = "Montado com"
        pt_copy["bundle"]["Release Briefing Explorer"] = "Explorador sincronizado"
        pt_copy["walkthrough"]["package"] = (
            "# Entrega VSIX validada\n\n"
            "Confirme que o pacote sincronizado inclui o manifesto e os bundles localizados.\n"
        )

        zh_copy["package"]["command.export.title"] = "导出校验产物"
        zh_copy["package"]["walkthrough.step.package.title"] = "打包校验步骤"
        zh_copy["package"]["walkthrough.step.package.markdown"] = "./resources/walkthrough/zh-cn/package-check.md"
        zh_copy["bundle"]["Generated with"] = "交付工具"
        zh_copy["bundle"]["Release Briefing Explorer"] = "版本简报浏览器"
        zh_copy["walkthrough"]["package"] = (
            "# 打包校验步骤\n\n"
            "确认同步后的 VSIX 同时包含本地化 manifest 与运行态 bundle。\n"
        )

        write_json(pt_copy_path, pt_copy)
        write_json(zh_copy_path, zh_copy)
        run_npm_pipeline(variant_extension_root, variant_root, output_root)

        pt_manifest = locale_manifest(variant_extension_root, "pt-br")
        zh_manifest = locale_manifest(variant_extension_root, "zh-cn")
        pt_package_markdown = walkthrough_markdown_path(
            variant_extension_root, pt_manifest, "walkthrough.step.package.markdown"
        )
        zh_package_markdown = walkthrough_markdown_path(
            variant_extension_root, zh_manifest, "walkthrough.step.package.markdown"
        )
        pt_output = read_text(output_root / "release-briefing.pt-br.md")
        zh_output = read_text(output_root / "release-briefing.zh-cn.md")

        assert pt_manifest["command.export.title"] == "Exportar entregas validadas"
        assert zh_manifest["command.export.title"] == "导出校验产物"
        assert pt_manifest["walkthrough.step.package.markdown"].endswith("package-check.md")
        assert zh_manifest["walkthrough.step.package.markdown"].endswith("package-check.md")
        assert "# Entrega VSIX validada" in read_text(pt_package_markdown)
        assert "# 打包校验步骤" in read_text(zh_package_markdown)
        assert "> Montado com: Explorador sincronizado" in pt_output
        assert "> 交付工具: 版本简报浏览器" in zh_output

        with zipfile.ZipFile(output_root / "release-briefing-extension.vsix") as archive:
            members = set(archive.namelist())

    assert "extension/resources/walkthrough/pt-br/package-check.md" in members
    assert "extension/resources/walkthrough/zh-cn/package-check.md" in members


def test_release_note_renderer_respects_synced_locale_assets() -> None:
    with tempfile.TemporaryDirectory() as temp_dir:
        variant_root, variant_extension_root, _ = prepare_variant_copy(temp_dir)

        pt_terms_path = variant_root / "locales" / "pt-br" / "briefing_terms.json"
        zh_terms_path = variant_root / "locales" / "zh-cn" / "briefing_terms.json"
        pt_copy_path = locale_copy_path(variant_root, "pt-br")
        zh_copy_path = locale_copy_path(variant_root, "zh-cn")

        pt_terms = read_json(pt_terms_path)
        zh_terms = read_json(zh_terms_path)
        pt_copy = read_json(pt_copy_path)
        zh_copy = read_json(zh_copy_path)

        pt_terms["focus_names"]["views"] = "Views em revisao"
        zh_terms["focus_names"]["views"] = "视图复核项"
        pt_copy["bundle"]["Highlights in briefing scope"] = "Destaques validados"
        pt_copy["bundle"]["Additional snapshot highlights"] = "Outros destaques validados"
        pt_copy["bundle"]["Focus: {0}"] = "Area validada: {0}"
        pt_copy["bundle"]["Recommended action: {0}"] = "Acao validada: {0}"
        zh_copy["bundle"]["Highlights in briefing scope"] = "范围内重点校验"
        zh_copy["bundle"]["Additional snapshot highlights"] = "其他重点校验项"
        zh_copy["bundle"]["Focus: {0}"] = "校验范围：{0}"
        zh_copy["bundle"]["Recommended action: {0}"] = "校验动作：{0}"

        write_json(pt_terms_path, pt_terms)
        write_json(zh_terms_path, zh_terms)
        write_json(pt_copy_path, pt_copy)
        write_json(zh_copy_path, zh_copy)

        env = os.environ.copy()
        env["RELEASE_BRIEFING_DATA_ROOT"] = variant_root.as_posix()
        node_script = f"""
const core = require("{(variant_extension_root / 'src' / 'core.js').as_posix()}");
const pt = core.renderReleaseNote(
  "1.88",
  "pt-BR",
  "{variant_root.as_posix()}",
  "{variant_extension_root.as_posix()}"
);
const zh = core.renderReleaseNote(
  "1.89",
  "zh-CN",
  "{variant_root.as_posix()}",
  "{variant_extension_root.as_posix()}"
);
console.log("===PT===");
console.log(pt);
console.log("===ZH===");
console.log(zh);
"""
        rendered = run_node(node_script, cwd=variant_extension_root, env=env)

    pt_output = rendered.split("===PT===\n", 1)[1].split("\n===ZH===\n", 1)[0]
    zh_output = rendered.split("\n===ZH===\n", 1)[1]

    assert "Views em revisao" in pt_output
    assert "视图复核项" in zh_output
    assert "Acao validada:" in pt_output
    assert "校验动作：" in zh_output
    assert "Destaques validados" in pt_output
    assert "范围内重点校验" in zh_output


def test_walkthrough_markdown_reuses_localized_entrypoints() -> None:
    for locale in SUPPORTED_LOCALES:
        payload = locale_manifest(EXTENSION_ROOT, locale)
        browse = read_text(walkthrough_markdown_path(EXTENSION_ROOT, payload, "walkthrough.step.browse.markdown"))
        export = read_text(walkthrough_markdown_path(EXTENSION_ROOT, payload, "walkthrough.step.export.markdown"))
        package = read_text(walkthrough_markdown_path(EXTENSION_ROOT, payload, "walkthrough.step.package.markdown"))

        assert payload["walkthrough.step.browse.title"] in browse
        assert "VS Code" in browse
        assert payload["walkthrough.step.export.title"] in export
        assert payload["walkthrough.step.package.title"] in package
        assert "VSIX" in package
        assert f'[{payload["command.export.title"]}](command:releaseBriefing.exportBriefings)' in payload["view.welcome"]


def test_release_note_renderer_separates_out_of_scope_highlights() -> None:
    env = os.environ.copy()
    env["RELEASE_BRIEFING_DATA_ROOT"] = DATA_ROOT.as_posix()
    node_script = f"""
const core = require("{(EXTENSION_ROOT / 'src' / 'core.js').as_posix()}");
const rendered = core.renderReleaseNote(
  "1.87",
  "en",
  "{DATA_ROOT.as_posix()}",
  "{EXTENSION_ROOT.as_posix()}"
);
console.log(rendered);
"""
    rendered = run_node(node_script, cwd=EXTENSION_ROOT, env=env)
    assert "Highlights in briefing scope" in rendered
    assert "Additional snapshot highlights" in rendered
    assert "FindFiles2 proposal for richer file queries" in rendered
    assert "Test coverage support for extension test runs" in rendered
