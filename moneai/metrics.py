"""Kennzahlen zur Beurteilung einer Strategie.

Alle Funktionen erwarten periodische Renditen (nicht kumuliert) mit einem
DatetimeIndex. Annualisiert wird anhand des tatsächlichen Zeitabstands der
Daten, damit Stunden-, Vier-Stunden- und Tageskerzen vergleichbar bleiben.
"""
from __future__ import annotations

from typing import Dict, Optional

import numpy as np
import pandas as pd

SECONDS_PER_YEAR = 365.25 * 24 * 3600


def periods_per_year(index: pd.DatetimeIndex) -> float:
    if len(index) < 3:
        return float("nan")
    steps = pd.Series(index).diff().dropna().dt.total_seconds()
    median = float(steps.median())
    if median <= 0:
        return float("nan")
    return SECONDS_PER_YEAR / median


def equity_curve(returns: pd.Series, initial: float = 1.0) -> pd.Series:
    return initial * (1.0 + returns.fillna(0.0)).cumprod()


def total_return(returns: pd.Series) -> float:
    return float(equity_curve(returns).iloc[-1] - 1.0)


def cagr(returns: pd.Series) -> float:
    years = len(returns) / periods_per_year(returns.index)
    if not years > 0:
        return float("nan")
    final = float(equity_curve(returns).iloc[-1])
    if final <= 0:
        return -1.0
    return final ** (1.0 / years) - 1.0


def annualised_volatility(returns: pd.Series) -> float:
    return float(returns.std(ddof=1) * np.sqrt(periods_per_year(returns.index)))


def sharpe_ratio(returns: pd.Series, risk_free: float = 0.0) -> float:
    """Sharpe auf Basis der Periodenrenditen, annualisiert.

    Bei stark schiefen Renditen (Trendfolge, Optionen) ist Sharpe allein
    irreführend. Immer zusammen mit Drawdown und Trade-Anzahl lesen.
    """
    ppy = periods_per_year(returns.index)
    excess = returns.fillna(0.0) - risk_free / ppy
    spread = float(excess.std(ddof=1))
    if not spread > 0:
        return float("nan")
    return float(excess.mean() / spread * np.sqrt(ppy))


def sortino_ratio(returns: pd.Series, risk_free: float = 0.0) -> float:
    ppy = periods_per_year(returns.index)
    excess = returns.fillna(0.0) - risk_free / ppy
    downside = excess.clip(upper=0.0)
    spread = float(np.sqrt((downside ** 2).mean()))
    if not spread > 0:
        return float("nan")
    return float(excess.mean() / spread * np.sqrt(ppy))


def drawdown_series(returns: pd.Series) -> pd.Series:
    curve = equity_curve(returns)
    return curve / curve.cummax() - 1.0


def max_drawdown(returns: pd.Series) -> float:
    """Größter Rückgang vom Hoch, als negative Zahl."""
    return float(drawdown_series(returns).min())


def longest_drawdown_days(returns: pd.Series) -> float:
    drawdown = drawdown_series(returns)
    under_water = drawdown < 0
    if not under_water.any():
        return 0.0
    groups = (~under_water).cumsum()[under_water]
    longest = 0.0
    for _, part in drawdown[under_water].groupby(groups):
        span = (part.index[-1] - part.index[0]).total_seconds() / 86400.0
        longest = max(longest, span)
    return longest


def calmar_ratio(returns: pd.Series) -> float:
    depth = abs(max_drawdown(returns))
    if not depth > 0:
        return float("nan")
    return cagr(returns) / depth


def exposure(positions: pd.Series) -> float:
    """Anteil der Zeit mit offener Position."""
    return float((positions.fillna(0.0).abs() > 0).mean())


def turnover(positions: pd.Series) -> float:
    """Gehandeltes Volumen pro Jahr, in Vielfachen des Kapitals."""
    traded = positions.fillna(0.0).diff().abs().sum()
    years = len(positions) / periods_per_year(positions.index)
    if not years > 0:
        return float("nan")
    return float(traded / years)


def trade_table(positions: pd.Series, returns: pd.Series) -> pd.DataFrame:
    """Fasst zusammenhängende Positionen gleicher Richtung zu Trades zusammen."""
    pos = positions.fillna(0.0)
    direction = np.sign(pos)
    block = (direction != direction.shift(1)).cumsum()
    frame = pd.DataFrame({
        "pos": pos,
        "ret": returns.reindex(pos.index).fillna(0.0),
        "block": block,
    })
    rows = []
    for _, group in frame.groupby("block"):
        if group["pos"].iloc[0] == 0:
            continue
        rows.append({
            "start": group.index[0],
            "end": group.index[-1],
            "bars": int(len(group)),
            "direction": float(np.sign(group["pos"].iloc[0])),
            "pnl": float((1.0 + group["ret"]).prod() - 1.0),
        })
    return pd.DataFrame(rows)


def trade_stats(positions: pd.Series, returns: pd.Series) -> Dict[str, float]:
    trades = trade_table(positions, returns)
    if trades.empty:
        return {"trades": 0.0, "hit_rate": float("nan"),
                "profit_factor": float("nan"), "avg_trade": float("nan")}
    wins = trades.loc[trades["pnl"] > 0, "pnl"]
    losses = trades.loc[trades["pnl"] < 0, "pnl"]
    gross_profit = float(wins.sum())
    gross_loss = float(-losses.sum())
    factor = gross_profit / gross_loss if gross_loss > 0 else float("inf")
    return {
        "trades": float(len(trades)),
        "hit_rate": float(len(wins)) / float(len(trades)),
        "profit_factor": factor,
        "avg_trade": float(trades["pnl"].mean()),
    }


def summary(returns: pd.Series, positions: Optional[pd.Series] = None) -> Dict[str, float]:
    stats = {
        "total_return": total_return(returns),
        "cagr": cagr(returns),
        "volatility": annualised_volatility(returns),
        "sharpe": sharpe_ratio(returns),
        "sortino": sortino_ratio(returns),
        "max_drawdown": max_drawdown(returns),
        "drawdown_days": longest_drawdown_days(returns),
        "calmar": calmar_ratio(returns),
        "bars": float(len(returns)),
    }
    if positions is not None:
        stats["exposure"] = exposure(positions)
        stats["turnover_per_year"] = turnover(positions)
        stats.update(trade_stats(positions, returns))
    return stats


def format_summary(stats: Dict[str, float], title: str = "Ergebnis") -> str:
    percent_keys = {"total_return", "cagr", "volatility", "max_drawdown",
                    "exposure", "hit_rate", "avg_trade"}
    lines = [title, "-" * len(title)]
    for key, value in stats.items():
        if key in percent_keys:
            lines.append(f"{key:<20} {value * 100:>10.2f} %")
        else:
            lines.append(f"{key:<20} {value:>10.2f}")
    return chr(10).join(lines)
