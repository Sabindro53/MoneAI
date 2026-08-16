"""Tests für die Annahmen, auf denen jedes Ergebnis beruht.

Ausführen im Projektordner mit: pytest -q
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from moneai.backtest import Backtester, CostModel  # noqa: E402
from moneai.metrics import max_drawdown, periods_per_year, summary  # noqa: E402
from moneai.strategies import SMACrossover  # noqa: E402

FREE = CostModel(taker_fee=0.0, half_spread=0.0, slippage=0.0, financing_per_year=0.0)


def make_frame(closes) -> pd.DataFrame:
    index = pd.date_range("2024-01-01", periods=len(closes), freq="h", tz="UTC")
    close = pd.Series(list(closes), index=index, dtype=float)
    return pd.DataFrame({
        "open": close.shift(1).fillna(close.iloc[0]),
        "high": close * 1.001,
        "low": close * 0.999,
        "close": close,
        "volume": 1.0,
    })


def test_signal_wirkt_erst_auf_der_naechsten_kerze():
    frame = make_frame([100.0, 100.0, 110.0, 110.0])
    signal = pd.Series([0.0, 1.0, 0.0, 0.0], index=frame.index)
    result = Backtester(costs=FREE).run(frame, signal)
    assert result.position.iloc[1] == pytest.approx(0.0)
    assert result.position.iloc[2] == pytest.approx(1.0)
    assert result.returns.iloc[1] == pytest.approx(0.0)
    assert result.returns.iloc[2] == pytest.approx(0.10)


def test_kosten_fressen_haeufiges_handeln():
    frame = make_frame([100.0] * 50)
    signal = pd.Series([1.0 if i % 2 == 0 else 0.0 for i in range(50)], index=frame.index)
    without_costs = Backtester(costs=FREE).run(frame, signal)
    with_costs = Backtester(costs=CostModel()).run(frame, signal)
    assert without_costs.returns.sum() == pytest.approx(0.0)
    assert with_costs.returns.sum() < -0.1


def test_stop_loss_begrenzt_den_verlust_und_bleibt_flach():
    index = pd.date_range("2024-01-01", periods=3, freq="h", tz="UTC")
    frame = pd.DataFrame({
        "open": [100.0, 100.0, 99.0],
        "high": [100.0, 100.0, 100.0],
        "low": [100.0, 90.0, 99.0],
        "close": [100.0, 99.0, 99.0],
        "volume": [1.0, 1.0, 1.0],
    }, index=index)
    signal = pd.Series([1.0, 1.0, 1.0], index=index)
    result = Backtester(costs=FREE, stop_loss=0.02).run(frame, signal)
    assert result.returns.iloc[1] == pytest.approx(-0.02)
    assert result.position.iloc[2] == pytest.approx(0.0)


def test_max_drawdown_ist_negativ_und_korrekt():
    index = pd.date_range("2024-01-01", periods=3, freq="D", tz="UTC")
    returns = pd.Series([0.10, -0.50, 0.0], index=index)
    assert max_drawdown(returns) == pytest.approx(-0.50)


def test_periods_per_year_bei_stundenkerzen():
    index = pd.date_range("2024-01-01", periods=10, freq="h", tz="UTC")
    assert periods_per_year(index) == pytest.approx(8766.0, rel=1e-3)


def test_strategie_nutzt_keine_zukunft():
    """Werden spätere Kerzen verändert, darf sich ein früheres Signal nicht ändern."""
    prices = list(100.0 + np.cumsum(np.random.default_rng(7).normal(0, 1, 300)))
    frame = make_frame(prices)
    strategy = SMACrossover(fast=5, slow=20)
    full = strategy.generate(frame)
    truncated = strategy.generate(frame.iloc[:200])
    pd.testing.assert_series_equal(full.iloc[:200], truncated, check_freq=False)


def test_summary_liefert_die_wichtigen_kennzahlen():
    frame = make_frame(list(100.0 + np.arange(500) * 0.1))
    signal = pd.Series(1.0, index=frame.index)
    result = Backtester(costs=FREE).run(frame, signal)
    stats = summary(result.returns, result.position)
    for key in ("sharpe", "max_drawdown", "trades", "exposure", "turnover_per_year"):
        assert key in stats
