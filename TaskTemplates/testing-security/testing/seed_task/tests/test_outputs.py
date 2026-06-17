from __future__ import annotations

from common import (
    access_log_path_for,
    run_user_suite,
    search_log_entries,
    workspace_test_text,
)


def test_existing_npm_test_command_succeeds() -> None:
    result = run_user_suite()
    assert result.exit_code == 0, result.stdout + "\n" + result.stderr


def test_saved_theme_first_paint_logic_is_present() -> None:
    text = workspace_test_text()
    assert "localStorage" in text
    assert "theme" in text
    assert any(
        all(marker in text for marker in markers)
        for markers in (
            (
                "page.addInitScript",
                "__airportThemeProbe",
                "beforeBackgroundColor",
                "beforePosition",
                "requestAnimationFrame(step)",
                "isLightCoverFrame",
            ),
            (
                "page.addInitScript",
                "sample.cover",
                "colorScheme",
                "requestAnimationFrame",
                "localStorage.setItem('theme', 'dark')",
            ),
            (
                "page.addInitScript",
                "__themeProbe",
                "coverActive",
                "requestAnimationFrame",
                "localStorage.setItem('theme', 'dark')",
            ),
            (
                "page.addInitScript",
                "__themeProbe",
                "overlayContent",
                "overlayPosition",
                "requestAnimationFrame",
                "localStorage.setItem('theme', 'dark')",
            ),
            (
                "page.addInitScript",
                "themeFrames",
                "flickerCoverPresent",
                "beforeBackgroundColor",
                "beforeContent",
            ),
            (
                "page.addInitScript",
                "__themeFrameSamples",
                "__releaseHeldAnimationFrames",
                "hasOpaqueLightCover",
                "readMeanLuminance",
            ),
            (
                "page.addInitScript",
                "__themeValidationSamples",
                "beforeBackground",
                "beforeContent",
                "colorScheme",
                "frameSamples",
            ),
            (
                "page.addInitScript",
                "__themeFrames",
                "__themeCaptureDone",
                "pseudoBackgroundColor",
                "pseudoContent",
                "coverVisible",
            ),
            (
                "page.addInitScript",
                "__themeSamples",
                "capture('domcontentloaded')",
                "beforeContent",
                "beforeBackground",
                "colorScheme",
                "parseAlpha",
                "hasVisibleCover",
                "requestAnimationFrame(step)",
            ),
            (
                "page.addInitScript",
                "__themeProbe",
                "samples: [], done: false",
                "overlayPresent",
                "colorScheme",
                "requestAnimationFrame(sample)",
                "localStorage.setItem('theme', desiredTheme)",
            ),
            (
                "page.addInitScript",
                "__themeProbeSamples",
                "bodyColor",
                "overlayBackgroundColor",
                "overlayZIndex",
                "hasLightCover(sample)",
                "DARK_THEME_BODY_COLOR",
            ),
            (
                "page.addInitScript",
                "__themeProbe = {",
                "beforeBackground",
                "flickerCoverPresent",
                "storageError",
                "window.__themeProbe.done = true",
                "['domcontentloaded', 'raf1', 'raf2'].includes(sample.label)",
            ),
        )
    )


