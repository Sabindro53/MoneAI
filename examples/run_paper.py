"""Lokaler Demo-Lauf mit Ticket-Ausgabe.

    python examples/run_paper.py --once
    python examples/run_paper.py --strategy donchian --poll-seconds 300
    python examples/run_paper.py --once --account

Das Skript läuft auf deinem Rechner, holt öffentliche Marktdaten, führt eine
Demo-Wallet und zeigt dir Order-Vorschläge. Es sendet nichts an dein Konto.
Mit --account liest es zusätzlich deine Kraken-Bestände, wenn in .env ein
Schlüssel mit reinen Leserechten hinterlegt ist.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from moneai.config import load_settings, permission_warning  # noqa: E402
from moneai.paper import OrderTicket, PaperWallet  # noqa: E402
from moneai.runner import PaperRunner  # noqa: E402
from moneai.strategies import REGISTRY, build  # noqa: E402


def parse_args(argv=None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="MoneAI Demo-Wallet, lokal")
    parser.add_argument("--strategy", default="sma", choices=sorted(REGISTRY))
    parser.add_argument("--pair", default=None, help="überschreibt MONEAI_PAIR")
    parser.add_argument("--interval", type=int, default=None, help="Kerzenlänge in Minuten")
    parser.add_argument("--start-cash", dest="start_cash", type=float, default=None)
    parser.add_argument("--poll-seconds", dest="poll_seconds", type=int, default=300)
    parser.add_argument("--max-steps", dest="max_steps", type=int, default=None)
    parser.add_argument("--once", action="store_true", help="nur ein Durchgang")
    parser.add_argument("--journal", type=Path, default=Path("results/paper_journal.csv"))
    parser.add_argument("--account", action="store_true",
                        help="Kontostand lesen (nur mit Leserechte-Schlüssel)")
    return parser.parse_args(argv)


def show_account(settings) -> None:
    if not settings.has_credentials:
        print("Keine Zugangsdaten in .env gefunden. Kontoanzeige übersprungen.")
        return
    from moneai.kraken_private import ReadOnlyKrakenClient
    try:
        client = ReadOnlyKrakenClient(settings.api_key, settings.api_secret)
        print(client.summary())
    except Exception as problem:
        print("Konto konnte nicht gelesen werden: " + str(problem))
        print("Prüfe, ob der Schlüssel die Rechte Query Funds und Query Ledger hat.")
    print("")


def main(argv=None) -> int:
    args = parse_args(argv)
    settings = load_settings()

    warning = permission_warning()
    if warning:
        print(warning)
    if args.account:
        show_account(settings)

    pair = args.pair or settings.pair
    interval = args.interval or settings.interval
    start_cash = args.start_cash if args.start_cash is not None else settings.start_cash

    wallet = PaperWallet(start_cash=start_cash, pair=pair, journal_path=args.journal)
    runner = PaperRunner(build(args.strategy), wallet, pair=pair, interval=interval)

    print("Demo-Lauf: " + runner.strategy.describe() + " auf " + pair
          + ", Kerzen " + str(interval) + " Minuten")
    print("Journal: " + str(args.journal))
    print("Es werden keine Orders gesendet." + chr(10))

    def announce(ticket: OrderTicket) -> None:
        print(ticket.render())

    if args.once:
        ticket = runner.step()
        if ticket is None:
            print("Keine Änderung nötig.")
        else:
            announce(ticket)
        print(wallet.snapshot(runner.state.last_price))
        return 0

    try:
        runner.run(poll_seconds=args.poll_seconds, max_steps=args.max_steps, on_ticket=announce)
    finally:
        print(chr(10) + wallet.snapshot(runner.state.last_price))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
