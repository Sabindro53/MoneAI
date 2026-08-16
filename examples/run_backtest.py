"""Kommandozeilen-Einstieg: eine Idee gegen historische Kerzen prüfen.

Beispiele:

    python examples/run_backtest.py --strategy sma
    python examples/run_backtest.py --csv XBTUSD_60.csv --strategy donchian --walkforward
    python examples/run_backtest.py --csv XBTUSD_60.csv --strategy sma --stop-loss 0.01

Der letzte Aufruf zeigt, was ein sehr enger Stop mit einer Strategie anstellt:
in der Regel viele kleine Verluste plus Gebühren.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from moneai import data as market_data  # noqa: E402
from moneai.backtest import Backtester, CostModel  # noqa: E402
from moneai.metrics import equity_curve  # noqa: E402
from moneai.strategies import REGISTRY, build  # noqa: E402
from moneai.walkforward import WalkForwardConfig, walk_forward  # noqa: E402


def parse_args(argv=None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="MoneAI Backtest")
    parser.add_argument("--pair", default="XBTUSD", help="Kraken-Paar, öffentliche API")
    parser.add_argument("--csv", type=Path, default=None, help="lokale OHLC-Datei statt API")
    parser.add_argument("--interval", type=int, default=60, help="Kerzenlänge in Minuten")
    parser.add_argument("--strategy", default="sma", choices=sorted(REGISTRY))
    parser.add_argument("--fee", type=float, default=0.0026, help="Taker-Gebühr je Trade")
    parser.add_argument("--slippage", type=float, default=0.0005)
    parser.add_argument("--leverage", type=float, default=1.0, help="nur als Was-wäre-wenn")
    parser.add_argument("--stop-loss", dest="stop_loss", type=float, default=None,
                        help="Anteil, z. B. 0.01 für ein Prozent")
    parser.add_argument("--walkforward", action="store_true")
    parser.add_argument("--train-bars", dest="train_bars", type=int, default=2000)
    parser.add_argument("--test-bars", dest="test_bars", type=int, default=500)
    parser.add_argument("--plot", action="store_true")
    return parser.parse_args(argv)


def load_frame(args: argparse.Namespace):
    if args.csv is not None:
        frame = market_data.load_csv(args.csv)
    else:
        frame = market_data.cached_ohlc(args.pair, args.interval)
    print(market_data.describe(frame))
    return frame


def show_plot(returns) -> None:
    try:
        import matplotlib.pyplot as plt
    except ImportError:
        print("matplotlib fehlt - pip install matplotlib")
        return
    equity_curve(returns).plot(logy=True, title="Kapitalkurve nach Kosten")
    plt.tight_layout()
    plt.show()


def main(argv=None) -> int:
    args = parse_args(argv)
    frame = load_frame(args)

    costs = CostModel(taker_fee=args.fee, slippage=args.slippage)
    tester = Backtester(costs=costs, max_leverage=args.leverage, stop_loss=args.stop_loss)

    if args.walkforward:
        setup = WalkForwardConfig(train_bars=args.train_bars, test_bars=args.test_bars)
        outcome = walk_forward(frame, REGISTRY[args.strategy], backtester=tester, config=setup)
        print(outcome.report())
        series = outcome.returns
    else:
        strategy = build(args.strategy)
        print("Strategie: " + strategy.describe())
        outcome = tester.run(frame, strategy.generate(frame))
        print(outcome.report())
        series = outcome.returns
        print(chr(10) + "Hinweis: ein einzelner Durchlauf ohne Walk-Forward sagt wenig aus.")

    if len(frame) < 1000:
        print("Warnung: unter 1000 Kerzen ist jedes Ergebnis überwiegend Rauschen.")
    if args.plot:
        show_plot(series)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
