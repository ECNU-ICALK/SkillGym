#!/bin/bash
set -euo pipefail

mkdir -p "${TASK_OUTPUT_DIR:-/root/output}"

python3 <<'PY'
from __future__ import annotations

import json
import math
from pathlib import Path

import numpy as np
import pandas as pd
import yaml


import os


INPUT_DIR = Path(os.environ.get("TASK_INPUT_DIR", "/root/input"))
OUTPUT_PATH = Path(os.environ.get("TASK_OUTPUT_PATH", "/root/output/arkk_risk_report.json"))
FACTOR_COLUMNS = ["Mkt-RF", "SMB", "HML", "RMW", "CMA", "Mom"]
Z_05 = -1.6448536269514722


def load_frame() -> pd.DataFrame:
    prices = pd.read_csv(INPUT_DIR / "daily_prices.csv")
    pivot = prices.pivot(index="Date", columns="symbol", values="adj_close").sort_index()
    returns = (
        pivot[["ARKK", "QQQ"]]
        .pct_change()
        .dropna()
        .rename(columns={"ARKK": "arkk_return", "QQQ": "qqq_return"})
        .reset_index()
    )
    ff5 = pd.read_csv(INPUT_DIR / "F-F_Research_Data_5_Factors_2x3_daily.csv")
    mom = pd.read_csv(INPUT_DIR / "F-F_Momentum_Factor_daily.csv")
    frame = returns.merge(ff5, on="Date", how="inner").merge(mom, on="Date", how="inner")
    frame = frame[(frame["Date"] >= "2020-01-02") & (frame["Date"] <= "2024-12-31")].copy()
    for col in FACTOR_COLUMNS + ["RF"]:
        frame[col] = pd.to_numeric(frame[col], errors="raise") / 100.0
    return frame.sort_values("Date").reset_index(drop=True)


def cumulative_return(returns: np.ndarray) -> float:
    return float(np.prod(1.0 + returns) - 1.0)


def annualized_return(returns: np.ndarray) -> float:
    return float(np.prod(1.0 + returns) ** (252.0 / len(returns)) - 1.0)


def annualized_volatility(returns: np.ndarray) -> float:
    return float(np.std(returns, ddof=1) * math.sqrt(252.0))


def max_drawdown(returns: np.ndarray) -> float:
    wealth = np.cumprod(1.0 + returns)
    return float((wealth / np.maximum.accumulate(wealth) - 1.0).min())


def ols(y: np.ndarray, x: np.ndarray) -> tuple[np.ndarray, float, np.ndarray, np.ndarray]:
    x_with_const = np.column_stack([np.ones(len(x)), x])
    beta = np.linalg.lstsq(x_with_const, y, rcond=None)[0]
    fitted = x_with_const @ beta
    residuals = y - fitted
    ss_res = float(np.sum(residuals ** 2))
    ss_tot = float(np.sum((y - y.mean()) ** 2))
    r_squared = 1.0 - ss_res / ss_tot
    adjusted = 1.0 - (1.0 - r_squared) * (len(y) - 1) / (len(y) - x.shape[1] - 1)
    sigma2 = ss_res / (len(y) - x_with_const.shape[1])
    covariance = sigma2 * np.linalg.inv(x_with_const.T @ x_with_const)
    t_stats = beta / np.sqrt(np.diag(covariance))
    hac_t_stats = beta / np.sqrt(np.diag(newey_west_covariance(x_with_const, residuals, lag=5)))
    return beta, float(adjusted), t_stats, hac_t_stats


def newey_west_covariance(x_with_const: np.ndarray, residuals: np.ndarray, lag: int) -> np.ndarray:
    n = x_with_const.shape[0]
    meat = np.zeros((x_with_const.shape[1], x_with_const.shape[1]))
    for t in range(n):
        xt = x_with_const[t:t + 1].T
        meat += residuals[t] ** 2 * (xt @ xt.T)
    for ell in range(1, lag + 1):
        weight = 1.0 - ell / (lag + 1.0)
        gamma = np.zeros_like(meat)
        for t in range(ell, n):
            xt = x_with_const[t:t + 1].T
            xl = x_with_const[t - ell:t - ell + 1].T
            gamma += residuals[t] * residuals[t - ell] * (xt @ xl.T)
        meat += weight * (gamma + gamma.T)
    bread = np.linalg.inv(x_with_const.T @ x_with_const)
    return bread @ meat @ bread


def cornish_fisher_var_95(returns: np.ndarray) -> float:
    series = pd.Series(returns)
    mean = float(series.mean())
    std = float(series.std(ddof=1))
    skew = float(series.skew())
    excess_kurt = float(series.kurt())
    z = Z_05
    z_cf = z + ((z ** 2 - 1.0) * skew / 6.0) + ((z ** 3 - 3.0 * z) * excess_kurt / 24.0) - ((2.0 * z ** 3 - 5.0 * z) * skew ** 2 / 36.0)
    return float(mean + z_cf * std)


