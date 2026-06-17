from pathlib import Path


FRAMEWORK_ROOT = Path("/app/workspace/framework")
TARGETS = [
    ("internal_notes", "segment-cache-audit", "md", 180),
    ("src/compat", "define-env-plugin.legacy", "ts", 180),
    ("src/diagnostics", "next-server.audit", "ts", 180),
    ("src/generated", "module.compiled.experimental", "js", 180),
    ("src/legacy", "runtime-bundle-plan.legacy", "ts", 180),
    ("src/probes", "taskfile.bundle-probe", "ts", 180),
]


for relative_dir, prefix, extension, count in TARGETS:
    directory = FRAMEWORK_ROOT / relative_dir
    directory.mkdir(parents=True, exist_ok=True)
    for index in range(1, count + 1):
        target = directory / f"{prefix}-{index}.{extension}"
        target.write_text(
            "\n".join(
                [
                    f"// generated decoy {index}",
                    "export const note = {",
                    f'  file: "{prefix}-{index}.{extension}",',
                    '  feature: "segmentCache",',
                    '  status: "audit-only"',
                    "};",
                    "",
                ]
            )
            + "\n",
            encoding="utf-8",
        )