def test_layout_shift_observer_logic_is_present() -> None:
    text = workspace_test_text()
    assert any(
        all(marker in text for marker in markers)
        for markers in (
            (
                "collectLayoutSamples",
                "getBoundingClientRect",
                "contentGridTopShift",
                "tableCardWidthShift",
                "insightsPanelLeftShift",
                "insightsPanelWidthShift",
            ),
            (
                "maxControlsTopDelta",
                "maxTableTopDelta",
                "maxTableWidthDelta",
                "maxInsightsLeftDelta",
                "getBoundingClientRect",
            ),
            (
                "maxDrift('summary.y')",
                "maxDrift('controls.y')",
                "maxDrift('tableCard.width')",
                "maxDrift('insights.x')",
                "summaryLoaded",
                "insightsLoaded",
            ),
            (
                "Performance.getMetrics",
                "CumulativeLayoutShift",
                "contentGridBeforeLoad",
                "contentGridAfterLoad",
                "insightsBeforeLoad",
                "insightsAfterLoad",
            ),
            (
                "maxShift.controlsTop",
                "maxShift.contentGridTop",
                "maxShift.tableCardWidth",
                "maxShift.panelStackWidth",
                "summaryLoaded",
                "insightsLoaded",
            ),
            (
                "collectLayoutSample",
                "maxDelta(samples, (sample) => sample.controls.top)",
                "maxDelta(samples, (sample) => sample.panelStack.left)",
                "maxDelta(samples, (sample) => sample.tableCard.width)",
                "summaryLoaded",
                "insightsLoaded",
            ),
            (
                "collectLayoutMetrics",
                "before.statusBar.y",
                "after.statusBar.y",
                "before.contentGrid.y",
                "after.contentGrid.y",
                "before.tableCard.width",
                "before.panelStack.width",
            ),
            (
                "__layoutSamples",
                "__layoutShiftValue",
                "extractMetricDelta(samples, 'controls', 'y')",
                "extractMetricDelta(samples, 'statusBar', 'y')",
                "extractMetricDelta(samples, 'tableCard', 'width')",
                "extractMetricDelta(samples, 'panelStack', 'x')",
            ),
            (
                "__layoutSamples",
                "__layoutSamplingDone",
                "openingAnchor",
                "tableCard",
                "insightsPanel",
                "summaryLoaded",
                "insightsLoaded",
                "readRect('[data-testid=\"search-input\"]')",
                "maxDrift(samples, (sample) => sample.openingAnchor?.y)",
                "maxDrift(samples, (sample) => sample.tableCard?.x)",
                "maxDrift(samples, (sample) => sample.tableCard?.width)",
                "maxDrift(samples, (sample) => sample.insightsPanel?.x)",
                "maxDrift(samples, (sample) => sample.insightsPanel?.height)",
            ),
            (
                "__layoutProbe",
                "samples: [], done: false",
                "resultsSummaryBodyVisible",
                "insightsBodyVisible",
                "controls: captureRect(selectors.controls)",
                "statusBar: captureRect(selectors.statusBar)",
                "tableCard: captureRect(selectors.tableCard)",
                "insightsPanel: captureRect(selectors.insightsPanel)",
                "maxDelta(samples, 'controls', 'top')",
                "maxDelta(samples, 'statusBar', 'top')",
                "maxDelta(samples, 'tableCard', 'width')",
                "maxDelta(samples, 'insightsPanel', 'left')",
                "maxDelta(samples, 'insightsPanel', 'width')",
            ),
            (
                "captureLayoutSnapshot",
                "expectShiftAtMost",
                "MAX_OPENING_SHIFT_PX",
                "MAX_LOWER_AREA_SHIFT_PX",
                "results-summary-skeleton",
                "insights-skeleton",
                "before.controls.top",
                "after.controls.top",
                "before.statusBar.top",
                "after.statusBar.top",
                "before.tableCard.width",
                "after.tableCard.width",
                "before.panelStack.left",
                "after.panelStack.left",
                "before.insightsPanel.width",
                "after.insightsPanel.width",
            ),
            (
                "maxDelta(samples, elementKey, field)",
                "summaryLoaded",
                "insightsLoaded",
                "contentGrid",
                "panelStack",
                "Number(box.width.toFixed(2))",
                "['controls', 'y', 2]",
                "['panelStack', 'width', 2]",
            ),
        )
    )


def test_core_airport_flow_is_covered() -> None:
    result = run_user_suite()
    detail_logs = search_log_entries("detail")
    compare_logs = search_log_entries("compare")
    export_logs = search_log_entries("export")
    assert detail_logs, result.stdout + "\n" + result.stderr
    assert compare_logs, result.stdout + "\n" + result.stderr
    assert export_logs, result.stdout + "\n" + result.stderr


def test_theme_flicker_regression_is_detected() -> None:
    mutation_mode = "theme-flicker"
    result = run_user_suite(mutation_mode)
    assert result.exit_code != 0, result.stdout + "\n" + result.stderr


def test_layout_shift_regression_is_detected() -> None:
    mutation_mode = "insights-layout-shift"
    result = run_user_suite(mutation_mode)
    compare_logs = search_log_entries("compare", access_log_path_for(mutation_mode))
    assert compare_logs, compare_logs
    assert result.exit_code != 0, result.stdout + "\n" + result.stderr


def test_lateral_layout_shift_regression_is_detected() -> None:
    mutation_mode = "insights-lateral-shift"
    result = run_user_suite(mutation_mode)
    compare_logs = search_log_entries("compare", access_log_path_for(mutation_mode))
    assert compare_logs, compare_logs
    assert result.exit_code != 0, result.stdout + "\n" + result.stderr


def test_detail_regression_is_detected() -> None:
    mutation_mode = "detail-kjfk-region-swap"
    result = run_user_suite(mutation_mode)
    detail_logs = search_log_entries("detail", access_log_path_for(mutation_mode))
    assert any(entry.get("airportIdent") == "KJFK" for entry in detail_logs), detail_logs
    assert result.exit_code != 0, result.stdout + "\n" + result.stderr


def test_compare_regression_is_detected() -> None:
    mutation_mode = "compare-kjfk-klax-difference-bug"
    result = run_user_suite(mutation_mode)
    compare_logs = search_log_entries("compare", access_log_path_for(mutation_mode))
    assert any(
        entry.get("left") == "KJFK" and entry.get("right") == "KLAX" for entry in compare_logs
    ), compare_logs
    assert result.exit_code != 0, result.stdout + "\n" + result.stderr


def test_filtered_export_regression_is_detected() -> None:
    mutation_mode = "export-us-12000-klax-region-bug"
    result = run_user_suite(mutation_mode)
    export_logs = search_log_entries("export", access_log_path_for(mutation_mode))
    assert export_logs, export_logs
    assert result.exit_code != 0, result.stdout + "\n" + result.stderr
