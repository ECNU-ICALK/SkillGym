## What's Changed
* chore(release): bump version to 0.41.0-nightly.20260423.gaa05b4583 by @gemini-cli-robot in https://github.com/google-gemini/gemini-cli/pull/25847
* fix(core): only show `list` suggestion if the partial input is empty by @cynthialong0-0 in https://github.com/google-gemini/gemini-cli/pull/25821
* feat(cli): secure .env loading and enforce workspace trust in headless mode by @ehedlund in https://github.com/google-gemini/gemini-cli/pull/25814
* fix: fatal hard-crash on loop detection via unhandled AbortError by @hsm207 in https://github.com/google-gemini/gemini-cli/pull/20108
* update package-lock.json by @ehedlund in https://github.com/google-gemini/gemini-cli/pull/25876
* feat(core): enhance shell command validation and add core tools allowlist by @galz10 in https://github.com/google-gemini/gemini-cli/pull/25720
* fix(ui): corrected background color check in user message components by @devr0306 in https://github.com/google-gemini/gemini-cli/pull/25880
* perf(core): fix slow boot by fetching experiments and quota asynchronously by @spencer426 in https://github.com/google-gemini/gemini-cli/pull/25758
* feat(core,cli): add support for Gemma 4 models (experimental) by @Abhijit-2592 in https://github.com/google-gemini/gemini-cli/pull/25604
* update FatalUntrustedWorkspaceError message to include doc link by @ehedlund in https://github.com/google-gemini/gemini-cli/pull/25874
* docs: add Gemini CLI course link to README by @JayadityaGit in https://github.com/google-gemini/gemini-cli/pull/25925
* feat(repo): add gemini-cli-bot metrics and workflows by @gundermanc in https://github.com/google-gemini/gemini-cli/pull/25888
* fix(cli): allow output redirection for cli commands by @spencer426 in https://github.com/google-gemini/gemini-cli/pull/25894
* fix(core): fail closed in YOLO mode when shell parsing fails for restricted rules by @ehedlund in https://github.com/google-gemini/gemini-cli/pull/25935
* fix(cli-ui): revert backspace handling to fix Windows regression by @scidomino in https://github.com/google-gemini/gemini-cli/pull/25941
* feat(voice): implement real-time voice mode with cloud and local backends by @Abhijit-2592 in https://github.com/google-gemini/gemini-cli/pull/24174
* Changelog for v0.39.0 by @gemini-cli-robot in https://github.com/google-gemini/gemini-cli/pull/25848
* feat(memory): persist auto-memory scratchpad for skill extraction by @SandyTao520 in https://github.com/google-gemini/gemini-cli/pull/25873
* fix(cli): add missing response key to custom theme text schema by @gaurav0107 in https://github.com/google-gemini/gemini-cli/pull/25822
* fix(cli): provide manual update command when automatic update fails by @cocosheng-g in https://github.com/google-gemini/gemini-cli/pull/26052
* test(cli): add unit tests for restore ACP command (#23402) by @cocosheng-g in https://github.com/google-gemini/gemini-cli/pull/26053
* fix(ui): better error messages for ECONNRESET and ETIMEDOUT by @devr0306 in https://github.com/google-gemini/gemini-cli/pull/26059
* feat(core): wire up the new ContextManager and AgentChatHistory by @joshualitt in https://github.com/google-gemini/gemini-cli/pull/25409
* fix(cli): ensure sandbox proxy cleanup and remove handler leaks by @ehedlund in https://github.com/google-gemini/gemini-cli/pull/26065
* fix(cli): correct alternate buffer warning logic for JetBrains by @Adib234 in https://github.com/google-gemini/gemini-cli/pull/26067
* fix(cli): make MCP ping optional in list command and use configured timeout by @cocosheng-g in https://github.com/google-gemini/gemini-cli/pull/26068
* fix(core): better error message for failed cloudshell-gca auth by @devr0306 in https://github.com/google-gemini/gemini-cli/pull/26079
* feat(cli): provide manual session UUID via command line arg by @cocosheng-g in https://github.com/google-gemini/gemini-cli/pull/26060
* Changelog for v0.40.0-preview.2 by @gemini-cli-robot in https://github.com/google-gemini/gemini-cli/pull/25846
* (docs) update sandboxing documentation by @g-samroberts in https://github.com/google-gemini/gemini-cli/pull/25930
* fix(core): enforce parallel task tracker updates by @anj-s in https://github.com/google-gemini/gemini-cli/pull/24477
* Update policy so transient errors are not marked terminal by @DavidAPierce in https://github.com/google-gemini/gemini-cli/pull/26066
* Implement bot that performs time-series metric analysis and suggests repo management improvements by @gundermanc in https://github.com/google-gemini/gemini-cli/pull/25945
* fix(core): handle non-string model flags in resolution by @Adib234 in https://github.com/google-gemini/gemini-cli/pull/26069
* fix(ux): added error message for ENOTDIR by @devr0306 in https://github.com/google-gemini/gemini-cli/pull/26128
* Changelog for v0.40.0-preview.3 by @gemini-cli-robot in https://github.com/google-gemini/gemini-cli/pull/25904
* fix(cli): prevent ACP stdout pollution from SessionEnd hooks by @cocosheng-g in https://github.com/google-gemini/gemini-cli/pull/26125
* feat(cli): support boolean and number casting for env vars in settings.json by @cocosheng-g in https://github.com/google-gemini/gemini-cli/pull/26118
* fix(cli): preserve Request headers in DevTools activity logger by @Adib234 in https://github.com/google-gemini/gemini-cli/pull/26078

## New Contributors
* @hsm207 made their first contribution in https://github.com/google-gemini/gemini-cli/pull/20108
* @gaurav0107 made their first contribution in https://github.com/google-gemini/gemini-cli/pull/25822

**Full Changelog**: https://github.com/google-gemini/gemini-cli/compare/v0.40.0-preview.5...v0.41.0-preview.0
