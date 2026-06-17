from __future__ import annotations

from risk_utils import assert_close, expected_report, read_submission


REQUIRED_TOP_LEVEL = {
    "analysis_window",
    "portfolio_metrics",
    "relative_metrics",
    "factor_regression",
    "drawdown_diagnostics",
    "tail_diagnostics",
    "rolling_risk",
    "data_quality",
    "bootstrap_tail_risk",
    "stress_harness",
    "policy_breaches",
}

PORTFOLIO_KEYS = {
    "cumulative_return",
    "annualized_return",
    "annualized_volatility",
    "sharpe_ratio",
    "sortino_ratio",
    "max_drawdown",
    "var_95",
    "cvar_95",
    "modified_var_95",
}

RELATIVE_KEYS = {
    "benchmark",
    "active_cumulative_return",
    "tracking_error",
    "information_ratio",
    "beta",
    "downside_beta",
    "correlation",
}

REGRESSION_KEYS = {
    "model",
    "alpha",
    "mkt_rf",
    "smb",
    "hml",
    "rmw",
    "cma",
    "mom",
    "adjusted_r_squared",
    "t_alpha",
    "t_mkt_rf",
    "t_smb",
    "t_hml",
    "t_rmw",
    "t_cma",
    "t_mom",
    "hac_lag",
    "hac_t_alpha",
    "hac_t_mkt_rf",
    "hac_t_smb",
    "hac_t_hml",
    "hac_t_rmw",
    "hac_t_cma",
    "hac_t_mom",
}


def test_output_exists_and_schema_is_parseable() -> None:
    submission = read_submission()
    assert REQUIRED_TOP_LEVEL.issubset(submission), f"Missing top-level keys: {REQUIRED_TOP_LEVEL - set(submission)}"
    assert PORTFOLIO_KEYS.issubset(submission["portfolio_metrics"])
    assert RELATIVE_KEYS.issubset(submission["relative_metrics"])
    assert REGRESSION_KEYS.issubset(submission["factor_regression"])
    assert isinstance(submission["policy_breaches"], list)


def test_analysis_window_and_trading_day_alignment() -> None:
    submission = read_submission()
    expected = expected_report()
    assert submission["analysis_window"]["start"] == expected["analysis_window"]["start"]
    assert submission["analysis_window"]["end"] == expected["analysis_window"]["end"]
    assert submission["analysis_window"]["trading_days_used"] == expected["analysis_window"]["trading_days_used"]


def test_portfolio_absolute_risk_metrics() -> None:
    submission = read_submission()
    expected = expected_report()
    for key, value in expected["portfolio_metrics"].items():
        if key == "sharpe_ratio":
            submitted = submission["portfolio_metrics"].get(key)
            annualized_over_daily_vol = value * (252 ** 0.5)
            if abs(float(submitted) - annualized_over_daily_vol) <= 5e-5:
                continue
        if key == "var_95":
            assert_close(submission["portfolio_metrics"].get(key), value, f"portfolio_metrics.{key}", atol=5e-4)
            continue
        assert_close(submission["portfolio_metrics"].get(key), value, f"portfolio_metrics.{key}")


def test_benchmark_relative_metrics() -> None:
    submission = read_submission()
    expected = expected_report()
    assert submission["relative_metrics"]["benchmark"] == "QQQ"
    for key, value in expected["relative_metrics"].items():
        if key == "benchmark":
            continue
        assert_close(submission["relative_metrics"].get(key), value, f"relative_metrics.{key}")


def test_factor_regression_metrics() -> None:
    submission = read_submission()
    expected = expected_report()
    assert submission["factor_regression"]["model"] == "fama_french_5_plus_momentum"
    assert submission["factor_regression"]["hac_lag"] == 5
    for key, value in expected["factor_regression"].items():
        if key == "model":
            continue
        if key == "hac_lag":
            continue
        assert_close(submission["factor_regression"].get(key), value, f"factor_regression.{key}")


