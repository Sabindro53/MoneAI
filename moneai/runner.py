"""Der lokale Lauf: Daten holen, Signal rechnen, Demo-Wallet fortschreiben.

Der Ablauf ist einstufig und endet bei einem Ticket auf deinem Bildschirm. Es
gibt keinen zweiten Prozess, der die Demo-Wallet auf ein echtes Konto spiegelt.
Eine automatische Spiegelung wäre derselbe Autotrader wie vorher, nur mit einem
Umweg, und sie würde genau die Pause entfernen, in der ein Mensch prüfen kann,
ob die Lage noch zu der Annahme passt.

Zwei Details, die leicht übersehen werden. Bewertet wird immer die letzte
abgeschlossene Kerze, nie die laufende, sonst flackern Signale. Und ein Ticket
entsteht nur, wenn die Veränderung groß genug ist, um die Gebühr zu lohnen.
"""
from __future__ import annotations

import time
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Callable, List, Optional

import pandas as pd

from .data import fetch_ohlc
from .paper import OrderTicket, PaperWallet
from .strategies import Strategy


@dataclass
class RunnerState:
    last_candle: Optional[pd.Timestamp] = None
    last_target: float = 0.0
    last_price: float = float("nan")
    steps: int = 0
    errors: int = 0


class PaperRunner:
    """Führt eine Strategie gegen laufende Marktdaten auf einer Demo-Wallet."""

    def __init__(self, strategy: Strategy, wallet: PaperWallet, pair: str = "XBTUSD",
                 interval: int = 60, min_history: int = 200) -> None:
        self.strategy = strategy
        self.wallet = wallet
        self.pair = pair
        self.interval = interval
        self.min_history = min_history
        self.state = RunnerState()
        self.tickets: List[OrderTicket] = []

    def latest_frame(self) -> pd.DataFrame:
        frame = fetch_ohlc(pair=self.pair, interval=self.interval)
        if len(frame) < self.min_history:
            raise RuntimeError("Zu wenig Historie für die Strategie: "
                               + str(len(frame)) + " Kerzen")
        return frame

    def step(self, frame: Optional[pd.DataFrame] = None) -> Optional[OrderTicket]:
        """Ein Durchgang. Gibt ein Ticket zurück oder None, wenn nichts zu tun ist."""
        candles = self.latest_frame() if frame is None else frame
        closed = candles.iloc[:-1]
        candle_time = closed.index[-1]
        price = float(closed["close"].iloc[-1])
        self.state.last_price = price
        if self.state.last_candle is not None and candle_time <= self.state.last_candle:
            return None

        target = float(self.strategy.generate(closed).iloc[-1])
        self.state.last_candle = candle_time
        self.state.last_target = target
        self.state.steps += 1

        if target < 0:
            # Die Demo-Wallet ist ein Kassakonto. Ein Short-Signal bedeutet hier
            # schlicht: nicht investiert. Alles andere wäre eine Hülle für Hebel.
            target = 0.0

        stamp = candle_time.strftime("%Y-%m-%d %H:%M")
        reason = self.strategy.describe() + " auf Kerze " + stamp + " UTC"
        ticket = self.wallet.target_position(target, price, reason=reason,
                                             now=datetime.now(timezone.utc))
        if ticket is not None:
            self.tickets.append(ticket)
        return ticket

    def run(self, poll_seconds: int = 300, max_steps: Optional[int] = None,
            on_ticket: Optional[Callable[[OrderTicket], None]] = None) -> None:
        """Schleife auf deinem Rechner. Beenden mit Strg+C."""
        performed = 0
        while max_steps is None or performed < max_steps:
            try:
                ticket = self.step()
                if ticket is not None and on_ticket is not None:
                    on_ticket(ticket)
            except KeyboardInterrupt:
                print("Beendet. Die Demo-Wallet bleibt im Journal erhalten.")
                return
            except Exception as problem:  # Netz, Rate Limit, kaputte Antwort
                self.state.errors += 1
                print("Durchgang übersprungen: " + str(problem))
            performed += 1
            try:
                time.sleep(poll_seconds)
            except KeyboardInterrupt:
                print("Beendet.")
                return
