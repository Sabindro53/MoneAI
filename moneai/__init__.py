"""MoneAI - Research- und Backtesting-Framework.

Das Paket beantwortet eine einzige Frage: hätte eine Idee nach realistischen
Kosten funktioniert? Orderausführung gehört bewusst nicht dazu.
"""
from .backtest import Backtester, BacktestResult, CostModel
from .data import cached_ohlc, describe, fetch_ohlc, load_csv
from .metrics import equity_curve, format_summary, summary
from .strategies import REGISTRY, Strategy, build
from .walkforward import WalkForwardConfig, WalkForwardResult, walk_forward

__all__ = [
    "Backtester",
    "BacktestResult",
    "CostModel",
    "REGISTRY",
    "Strategy",
    "WalkForwardConfig",
    "WalkForwardResult",
    "build",
    "cached_ohlc",
    "describe",
    "equity_curve",
    "fetch_ohlc",
    "format_summary",
    "load_csv",
    "summary",
    "walk_forward",
]

__version__ = "0.1.0"
