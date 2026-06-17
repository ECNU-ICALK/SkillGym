## What's Changed
* chore(release): bump version to 0.40.0-nightly.20260414.g5b1f7375a by @gemini-cli-robot in https://github.com/google-gemini/gemini-cli/pull/25420
* Fix(core): retry additional OpenSSL 3.x SSL errors during streaming (#16075) by @rcleveng in https://github.com/google-gemini/gemini-cli/pull/25187
* fix(core): prevent YOLO mode from being downgraded by @galz10 in https://github.com/google-gemini/gemini-cli/pull/25341
* feat: bundle ripgrep binaries into SEA for offline support by @scidomino in https://github.com/google-gemini/gemini-cli/pull/25342
* Changelog for v0.39.0-preview.0 by @gemini-cli-robot in https://github.com/google-gemini/gemini-cli/pull/25417
* feat(test): add large conversation scenario for performance test by @cynthialong0-0 in https://github.com/google-gemini/gemini-cli/pull/25331
* improve(core): require recurrence evidence before extracting skills by @SandyTao520 in https://github.com/google-gemini/gemini-cli/pull/25147
* test(evals): add subagent delegation evaluation tests by @anj-s in https://github.com/google-gemini/gemini-cli/pull/24619
* feat: add github colorblind themes by @Z1xus in https://github.com/google-gemini/gemini-cli/pull/15504
* fix(core): honor GOOGLE_GEMINI_BASE_URL and GOOGLE_VERTEX_BASE_URL by @chrisjcthomas in https://github.com/google-gemini/gemini-cli/pull/25357
* fix(cli): clean up slash command IDE listeners by @jasonmatthewsuhari in https://github.com/google-gemini/gemini-cli/pull/24397
* Changelog for v0.38.0 by @gemini-cli-robot in https://github.com/google-gemini/gemini-cli/pull/25470
* fix(evals): update eval tests for invoke_agent telemetry and project-scoped memory by @SandyTao520 in https://github.com/google-gemini/gemini-cli/pull/25502
* Changelog for v0.38.1 by @gemini-cli-robot in https://github.com/google-gemini/gemini-cli/pull/25476
* feat(core): integrate skill-creator into skill extraction agent by @SandyTao520 in https://github.com/google-gemini/gemini-cli/pull/25421
* feat(cli): provide default post-submit prompt for skill command by @ruomengz in https://github.com/google-gemini/gemini-cli/pull/25327
* feat(core): add tools to list and read MCP resources by @ruomengz in https://github.com/google-gemini/gemini-cli/pull/25395
* fix(evals): add typecheck coverage for evals, integration-tests, and memory-tests by @SandyTao520 in https://github.com/google-gemini/gemini-cli/pull/25480
* Use OSC 777 for terminal notifications by @jackyliuxx in https://github.com/google-gemini/gemini-cli/pull/25300
* fix(extensions): fix bundling for examples by @abhipatel12 in https://github.com/google-gemini/gemini-cli/pull/25542
* fix(cli): reset plan session state on /clear by @jasonmatthewsuhari in https://github.com/google-gemini/gemini-cli/pull/25515
* feat(core): add .mdx support to get-internal-docs tool by @g-samroberts in https://github.com/google-gemini/gemini-cli/pull/25090
* docs(policy): mention that workspace policies are broken by @6112 in https://github.com/google-gemini/gemini-cli/pull/24367
* fix(core): allow explicit write permissions to override governance file protections in sandboxes by @galz10 in https://github.com/google-gemini/gemini-cli/pull/25338
* feat(sandbox): resolve custom seatbelt profiles from $HOME/.gemini first by @mvanhorn in https://github.com/google-gemini/gemini-cli/pull/25427
* Reduce blank lines. by @gundermanc in https://github.com/google-gemini/gemini-cli/pull/25563
* fix(ui): revert preview theme on dialog unmount by @JayadityaGit in https://github.com/google-gemini/gemini-cli/pull/22542
* fix(core): fix ShellExecutionConfig spread and add ProjectRegistry save backoff by @mahimashanware in https://github.com/google-gemini/gemini-cli/pull/25382
* feat(core): Disable topic updates for subagents by @gundermanc in https://github.com/google-gemini/gemini-cli/pull/25567
* feat(core): enable topic update narration by default and promote to general by @gundermanc in https://github.com/google-gemini/gemini-cli/pull/25586
* docs: migrate installation and authentication to mdx with tabbed layouts by @g-samroberts in https://github.com/google-gemini/gemini-cli/pull/25155
* feat(config): split memoryManager flag into autoMemory by @SandyTao520 in https://github.com/google-gemini/gemini-cli/pull/25601
* fix(core): allow Cloud Shell users to use PRO_MODEL_NO_ACCESS experiment by @sehoon38 in https://github.com/google-gemini/gemini-cli/pull/25702
* fix(cli): round slow render latency to avoid opentelemetry float warning by @scidomino in https://github.com/google-gemini/gemini-cli/pull/25709
* docs(tracker): introduce experimental task tracker feature by @anj-s in https://github.com/google-gemini/gemini-cli/pull/24556
* docs(cli): fix inconsistent system.md casing in system prompt docs by @Bodlux in https://github.com/google-gemini/gemini-cli/pull/25414
* feat(cli): add streamlined `gemini gemma` local model setup by @Samee24 in https://github.com/google-gemini/gemini-cli/pull/25498
* Changelog for v0.38.2 by @gemini-cli-robot in https://github.com/google-gemini/gemini-cli/pull/25593
* Fix: Disallow overriding IDE stdio via workspace .env (RCE) by @M0nd0R in https://github.com/google-gemini/gemini-cli/pull/25022
* feat(test): refactor the memory usage test to use metrics from CLI process instead of test runner by @cynthialong0-0 in https://github.com/google-gemini/gemini-cli/pull/25708
* feat(vertex): add settings for Vertex AI request routing by @gordonhwc in https://github.com/google-gemini/gemini-cli/pull/25513
* Fix/allow for session persistence by @ahsanfarooq210 in https://github.com/google-gemini/gemini-cli/pull/25176
* Allow dots on GEMINI_API_KEY by @DKbyo in https://github.com/google-gemini/gemini-cli/pull/25497
* feat(telemetry): add flag for enabling traces specifically by @spencer426 in https://github.com/google-gemini/gemini-cli/pull/25343
* fix(core): resolve nested plan directory duplication and relative path policies by @mahimashanware in https://github.com/google-gemini/gemini-cli/pull/25138
* feat: detect new files in @ recommendations with watcher based updates by @prassamin in https://github.com/google-gemini/gemini-cli/pull/25256
* fix(cli): use newline in shell command wrapping to avoid breaking heredocs by @cocosheng-g in https://github.com/google-gemini/gemini-cli/pull/25537
* fix(cli): ensure theme dialog labels are rendered for all themes by @JayadityaGit in https://github.com/google-gemini/gemini-cli/pull/24599
* fix(core): disable detached mode in Bun to prevent immediate SIGHUP of child processes by @euxaristia in https://github.com/google-gemini/gemini-cli/pull/22620
* feat: add /new as alias for /clear and refine command description by @ved015 in https://github.com/google-gemini/gemini-cli/pull/17865
* fix(cli): start auto memory in ACP sessions by @jasonmatthewsuhari in https://github.com/google-gemini/gemini-cli/pull/25626
* fix(core): remove duplicate initialize call on agents refreshed by @adamfweidman in https://github.com/google-gemini/gemini-cli/pull/25670
* test(e2e): default integration tests to Flash Preview by @SandyTao520 in https://github.com/google-gemini/gemini-cli/pull/25753
* refactor(memory): replace MemoryManagerAgent with prompt-driven memory editing across four tiers by @SandyTao520 in https://github.com/google-gemini/gemini-cli/pull/25716
* fix(cli): fix "/clear (new)" command by @mini2s in https://github.com/google-gemini/gemini-cli/pull/25801
* fix(core): use dynamic CLI version for IDE client instead of hardcoded '1.0.0' by @thekishandev in https://github.com/google-gemini/gemini-cli/pull/24414
* fix(core): handle line endings in ignore file parsing by @xoma-zver in https://github.com/google-gemini/gemini-cli/pull/23895
* Fix/command injection shell by @Famous077 in https://github.com/google-gemini/gemini-cli/pull/24170
* fix(ui): removed background color for input by @devr0306 in https://github.com/google-gemini/gemini-cli/pull/25339
* fix(devtools): reduce memory usage and defer connection by @SandyTao520 in https://github.com/google-gemini/gemini-cli/pull/24496
* fix(core): support jsonl session logs in memory and summary services by @SandyTao520 in https://github.com/google-gemini/gemini-cli/pull/25816
* fix(release): exclude ripgrep binaries from npm tarballs by @SandyTao520 in https://github.com/google-gemini/gemini-cli/pull/25841
* fix(patch): cherry-pick 048bf6e to release/v0.40.0-preview.3-pr-25941 to patch version v0.40.0-preview.3 and create version 0.40.0-preview.4 by @gemini-cli-robot in https://github.com/google-gemini/gemini-cli/pull/25942
* fix(patch): cherry-pick 54b7586 to release/v0.40.0-preview.4-pr-26066 [CONFLICTS] by @gemini-cli-robot in https://github.com/google-gemini/gemini-cli/pull/26124

## New Contributors
* @rcleveng made their first contribution in https://github.com/google-gemini/gemini-cli/pull/25187
* @Z1xus made their first contribution in https://github.com/google-gemini/gemini-cli/pull/15504
* @jackyliuxx made their first contribution in https://github.com/google-gemini/gemini-cli/pull/25300
* @6112 made their first contribution in https://github.com/google-gemini/gemini-cli/pull/24367
* @mvanhorn made their first contribution in https://github.com/google-gemini/gemini-cli/pull/25427
* @Bodlux made their first contribution in https://github.com/google-gemini/gemini-cli/pull/25414
* @M0nd0R made their first contribution in https://github.com/google-gemini/gemini-cli/pull/25022
* @gordonhwc made their first contribution in https://github.com/google-gemini/gemini-cli/pull/25513
* @ahsanfarooq210 made their first contribution in https://github.com/google-gemini/gemini-cli/pull/25176
* @DKbyo made their first contribution in https://github.com/google-gemini/gemini-cli/pull/25497
* @prassamin made their first contribution in https://github.com/google-gemini/gemini-cli/pull/25256
* @mini2s made their first contribution in https://github.com/google-gemini/gemini-cli/pull/25801
* @thekishandev made their first contribution in https://github.com/google-gemini/gemini-cli/pull/24414
* @xoma-zver made their first contribution in https://github.com/google-gemini/gemini-cli/pull/23895

**Full Changelog**: https://github.com/google-gemini/gemini-cli/compare/v0.39.1...v0.40.0
