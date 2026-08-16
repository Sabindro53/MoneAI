"""Beispielstrategien mit einheitlicher Schnittstelle.

Eine Strategie liefert je Kerze eine Zielposition: 1.0 long, -1.0 short, 0.0
flach, Zwischenwerte für Teilpositionen. Sie darf nur Daten bis einschließlich
dieser Kerze verwenden. Deshalb sind alle Fenster rollierend und nie zentriert,
und Ausbruchsschwellen werden zusätzlich um eine Kerze versetzt.

Die Strategien hier sind bewusst alt und simpel. Sie sind Basislinien, keine
Empfehlungen: eine neue Idee muss zuerst diese Referenzen und Kaufen-und-Halten
schlagen, bevor sie interessant wird.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Type

import numpy as np
import pandas as pd

from .metrics import periods_per_year


class Strategy:
    """Basisklasse. Unterklassen implementieren generate()."""

    name = "basis"

    def generate(self, data: pd.DataFrame) -> pd.Series:
        raise NotImplementedError

    def describe(self) -> str:
        params = ", ".join(f"{key}={value}" for key, value in vars(self).items())
        return f"{self.name}({params})"

    @classmethod
    def grid(cls) -> List[dict]:
        """Parameterraster für die Walk-Forward-Suche."""
        return [{}]


@dataclass
class BuyAndHold(Strategy):
    name = "hold"

    def generate(self, data: pd.DataFrame) -> pd.Series:
        return pd.Series(1.0, index=data.index)


@dataclass
class SMACrossover(Strategy):
    """Klassische Trendfolge: schneller Durchschnitt über langsamem."""

    fast: int = 24
    slow: int = 96
    allow_short: bool = False
    name = "sma"

    def generate(self, data: pd.DataFrame) -> pd.Series:
        if self.fast >= self.slow:
            raise ValueError("fast muss kleiner als slow sein")
        close = data["close"]
        fast_line = close.rolling(self.fast).mean()
        slow_line = close.rolling(self.slow).mean()
        short_value = -1.0 if self.allow_short else 0.0
        raw = np.where(fast_line > slow_line, 1.0, short_value)
        signal = pd.Series(raw, index=data.index)
        return signal.where(slow_line.notna(), 0.0)

    @classmethod
    def grid(cls) -> List[dict]:
        return [{"fast": fast, "slow": slow}
                for fast in (12, 24, 48, 72)
                for slow in (96, 168, 336, 720)
                if fast < slow]


@dataclass
class DonchianBreakout(Strategy):
    """Ausbruch über das Hoch der letzten N Kerzen, Ausstieg über ein kürzeres Fenster."""

    entry: int = 55
    exit: int = 20
    allow_short: bool = True
    name = "donchian"

    def generate(self, data: pd.DataFrame) -> pd.Series:
        entry_high = data["high"].rolling(self.entry).max().shift(1)
        entry_low = data["low"].rolling(self.entry).min().shift(1)
        exit_high = data["high"].rolling(self.exit).max().shift(1)
        exit_low = data["low"].rolling(self.exit).min().shift(1)
        close = data["close"]
        position = np.zeros(len(data))
        current = 0.0
        for i in range(len(data)):
            price = close.iat[i]
            if current == 0.0:
                if price > entry_high.iat[i]:
                    current = 1.0
                elif self.allow_short and price < entry_low.iat[i]:
                    current = -1.0
            elif current > 0.0 and price < exit_low.iat[i]:
                current = 0.0
            elif current < 0.0 and price > exit_high.iat[i]:
                current = 0.0
            position[i] = current
        return pd.Series(position, index=data.index)

    @classmethod
    def grid(cls) -> List[dict]:
        return [{"entry": entry, "exit": exit_window}
                for entry in (20, 55, 100, 200)
                for exit_window in (10, 20, 50)
                if exit_window < entry]


@dataclass
class ZScoreReversion(Strategy):
    """Rückkehr zum Mittelwert: Einstieg bei Abweichung, Ausstieg nahe null."""

    lookback: int = 48
    entry: float = 2.0
    exit: float = 0.5
    allow_short: bool = True
    name = "zscore"

    def generate(self, data: pd.DataFrame) -> pd.Series:
        close = data["close"]
        mean = close.rolling(self.lookback).mean()
        spread = close.rolling(self.lookback).std(ddof=0).replace(0.0, np.nan)
        score = (close - mean) / spread
        position = np.zeros(len(data))
        current = 0.0
        for i in range(len(data)):
            value = score.iat[i]
            if not np.isnan(value):
                if current == 0.0:
                    if value <= -self.entry:
                        current = 1.0
                    elif self.allow_short and value >= self.entry:
                        current = -1.0
                elif current > 0.0 and value >= -self.exit:
                    current = 0.0
                elif current < 0.0 and value <= self.exit:
                    current = 0.0
            position[i] = current
        return pd.Series(position, index=data.index)

    @classmethod
    def grid(cls) -> List[dict]:
        return [{"lookback": lookback, "entry": entry}
                for lookback in (24, 48, 96, 168)
                for entry in (1.5, 2.0, 2.5, 3.0)]


@dataclass
class VolatilityTarget(Strategy):
    """Skaliert die Position einer Basisstrategie auf ein Zielrisiko.

    In ruhigen Phasen wird die Position größer, in hektischen kleiner. Das ist
    kein Gewinnbringer, es macht Drawdowns nur planbarer.
    """

    base: Strategy
    target_annual_vol: float = 0.20
    lookback: int = 168
    max_leverage: float = 1.0
    name = "voltarget"

    def generate(self, data: pd.DataFrame) -> pd.Series:
        raw = self.base.generate(data)
        returns = data["close"].pct_change()
        realised = returns.rolling(self.lookback).std(ddof=0) * np.sqrt(periods_per_year(data.index))
        scale = (self.target_annual_vol / realised.replace(0.0, np.nan)).clip(upper=self.max_leverage)
        scaled = (raw * scale).fillna(0.0)
        return scaled.clip(-self.max_leverage, self.max_leverage)


REGISTRY: Dict[str, Type[Strategy]] = {
    "hold": BuyAndHold,
    "sma": SMACrossover,
    "donchian": DonchianBreakout,
    "zscore": ZScoreReversion,
}


def build(name: str, **params) -> Strategy:
    if name not in REGISTRY:
        raise KeyError("Unbekannte Strategie " + name + ". Bekannt: " + ", ".join(sorted(REGISTRY)))
    return REGISTRY[name](**params)