def drawdown_diagnostics(frame: pd.DataFrame, returns: np.ndarray) -> dict:
    dates = frame["Date"].tolist()
    wealth = pd.Series(np.cumprod(1.0 + returns), index=dates)
    drawdown = wealth / wealth.cummax() - 1.0
    trough_date = str(drawdown.idxmin())
    peak_value = float(wealth.cummax().loc[trough_date])
    peak_candidates = wealth.loc[:trough_date]
    peak_date = str(peak_candidates.index[np.isclose(peak_candidates.to_numpy(), peak_value)][-1])
    recovered = wealth.loc[trough_date:][wealth.loc[trough_date:] >= peak_value]
    return {
        "max_drawdown_peak_date": peak_date,
        "max_drawdown_trough_date": trough_date,
        "max_drawdown_recovery_date": None if recovered.empty else str(recovered.index[0]),
    }


def tail_diagnostics(frame: pd.DataFrame, returns: np.ndarray, var_95: float) -> dict:
    series = pd.Series(returns, index=frame["Date"].tolist())
    worst = series.sort_values(kind="mergesort").head(5)
    tail_count = int((series <= var_95).sum())
    return {
        "var_95_observation_count": tail_count,
        "cvar_95_observation_count": tail_count,
        "worst_daily_return_date": str(worst.index[0]),
        "worst_daily_return": float(worst.iloc[0]),
        "worst_5_return_dates": [str(idx) for idx in worst.index.tolist()],
    }


def rolling_risk(frame: pd.DataFrame, returns: np.ndarray) -> dict:
    dates = frame["Date"].tolist()
    series = pd.Series(returns, index=dates)
    window = 63
    rolling_cumulative = series.rolling(window).apply(lambda values: float(np.prod(1.0 + values) - 1.0), raw=True)
    rolling_volatility = series.rolling(window).std(ddof=1) * math.sqrt(252.0)
    worst_end = rolling_cumulative.idxmin()
    vol_end = rolling_volatility.idxmax()
    worst_end_pos = dates.index(worst_end)
    vol_end_pos = dates.index(vol_end)
    return {
        "window_trading_days": window,
        "worst_63d_cumulative_return": float(rolling_cumulative.loc[worst_end]),
        "worst_63d_start_date": str(dates[worst_end_pos - window + 1]),
        "worst_63d_end_date": str(worst_end),
        "highest_63d_annualized_volatility": float(rolling_volatility.loc[vol_end]),
        "highest_63d_vol_start_date": str(dates[vol_end_pos - window + 1]),
        "highest_63d_vol_end_date": str(vol_end),
    }


def bootstrap_tail_risk(returns: np.ndarray) -> dict:
    seed = 20260425
    sample_count = 25000
    block_length = 21
    blocks_per_sample = 3
    rng = np.random.default_rng(seed)
    starts = rng.integers(0, len(returns) - block_length + 1, size=(sample_count, blocks_per_sample))
    cumulative = np.empty(sample_count, dtype=float)
    for i in range(sample_count):
        path = np.concatenate([returns[start:start + block_length] for start in starts[i]])
        cumulative[i] = np.prod(1.0 + path) - 1.0
    var_99 = float(np.quantile(cumulative, 0.01))
    return {
        "method": "moving_block_21x3",
        "seed": seed,
        "sample_count": sample_count,
        "block_length": block_length,
        "horizon_trading_days": block_length * blocks_per_sample,
        "var_99": var_99,
        "cvar_99": float(cumulative[cumulative <= var_99].mean()),
    }


def moving_block_sample(returns: np.ndarray, rng: np.random.Generator, sample_count: int, block_length: int, horizon: int) -> np.ndarray:
    blocks_needed = int(np.ceil(horizon / block_length))
    starts = rng.integers(0, len(returns) - block_length + 1, size=(sample_count, blocks_needed))
    offsets = np.arange(block_length)
    block_paths = returns[starts[:, :, None] + offsets[None, None, :]].reshape(sample_count, blocks_needed * block_length)
    paths = block_paths[:, :horizon]
    return np.prod(1.0 + paths, axis=1) - 1.0


def stress_harness(returns: np.ndarray) -> list[dict]:
    rows: list[dict] = []
    sample_count = 100000
    for seed in range(101, 111):
        for block_length in [5, 10, 21]:
            for horizon in [21, 63]:
                for tail_probability in [0.01, 0.05]:
                    cumulative = moving_block_sample(returns, np.random.default_rng(seed), sample_count, block_length, horizon)
                    var = float(np.quantile(cumulative, tail_probability))
                    rows.append({
                        "seed": seed,
                        "block_length": block_length,
                        "horizon_trading_days": horizon,
                        "tail_probability": tail_probability,
                        "sample_count": sample_count,
                        "var": var,
                        "cvar": float(cumulative[cumulative <= var].mean()),
                    })
    return rows


