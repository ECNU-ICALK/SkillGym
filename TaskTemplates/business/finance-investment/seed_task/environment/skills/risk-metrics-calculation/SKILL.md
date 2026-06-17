---
name: risk-metrics-calculation
description: Calculate portfolio risk metrics, benchmark-relative active risk, tail loss, drawdown, factor exposures, HAC statistics, and deterministic bootstrap stress grids from market return data.
---

# Risk Metrics Calculation

Use this skill when a task asks you to calculate portfolio risk metrics, benchmark-relative active risk, tail loss, drawdown, or factor exposures from market return data. It is especially useful for investment-risk tasks where small details such as factor units, risk-free-rate alignment, and downside windows can change the answer.

## Recommended workflow

1. Treat adjusted close prices as the source for daily simple returns.
2. Build a single date-aligned table before computing metrics. For factor work, use only dates common to portfolio returns, benchmark returns, risk-free rates, and all requested factors.
3. Convert Kenneth French daily factor files from percent units to decimal units before using them.
4. Use excess returns where required:
   - Sharpe ratio uses `(mean daily excess return / sample standard deviation of portfolio daily returns) * sqrt(252)`.
   - Sortino ratio uses `(mean daily excess return / sample standard deviation of negative daily excess returns) * sqrt(252)`.
   - Fama-French regressions use portfolio excess return as the dependent variable.
5. Compute cumulative return by compounding daily returns, not by summing returns.
6. Annualize with 252 trading days:
   - annualized return from compounded total return;
   - volatility and tracking error by multiplying daily standard deviation by `sqrt(252)`.
7. Compute maximum drawdown from the cumulative wealth curve and previous running peaks.
8. Compute historical VaR as the lower-tail percentile of daily returns and CVaR as the average return at or below that percentile. Report both as negative return values.
9. Compute Cornish-Fisher modified VaR from mean, sample standard deviation, sample skewness, excess kurtosis, and the 5% normal quantile.
10. Compute benchmark beta as `cov(portfolio, benchmark) / var(benchmark)`.
11. Compute downside beta using only dates where benchmark return is negative.
12. Compute both conventional OLS t-statistics and Newey-West HAC lag-5 t-statistics with Bartlett weights.
13. For `active_cumulative_return`, use portfolio cumulative return minus benchmark cumulative return over the same aligned window. Do not compound daily active returns for this field unless the task explicitly asks for that alternative.
14. After all metrics are calculated, evaluate risk-policy limits separately so policy errors do not contaminate the metric calculations.
15. For factor policy breaches, keep the observed factor loading signed even though the limit is an absolute-value threshold.
16. For audit diagnostics, compute drawdown peak/trough/recovery from the wealth curve, lower-tail membership from the VaR cutoff, rolling 63-day cumulative return and volatility windows, and OLS t-statistics from `(X'X)^-1`.
17. For deterministic bootstrap tail risk, keep the random generator, block length, horizon construction, and tail cutoff exactly aligned with the task notes before writing JSON.
18. For stress harnesses, generate rows from the parameter grid in the requested order. Avoid hand-writing rows; loop over the grid and use the same moving-block function for every scenario.
19. When a stress harness specifies a seed per row, reinitialize a fresh random generator for every row before drawing blocks. Do not create one generator per seed and let it advance across block lengths or horizons unless the task explicitly asks for that.

## Helper script

- `scripts/build_risk_report.py`: reads the task's input files and emits a candidate risk report using the full workflow above, including audit diagnostics and the large deterministic stress grid. It does not contain hard-coded answers; it derives the report from the supplied market, factor, and policy files. Review the output schema before final submission.
- For this ARKK risk-review task, run the helper once to establish the exact alignment, HAC, bootstrap, and stress-harness conventions, then inspect or adapt the generated calculation script/output as needed. This is faster and safer than re-deriving every convention from scratch.

The helper script is meant to reduce diagnosis time and catch common financial-metric pitfalls. You are still responsible for matching the task's exact output schema and checking the final file before submission.