def test_audit_diagnostics_match_recomputation() -> None:
    submission = read_submission()
    expected = expected_report()
    assert submission["drawdown_diagnostics"] == expected["drawdown_diagnostics"]
    for count_key in ["var_95_observation_count", "cvar_95_observation_count"]:
        count = submission["tail_diagnostics"][count_key]
        assert isinstance(count, int)
        assert 50 <= count <= 70
    assert submission["tail_diagnostics"]["worst_daily_return_date"] == expected["tail_diagnostics"]["worst_daily_return_date"]
    assert submission["tail_diagnostics"]["worst_5_return_dates"] == expected["tail_diagnostics"]["worst_5_return_dates"]
    assert_close(submission["tail_diagnostics"]["worst_daily_return"], expected["tail_diagnostics"]["worst_daily_return"], "tail_diagnostics.worst_daily_return")
    assert submission["rolling_risk"]["window_trading_days"] == 63
    for key, value in expected["rolling_risk"].items():
        if key == "window_trading_days":
            continue
        if key.endswith("_date"):
            assert submission["rolling_risk"][key] == value
        else:
            assert_close(submission["rolling_risk"][key], value, f"rolling_risk.{key}")
    assert submission["data_quality"]["first_return_date"] == expected["data_quality"]["first_return_date"]
    assert submission["data_quality"]["last_return_date"] == expected["data_quality"]["last_return_date"]
    assert submission["data_quality"]["common_rows"] == expected["data_quality"]["common_rows"]


def test_bootstrap_tail_risk_matches_deterministic_spec() -> None:
    submission = read_submission()
    expected = expected_report()["bootstrap_tail_risk"]
    got = submission["bootstrap_tail_risk"]
    for key in ["method", "seed", "sample_count", "block_length", "horizon_trading_days"]:
        assert got[key] == expected[key]
    assert_close(got["var_99"], expected["var_99"], "bootstrap_tail_risk.var_99")
    assert_close(got["cvar_99"], expected["cvar_99"], "bootstrap_tail_risk.cvar_99")


def test_stress_harness_matches_parameter_grid() -> None:
    submission = read_submission()
    expected = expected_report()["stress_harness"]
    got = submission["stress_harness"]
    assert isinstance(got, list)
    assert len(got) == len(expected) == 120
    for idx, (actual, exp) in enumerate(zip(got, expected)):
        for key in ["seed", "block_length", "horizon_trading_days", "tail_probability", "sample_count"]:
            assert actual[key] == exp[key], f"stress_harness[{idx}].{key}"
        assert_close(actual["var"], exp["var"], f"stress_harness[{idx}].var")
        assert_close(actual["cvar"], exp["cvar"], f"stress_harness[{idx}].cvar")


def test_policy_breaches_match_policy_file() -> None:
    submission = read_submission()
    expected = expected_report()["policy_breaches"]
    submitted_by_rule = {}
    for item in submission["policy_breaches"]:
        rule_id = item.get("rule_id", "")
        if rule_id.startswith("factor_limits."):
            rule_id = "factor_" + rule_id.split(".", 1)[1]
        submitted_by_rule[rule_id] = item

    expected_rule_ids = {item["rule_id"] for item in expected}
    assert set(submitted_by_rule) == expected_rule_ids, f"Expected breach rules {expected_rule_ids}, got {set(submitted_by_rule)}"
    for exp in expected:
        got = submitted_by_rule[exp["rule_id"]]
        assert got.get("status") == "breach"
        observed = got.get("observed_value")
        if exp["rule_id"].startswith("factor_") and abs(float(observed) - abs(exp["observed_value"])) <= 5e-5:
            observed = exp["observed_value"]
        atol = 5e-4 if exp["rule_id"] == "var_95_min" else 5e-5
        assert_close(observed, exp["observed_value"], f"policy_breaches.{exp['rule_id']}.observed_value", atol=atol)
        assert_close(got.get("limit"), exp["limit"], f"policy_breaches.{exp['rule_id']}.limit")
