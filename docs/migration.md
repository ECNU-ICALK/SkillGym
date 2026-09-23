# Data Release Migration

The large `skill_library/`, `task_templates/`, and `Trajectories/` data releases are hosted in the [SkillGym Hugging Face dataset](https://huggingface.co/datasets/ecnu-icalk/SkillGym). GitHub now contains the construction code, documentation, and lightweight assets.

## HF files

| HF path | Local use |
| --- | --- |
| `skill_library.tar.zst` | Extract to `skill_library/` |
| `task_templates.tar.zst` | Extract to `task_templates/` |
| `Trajectories/*.jsonl` | Keep under `.hf/skillgym/Trajectories/` or copy as needed |

The two archives and eight trajectory files preserve the local release snapshot corresponding to GitHub commit `6ebabba67ca449cb04c87085a30fe78096eb99b3`. File sizes and SHA-256 checksums are available from the corresponding file metadata on the Hugging Face Hub.

## Download

From the repository root:

```bash
hf download ecnu-icalk/SkillGym \
  skill_library.tar.zst task_templates.tar.zst \
  --repo-type dataset --local-dir .hf/skillgym
hf download ecnu-icalk/SkillGym \
  --include "Trajectories/*.jsonl" \
  --repo-type dataset --local-dir .hf/skillgym
tar --zstd -xf .hf/skillgym/skill_library.tar.zst
tar --zstd -xf .hf/skillgym/task_templates.tar.zst
```

The trajectory filenames use explicit result labels:

- `skill_dependent_<harness>_<teacher>.jsonl`
- `verifier_passed_fallback_<harness>_<teacher>.jsonl`

The four harness/model pairs are Claude Code with DeepSeek V4 Pro or GLM-5.2, and Codex with GPT-5.4 or Nex-N2-Pro.

## Path behavior

After extraction, the builder defaults resolve `<repository>/task_templates` and `<repository>/outputs`. Explicit `--template-root`, `--skill-dir`, and `--output-root` arguments remain supported.

## Checks

Run the commands in the [Task Builder guide](../task_builder/README.md) after extracting the archives. CI checks code and documentation without downloading the HF data files.
