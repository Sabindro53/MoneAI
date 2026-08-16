"""Vektorisierter Backtester mit expliziten Kosten.

Vier Konventionen, die vor dem üblichen Selbstbetrug schützen:

* Ein Signal entsteht aus Daten bis einschließlich Kerze t.
* Gehandelt wird erst auf Kerze t+1 (position = signal.shift(1)).
* Jede Änderung der Position kostet Gebühr, halben Spread und Slippage,
  proportional zur gehandelten Menge.
* Fremdkapital aus Hebel oder Short kostet Finanzierung pro Zeit.

Ein Backtest ohne diese vier Punkte sieht immer besser aus als die Realität.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Optional

import numpy as np
import pandas as pd

from . import metrics


@dataclass(frozen=True)
class CostModel:
    """Kosten je gehandelter Kapitaleinheit.

    Die Voreinstellung entspricht Krakens Taker-Gebühr für kleine Volumina plus
    einem bewusst pessimistischen Aufschlag. Zu optimistische Kosten sind der
    häufigste Grund, warum ein guter Backtest live zusammenbricht.
    """

    taker_fee: float = 0.0026
    half_spread: float = 0.0005
    slippage: float = 0.0005
    financing_per_year: float = 0.10

    @property
    def per_unit_traded(self) -> float:
        return self.taker_fee + self.half_spread + self.slippage


@dataclass
class BacktestResult:
    data: pd.DataFrame
    position: pd.Series
    gross_returns: pd.Series
    cost_returns: pd.Series
    returns: pd.Series
    benchmark: pd.Series
    stats: Dict[str, float]

    @property
    def equity(self) -> pd.Series:
        return metrics.equity_curve(self.returns)

    def to_frame(self) -> pd.DataFrame:
        return pd.DataFrame({
            "close": self.data["close"],
            "position": self.position,
            "gross": self.gross_returns,
            "costs": self.cost_returns,
            "net": self.returns,
            "equity": self.equity,
        })

    def report(self) -> str:
        strategy = metrics.format_summary(self.stats, "Strategie nach Kosten")
        buy_hold = metrics.format_summary(metrics.summary(self.benchmark), "Kaufen und Halten")
        drag = float(self.cost_returns.sum())
        note = f"Kosten haben insgesamt {drag * 100:.2f} Prozentpunkte gekostet."
        return chr(10).join([strategy, "", buy_hold, "", note])


class Backtester:
    """Führt eine Zielpositions-Serie gegen historische Kerzen aus."""

    def __init__(self, costs: Optional[CostModel] = None, max_leverage: float = 1.0,
                 stop_loss: Optional[float] = None, price_col: str = "close") -> None:
        if max_leverage <= 0:
            raise ValueError("max_leverage muss positiv sein")
        if stop_loss is not None and not 0.0 < stop_loss < 1.0:
            raise ValueError("stop_loss ist ein Anteil, z. B. 0.02 für zwei Prozent")
        self.costs = costs or CostModel()
        self.max_leverage = float(max_leverage)
        self.stop_loss = stop_loss
        self.price_col = price_col

    def run(self, data: pd.DataFrame, signal: pd.Series) -> BacktestResult:
        if not data.index.is_monotonic_increasing:
            raise ValueError("Der Index muss zeitlich aufsteigend sortiert sein")
        price = data[self.price_col].astype(float)
        market = price.pct_change().fillna(0.0)
        target = signal.reindex(data.index).astype(float).fillna(0.0)
        target = target.clip(-self.max_leverage, self.max_leverage)

        # Der entscheidende Versatz: heute entschieden, morgen gehandelt.
        position = target.shift(1).fillna(0.0)

        if self.stop_loss is None:
            gross = position * market
        else:
            position, gross = self._apply_stop(data, position, market)

        traded = position.diff().abs()
        traded.iloc[0] = abs(float(position.iloc[0]))
        trading_costs = traded * self.costs.per_unit_traded

        long_borrow = (position.clip(lower=0.0) - 1.0).clip(lower=0.0)
        short_borrow = (-position).clip(lower=0.0)
        per_year = metrics.periods_per_year(data.index)
        financing = (long_borrow + short_borrow) * self.costs.financing_per_year / per_year

        cost_returns = trading_costs + financing
        net = gross - cost_returns
        stats = metrics.summary(net, position)
        return BacktestResult(data=data, position=position, gross_returns=gross,
                              cost_returns=cost_returns, returns=net,
                              benchmark=market, stats=stats)

    def _apply_stop(self, data: pd.DataFrame, position: pd.Series, market: pd.Series):
        """Näherung eines Stops innerhalb der Kerze.

        Beruehrt das Tief (bzw. Hoch) die Schwelle, gilt der Trade als zu genau
        dieser Schwelle geschlossen; die Position bleibt bis zum Richtungswechsel
        des Signals flach. Das ist optimistisch, weil echte Stops in schnellen
        Märkten schlechter ausgeführt werden. Enge Stops (ein Prozent und weniger)
        werden von normalem Rauschen ständig ausgelöst und verwandeln die
        Strategie in eine Gebührenmaschine - genau das zeigt dieser Vergleich.
        """
        stop = float(self.stop_loss)
        values = position.to_numpy(dtype=float).copy()
        market_values = market.to_numpy(dtype=float)
        previous_close = data[self.price_col].shift(1)
        adverse_long = (data["low"] / previous_close - 1.0).fillna(0.0).to_numpy(dtype=float)
        adverse_short = (data["high"] / previous_close - 1.0).fillna(0.0).to_numpy(dtype=float)
        realised = np.zeros(len(values))
        blocked = 0.0
        for i in range(len(values)):
            side = float(np.sign(values[i]))
            if blocked != 0.0:
                if side == blocked:
                    values[i] = 0.0
                    continue
                blocked = 0.0
            if values[i] > 0 and adverse_long[i] <= -stop:
                realised[i] = -stop * values[i]
                blocked = 1.0
            elif values[i] < 0 and adverse_short[i] >= stop:
                realised[i] = stop * values[i]
                blocked = -1.0
            else:
                realised[i] = values[i] * market_values[i]
        return (pd.Series(values, index=position.index),
                pd.Series(realised, index=position.index))