def policy_breaches(report: dict) -> list[dict]:
    policy = yaml.safe_load((INPUT_DIR / "portfolio_policy.yaml").read_text(encoding="utf-8"))
    breaches = []
    checks = [
        ("max_drawdown_min", report["portfolio_metrics"]["max_drawdown"], policy["max_drawdown_min"], "min"),
        ("tracking_error_max", report["relative_metrics"]["tracking_error"], policy["tracking_error_max"], "max"),
        ("downside_beta_max", report["relative_metrics"]["downside_beta"], policy["downside_beta_max"], "max"),
        ("var_95_min", report["portfolio_metrics"]["var_95"], policy["var_95_min"], "min"),
        ("cvar_95_min", report["portfolio_metrics"]["cvar_95"], policy["cvar_95_min"], "min"),
    ]
    for rule_id, observed, limit, mode in checks:
        if (mode == "max" and observed > limit) or (mode == "min" and observed < limit):
            breaches.append({"rule_id": rule_id, "observed_value": float(observed), "limit": float(limit), "status": "breach"})
    for limit_key, limit in policy["factor_limits"].items():
        factor_key = limit_key.removesuffix("_abs_max")
        observed = report["factor_regression"][factor_key]
        if abs(observed) > float(limit):
            breaches.append({"rule_id": f"factor_{limit_key}", "observed_value": float(observed), "limit": float(limit), "status": "breach"})
    return sorted(breaches, key=lambda item: item["rule_id"])


frame = load_frame()
arkk = frame["arkk_return"].to_numpy(dtype=float)
qqq = frame["qqq_return"].to_numpy(dtype=float)
rf = frame["RF"].to_numpy(dtype=float)
excess = arkk - rf
active = arkk - qqq
var_95 = float(np.quantile(arkk, 0.05))
cvar_95 = float(arkk[arkk <= var_95].mean())
downside = qqq < 0
beta, adjusted_r_squared, t_stats, hac_t_stats = ols(excess, frame[FACTOR_COLUMNS].to_numpy(dtype=float))

report = {
    "analysis_window": {"start": "2020-01-02", "end": "2024-12-31", "trading_days_used": int(len(frame))},
    "portfolio_metrics": {
        "cumulative_return": cumulative_return(arkk),
        "annualized_return": annualized_return(arkk),
        "annualized_volatility": annualized_volatility(arkk),
        "sharpe_ratio": float(excess.mean() / arkk.std(ddof=1) * math.sqrt(252.0)),
        "sortino_ratio": float(excess.mean() / excess[excess < 0].std(ddof=1) * math.sqrt(252.0)),
        "max_drawdown": max_drawdown(arkk),
        "var_95": var_95,
        "cvar_95": cvar_95,
        "modified_var_95": cornish_fisher_var_95(arkk),
    },
    "relative_metrics": {
        "benchmark": "QQQ",
        "active_cumulative_return": cumulative_return(arkk) - cumulative_return(qqq),
        "tracking_error": annualized_volatility(active),
        "information_ratio": float(active.mean() / active.std(ddof=1) * math.sqrt(252.0)),
        "beta": float(np.cov(arkk, qqq, ddof=1)[0, 1] / np.var(qqq, ddof=1)),
        "downside_beta": float(np.cov(arkk[downside], qqq[downside], ddof=1)[0, 1] / np.var(qqq[downside], ddof=1)),
        "correlation": float(np.corrcoef(arkk, qqq)[0, 1]),
    },
    "factor_regression": {
        "model": "fama_french_5_plus_momentum",
        "alpha": float(beta[0]),
        "mkt_rf": float(beta[1]),
        "smb": float(beta[2]),
        "hml": float(beta[3]),
        "rmw": float(beta[4]),
        "cma": float(beta[5]),
        "mom": float(beta[6]),
        "adjusted_r_squared": adjusted_r_squared,
        "t_alpha": float(t_stats[0]),
        "t_mkt_rf": float(t_stats[1]),
        "t_smb": float(t_stats[2]),
        "t_hml": float(t_stats[3]),
        "t_rmw": float(t_stats[4]),
        "t_cma": float(t_stats[5]),
        "t_mom": float(t_stats[6]),
        "hac_lag": 5,
        "hac_t_alpha": float(hac_t_stats[0]),
        "hac_t_mkt_rf": float(hac_t_stats[1]),
        "hac_t_smb": float(hac_t_stats[2]),
        "hac_t_hml": float(hac_t_stats[3]),
        "hac_t_rmw": float(hac_t_stats[4]),
        "hac_t_cma": float(hac_t_stats[5]),
        "hac_t_mom": float(hac_t_stats[6]),
    },
    "drawdown_diagnostics": drawdown_diagnostics(frame, arkk),
    "tail_diagnostics": tail_diagnostics(frame, arkk, var_95),
    "rolling_risk": rolling_risk(frame, arkk),
    "data_quality": {
        "first_return_date": str(frame["Date"].iloc[0]),
        "last_return_date": str(frame["Date"].iloc[-1]),
        "price_return_rows": int(len(frame[["arkk_return", "qqq_return"]].dropna())),
        "factor_rows": int(len(frame[FACTOR_COLUMNS + ["RF"]].dropna())),
        "common_rows": int(len(frame)),
    },
    "bootstrap_tail_risk": bootstrap_tail_risk(arkk),
    "stress_harness": stress_harness(arkk),
}
report["policy_breaches"] = policy_breaches(report)
OUTPUT_PATH.write_text(json.dumps(report, indent=2, sort_keys=True), encoding="utf-8")
PY
