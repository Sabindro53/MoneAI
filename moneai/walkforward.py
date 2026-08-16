"""Walk-Forward-Validierung.

Parameter werden auf einem Trainingsfenster gewählt und auf dem unmittelbar
folgenden Testfenster angewendet, das bei der Wahl nicht sichtbar war. Danach
rutschen beide Fenster weiter. Nur die aneinandergehängten Testabschnitte
zählen als Ergebnis.

In-Sample lässt sich fast jede Zeitreihe profitabel aussehen lassen. Der
Abstand zwischen In-Sample- und Out-of-Sample-Kennzahl ist ein direktes Maß
für Überanpassung. Wird er groß, hat man die Vergangenheit auswendig gelernt.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable, List, Optional, Type

import numpy as np
import pandas as pd

from . import metrics
from .backtest import Backtester, BacktestResult
from .strategies import Strategy


@dataclass
class WalkForwardConfig:
    train_bars: int = 2000
    test_bars: int = 500
    min_trades: float = 5.0


@dataclass
class Fold:
    train_start: pd.Timestamp
    train_end: pd.Timestamp
    test_start: pd.Timestamp
    test_end: pd.Timestamp
    params: dict
    in_sample_score: float
    out_of_sample_score: float


@dataclass
class WalkForwardResult:
    folds: List[Fold]
    returns: pd.Series
    stats: dict

    def fold_frame(self) -> pd.DataFrame:
        return pd.DataFrame([{
            "test_start": fold.test_start,
            "test_end": fold.test_end,
            "params": fold.params,
            "in_sample": round(fold.in_sample_score, 2),
            "out_of_sample": round(fold.out_of_sample_score, 2),
        } for fold in self.folds])

    def degradation(self) -> float:
        """Mittlerer Abfall vom Trainings- zum Testergebnis."""
        if not self.folds:
            return float("nan")
        inside = np.mean([fold.in_sample_score for fold in self.folds])
        outside = np.mean([fold.out_of_sample_score for fold in self.folds])
        return float(inside - outside)

    def report(self) -> str:
        lines = [metrics.format_summary(self.stats, "Out-of-Sample gesamt"), ""]
        lines.append(f"Fenster: {len(self.folds)}")
        lines.append(f"Mittlerer Abfall In-Sample zu Out-of-Sample: {self.degradation():.2f}")
        chosen = [tuple(sorted(fold.params.items())) for fold in self.folds]
        distinct = len(set(chosen))
        lines.append(f"Verschiedene Parametersätze über die Fenster: {distinct} von {len(chosen)}")
        if distinct > max(1, len(chosen) // 2):
            lines.append("Die Parameterwahl ist instabil - das spricht gegen einen echten Effekt.")
        lines.append("")
        lines.append(self.fold_frame().to_string(index=False))
        return chr(10).join(lines)


def default_objective(result: BacktestResult, min_trades: float = 5.0) -> float:
    """Sharpe nach Kosten, aber nur bei ausreichender Trade-Zahl."""
    score = result.stats.get("sharpe", float("nan"))
    trades = result.stats.get("trades", 0.0)
    if np.isnan(score) or trades < min_trades:
        return float("-inf")
    return float(score)


def walk_forward(data: pd.DataFrame, strategy_cls: Type[Strategy],
                 backtester: Optional[Backtester] = None,
                 config: Optional[WalkForwardConfig] = None,
                 grid: Optional[List[dict]] = None,
                 objective: Optional[Callable[[BacktestResult], float]] = None) -> WalkForwardResult:
    tester = backtester or Backtester()
    setup = config or WalkForwardConfig()
    search_space = grid if grid is not None else strategy_cls.grid()
    score_of = objective or (lambda result: default_objective(result, setup.min_trades))

    needed = setup.train_bars + setup.test_bars
    if len(data) < needed:
        raise ValueError("Zu wenig Daten: mindestens " + str(needed) + " Kerzen nötig, "
                         + str(len(data)) + " vorhanden")

    folds: List[Fold] = []
    pieces: List[pd.Series] = []
    start = 0
    while start + needed <= len(data):
        train = data.iloc[start:start + setup.train_bars]
        test = data.iloc[start + setup.train_bars:start + needed]
        window = data.iloc[start:start + needed]

        best_params = None
        best_score = float("-inf")
        for params in search_space:
            candidate = strategy_cls(**params)
            score = score_of(tester.run(train, candidate.generate(train)))
            if score > best_score:
                best_params, best_score = params, score
        if best_params is None:
            best_params, best_score = search_space[0], float("nan")

        chosen = strategy_cls(**best_params)
        # Signal auf dem gesamten Fenster rechnen, damit rollierende Fenster zu
        # Beginn des Tests bereits gefüllt sind. Bewertet wird nur der Testteil.
        signal = chosen.generate(window).loc[test.index]
        result = tester.run(test, signal)

        folds.append(Fold(train_start=train.index[0], train_end=train.index[-1],
                          test_start=test.index[0], test_end=test.index[-1],
                          params=dict(best_params), in_sample_score=float(best_score),
                          out_of_sample_score=score_of(result)))
        pieces.append(result.returns)
        start += setup.test_bars

    out_of_sample = pd.concat(pieces)
    return WalkForwardResult(folds=folds, returns=out_of_sample,
                             stats=metrics.summary(out_of_sample))
