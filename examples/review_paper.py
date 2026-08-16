"""Der wöchentliche Blick auf das Demo-Journal.

    python examples/review_paper.py
    python examples/review_paper.py --csv XBTUSD_60.csv
    python examples/review_paper.py --plot

Zeigt drei Zahlen nebeneinander: was die Demo-Wallet gemacht hat, was einfaches
Halten gemacht hätte, und was die Gebühren gekostet haben. Dazu eine
Wochentabelle und ein nüchternes Urteil.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from moneai import data as market_data  # noqa: E402
from moneai.config import load_settings  # noqa: E402
from moneai.review import DEFAULT_JOURNAL, review  # noqa: E402


def parse_args(argv=None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="MoneAI: Demo-Journal auswerten")
    parser.add_argument("--journal", type=Path, default=DEFAULT_JOURNAL)
    parser.add_argument("--pair", default=None)
    parser.add_argument("--interval", type=int, default=None)
    parser.add_argument("--csv", type=Path, default=None,
                        help="Kurshistorie aus Datei, nötig für Zeiträume über 720 Kerzen")
    parser.add_argument("--start-cash", dest="start_cash", type=float, default=None)
    parser.add_argument("--fee", type=float, default=0.0026)
    parser.add_argument("--plot", action="store_true")
    return parser.parse_args(argv)


def show_plot(outcome) -> None:
    try:
        import matplotlib.pyplot as plt
    except ImportError:
        print("matplotlib fehlt - pip install matplotlib")
        return
    axis = outcome.paper_equity.plot(label="Demo-Wallet")
    outcome.hold_equity.plot(ax=axis, label="Nur gehalten")
    axis.set_title("Demo-Wallet gegen Kaufen-und-Halten")
    axis.legend()
    plt.tight_layout()
    plt.show()


def main(argv=None) -> int:
    args = parse_args(argv)
    settings = load_settings()
    pair = args.pair or settings.pair
    interval = args.interval or settings.interval

    if args.csv is not None:
        prices = market_data.load_csv(args.csv)
    else:
        prices = market_data.cached_ohlc(pair, interval)
    print(market_data.describe(prices))

    outcome = review(prices, journal_path=args.journal,
                     start_cash=args.start_cash, fee=args.fee)

    if prices.index[0] > outcome.journal["zeit"].iloc[0]:
        print("Achtung: die Kursdaten beginnen später als der erste Journal-Eintrag. "
              "Der Vergleich deckt nur den gemeinsamen Zeitraum ab. "
              "Für die volle Historie ein CSV-Archiv mit --csv übergeben.")
    print("")
    print(outcome.report())

    if args.plot:
        show_plot(outcome)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
