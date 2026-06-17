---
name: discovering-make-commands
description: Lists available make commands for Streamlit development. Use for build, test, lint, or format tasks.
---

# Available `make` commands

List of all `make` commands available for execution from the repository root folder:

```text
help                      Show all available make commands.
all                       Install all dependencies, build frontend, and install editable Streamlit.
all-dev                   Install all dependencies and editable Streamlit, but do not build the frontend.
init                      Install all dependencies and build protobufs.
clean                     Remove all generated files.
protobuf                  Recompile Protobufs for Python and the frontend.
protobuf-lint             Lint and check formatting of protobuf files (buf).
protobuf-format           Format protobuf files (buf).
python-init               Install Python dependencies and Streamlit in editable mode.
python-lint               Lint and check formatting of Python files.
python-format             Format Python files.
python-tests              Run Python unit tests.
python-performance-tests  Run Python performance tests.
python-integration-tests  Run Python integration tests. Requires `uv sync --group integration` to be run first.
python-types              Run the Python type checker.
frontend-init             Install all frontend dependencies.
frontend                  Build the frontend.
frontend-with-profiler    Build the frontend with the profiler enabled.
frontend-fast             Build the frontend (as fast as possible).
frontend-dev              Start the frontend development server.
debug                     Start Streamlit and Vite dev server for debugging. Use via `make debug my-script.py`.
frontend-lint             Lint and check formatting of frontend files.
frontend-types            Run the frontend type checker.
frontend-format           Format frontend files.
frontend-tests            Run frontend unit tests and generate coverage report.
e2e-tests                 Run all Playwright tests. Use via `make e2e-tests TEST_ARGS='path/to/file.test.ts'`.
e2e-tests-fast            Run all Playwright tests without installation, typechecks or webpack build.
e2e-tests-dev            Run all Playwright tests against live local dev servers.
e2e-tests-coverage        Run all Playwright tests with JavaScript coverage.
e2e-tests-update-snapshots  Run all Playwright tests and update snapshots.
e2e-tests-chromium        Run Playwright tests on Chromium only.
e2e-tests-webkit          Run Playwright tests on WebKit only.
e2e-tests-firefox         Run Playwright tests on Firefox only.
e2e-tests-mobile          Run Playwright tests on mobile viewports.
e2e-tests-snowflake       Run Playwright tests with Snowflake partner features enabled.
e2e-tests-record          Run Playwright tests in record mode.
e2e-tests-debug           Run Playwright tests in debug mode.
lighthouse-tests          Run Lighthouse performance tests.
bare-execution-tests      Run all e2e tests in bare mode.
cli-smoke-tests           Run CLI smoke tests.
check                     Run all checks (format, lint, types, unit tests) on changed files only. Useful to verify the current state of the codebase before committing.
autofix                   Autofix linting and formatting errors.
package                   Create Python wheel files in `dist/`.
```
