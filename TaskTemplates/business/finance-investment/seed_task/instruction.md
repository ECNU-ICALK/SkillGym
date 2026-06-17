You are a portfolio risk analyst. Evaluate whether ARK Innovation ETF (ARKK) showed persistent style drift and excess downside risk relative to Nasdaq-100 ETF (QQQ) during the 2020-2024 market cycle.

Input data is in `/root/input/`:

- `daily_prices.csv`: adjusted daily market prices for ARKK, QQQ, SPY, IWM, and AGG.
- `F-F_Research_Data_5_Factors_2x3_daily.csv`: daily Fama-French 5 factor returns.
- `F-F_Momentum_Factor_daily.csv`: daily momentum factor returns.
- `portfolio_policy.yaml`: risk policy thresholds for drawdown, active risk, downside beta, tail loss, and factor exposures.

Your task:

1. Build an aligned daily return panel for ARKK and QQQ over `2020-01-02` through `2024-12-31`.
2. Use the Fama-French files to evaluate ARKK excess returns, factor style drift, and regression significance.
3. Produce absolute risk, QQQ-relative risk, drawdown, tail-risk, rolling-window, data-quality, bootstrap tail-risk, and stress-harness diagnostics.
4. Compare the calculated results with `portfolio_policy.yaml` and list every policy breach.
5. Write the final machine-readable report to `/root/output/arkk_risk_report.json`.

Output format:

Create `/root/output/arkk_risk_report.json` as a JSON object with this schema. All numeric metrics must be JSON numbers, not strings, and all returns/risk quantities must use decimal notation rather than percent notation.

```json
{
  "analysis_window": {
    "start": "2020-01-02",
    "end": "2024-12-31",
    "trading_days_used": 0
  },
  "portfolio_metrics": {
    "cumulative_return": 0.0,
    "annualized_return": 0.0,
    "annualized_volatility": 0.0,
    "sharpe_ratio": 0.0,
    "sortino_ratio": 0.0,
    "max_drawdown": 0.0,
    "var_95": 0.0,
    "cvar_95": 0.0,
    "modified_var_95": 0.0
  },
  "relative_metrics": {
    "benchmark": "QQQ",
    "active_cumulative_return": 0.0,
    "tracking_error": 0.0,
    "information_ratio": 0.0,
    "beta": 0.0,
    "downside_beta": 0.0,
    "correlation": 0.0
  },
  "factor_regression": {
    "model": "fama_french_5_plus_momentum",
    "alpha": 0.0,
    "mkt_rf": 0.0,
    "smb": 0.0,
    "hml": 0.0,
    "rmw": 0.0,
    "cma": 0.0,
    "mom": 0.0,
    "adjusted_r_squared": 0.0,
    "t_alpha": 0.0,
    "t_mkt_rf": 0.0,
    "t_smb": 0.0,
    "t_hml": 0.0,
    "t_rmw": 0.0,
    "t_cma": 0.0,
    "t_mom": 0.0,
    "hac_lag": 5,
    "hac_t_alpha": 0.0,
    "hac_t_mkt_rf": 0.0,
    "hac_t_smb": 0.0,
    "hac_t_hml": 0.0,
    "hac_t_rmw": 0.0,
    "hac_t_cma": 0.0,
    "hac_t_mom": 0.0
  },
  "drawdown_diagnostics": {
    "max_drawdown_peak_date": "YYYY-MM-DD",
    "max_drawdown_trough_date": "YYYY-MM-DD",
    "max_drawdown_recovery_date": null
  },
  "tail_diagnostics": {
    "var_95_observation_count": 0,
    "cvar_95_observation_count": 0,
    "worst_daily_return_date": "YYYY-MM-DD",
    "worst_daily_return": 0.0,
    "worst_5_return_dates": ["YYYY-MM-DD"]
  },
  "rolling_risk": {
    "window_trading_days": 63,
    "worst_63d_cumulative_return": 0.0,
    "worst_63d_start_date": "YYYY-MM-DD",
    "worst_63d_end_date": "YYYY-MM-DD",
    "highest_63d_annualized_volatility": 0.0,
    "highest_63d_vol_start_date": "YYYY-MM-DD",
    "highest_63d_vol_end_date": "YYYY-MM-DD"
  },
  "data_quality": {
    "first_return_date": "YYYY-MM-DD",
    "last_return_date": "YYYY-MM-DD",
    "price_return_rows": 0,
    "factor_rows": 0,
    "common_rows": 0
  },
  "bootstrap_tail_risk": {
    "method": "moving_block_21x3",
    "seed": 0,
    "sample_count": 0,
    "block_length": 0,
    "horizon_trading_days": 0,
    "var_99": 0.0,
    "cvar_99": 0.0
  },
  "stress_harness": [
    {
      "seed": 0,
      "block_length": 0,
      "horizon_trading_days": 0,
      "tail_probability": 0.0,
      "sample_count": 0,
      "var": 0.0,
      "cvar": 0.0
    }
  ],
  "policy_breaches": [
    {
      "rule_id": "",
      "observed_value": 0.0,
      "limit": 0.0,
      "status": "breach"
    }
  ]
}
```

Notes:

- Use adjusted close prices and daily simple returns.
- Convert Fama-French factor and risk-free-rate columns into decimal return units before using them.
- Use QQQ as the benchmark for all relative-risk metrics.
- Report `active_cumulative_return` as ARKK cumulative return minus QQQ cumulative return over the same aligned window.
- Tail-risk metrics and stress diagnostics must describe lower-tail losses, so VaR and CVaR values should be negative when losses are present.
- Drawdown and rolling-window diagnostics should be auditable from dates in the aligned return panel.
- The bootstrap tail-risk and stress-harness sections must be deterministic and reproducible from the provided market return data.
- For factor policy breaches, keep the signed factor loading as `observed_value` even when the policy limit is an absolute exposure threshold.
- Do not hardcode final answers.
- Do not modify files under `/root/input/`.
- Do not modify tests, verifier files, task metadata, or environment files.
- Do not bypass the requested financial calculations by writing placeholder values or manually fabricating outputs.
