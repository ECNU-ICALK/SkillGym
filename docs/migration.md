# Data Release Migration

The large `skill_library/` and `task_templates/` trees have moved out of Git history and into the [SkillGym Hugging Face dataset](https://huggingface.co/datasets/ecnu-icalk/SkillGym). This keeps GitHub focused on the construction code and documentation while preserving reproducible snapshots.

## HF archives

Download these files from the dataset repository:

| Archive | Restored path |
| --- | --- |
| `skill_library.tar.zst` | `skill_library/` |
| `task_templates.tar.zst` | `task_templates/` |

The archives preserve the source tree at GitHub commit `6ebabba67ca449cb04c87085a30fe78096eb99b3`. See [`migration_manifest.json`](https://huggingface.co/datasets/ecnu-icalk/SkillGym/blob/main/migration_manifest.json) for byte sizes and SHA-256 checksums.

From the repository root:

```bash
hf download ecnu-icalk/SkillGym skill_library.tar.zst task_templates.tar.zst \
  --repo-type dataset --local-dir .hf/skillgym
tar --zstd -xf .hf/skillgym/skill_library.tar.zst
tar --zstd -xf .hf/skillgym/task_templates.tar.zst
```

## Path behavior

Once extracted, the existing builder defaults continue to resolve `<repository>/task_templates` and `<repository>/outputs`. Explicit `--template-root`, `--skill-dir`, and `--output-root` arguments remain supported.

`Trajectories/` is deliberately unchanged in this migration. Its eight JSONL files remain tracked by Git LFS in GitHub and can be fetched separately with `git lfs pull --include="Trajectories/*.jsonl"`.

## Checks

Run the commands in the README's Development Checks section after extracting the archives. CI checks code and path references without downloading the large HF archives or trajectory objects.
