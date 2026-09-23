You need to prepare `/workspace/pkgmeta-kit` as a releasable Python distribution for the release engineering team.

Input data is in:
- `/workspace/pkgmeta-kit/data/licenses.json`
- `/workspace/pkgmeta-kit/data/trove_classifiers.py`
- `/workspace/pkgmeta-kit/contracts/cli_contract.json`
- `/workspace/pkgmeta-kit/contracts/automation_contract.json`

Your task:
1. Make `/workspace/pkgmeta-kit` buildable from the repository root for Python 3.12, produce both a wheel and a source distribution, and ensure both artifacts install cleanly in a fresh Python 3.12 environment.
2. Ensure the delivered package provides the `pkgmeta-kit` command and also supports `python -m pkgmeta_kit`.
3. Ensure the packaged application can read the required catalog data after installation.
4. Keep the CLI behavior defined in `/workspace/pkgmeta-kit/contracts/cli_contract.json`.
5. Ensure downstream release automation can discover the installed package callable defined in `/workspace/pkgmeta-kit/contracts/automation_contract.json`.
6. Ensure downstream Python 3.12 tooling can import the installed package root directly instead of relying on internal implementation paths.
7. Write `/workspace/out/release_manifest.json` as a JSON object with these fields:
   - `package_name`
   - `version`
   - `build_backend`
   - `python_requires`
   - `console_entrypoint`
   - `produced_artifacts`
   - `artifact_sha256`
   - `shipped_data_files`

Output:
- `dist/*.whl`
- `dist/*.tar.gz`
- `/workspace/out/release_manifest.json`

Notes:
- `produced_artifacts` must be a JSON array of artifact filenames.
- `artifact_sha256` must be a JSON object keyed by artifact filename.
- `shipped_data_files` must be a JSON array of package-relative paths.
- Do not upload anything to PyPI or any other package registry.
- Do not require interactive login, tokens, browser-based steps, or external publishing permissions.
- Do not replace the provided catalog files with alternate copies.
- Keep your work inside `/workspace/pkgmeta-kit` and `/workspace/out`.
