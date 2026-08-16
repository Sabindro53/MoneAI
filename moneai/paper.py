"""Demo-Wallet: ein Konto, das nur im Arbeitsspeicher und in einer CSV lebt.

Die Wallet kennt Bargeld, eine Position und Kosten. Sie führt Buch über jeden
simulierten Trade und erzeugt zu jeder Änderung ein Ticket: die Beschreibung
dessen, was ein Mensch in der Kraken-Oberfläche eingeben müsste. Ausgeführt
wird nichts.

Es handelt sich um ein Kassakonto ohne Fremdkapital. Gekauft wird höchstens für
das vorhandene Bargeld, verkauft höchstens die vorhandene Position. Damit kann
die Simulation nicht versehentlich etwas darstellen, das ein Konto ohne
Margin-Freigabe gar nicht tun könnte.
"""
from __future__ import annotations

import csv
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Optional

JOURNAL_HEADER = ["zeit", "paar", "richtung", "menge", "preis", "gebuehr",
                  "cash_danach", "position_danach", "equity_danach", "anlass"]


@dataclass
class Fill:
    time: datetime
    pair: str
    side: str
    quantity: float
    price: float
    fee: float
    cash_after: float
    position_after: float
    equity_after: float
    reason: str


@dataclass
class OrderTicket:
    """Was ein Mensch eingeben müsste, wenn er dieser Simulation folgen wollte."""

    time: datetime
    pair: str
    side: str
    quantity: float
    reference_price: float
    reason: str

    def render(self) -> str:
        rule = "-" * 52
        lines = [
            rule,
            "ORDER-VORSCHLAG - nicht ausgeführt, nicht übermittelt",
            f"Zeit       {self.time:%Y-%m-%d %H:%M} UTC",
            f"Paar       {self.pair}",
            f"Richtung   {self.side.upper()}",
            f"Menge      {self.quantity:.8f}",
            f"Referenz   {self.reference_price:.2f}",
            f"Anlass     {self.reason}",
            "Prüfen, entscheiden, gegebenenfalls selbst eingeben.",
            rule,
        ]
        return chr(10).join(lines)


class PaperWallet:
    """Simuliertes Kassakonto mit Gebühren, Slippage und Mindestordergröße."""

    def __init__(self, start_cash: float = 1000.0, pair: str = "XBTUSD",
                 fee: float = 0.0026, slippage: float = 0.0005,
                 min_notional: float = 10.0, journal_path: Optional[Path] = None) -> None:
        self.start_cash = float(start_cash)
        self.cash = float(start_cash)
        self.position = 0.0
        self.pair = pair
        self.fee = float(fee)
        self.slippage = float(slippage)
        self.min_notional = float(min_notional)
        self.fills: List[Fill] = []
        self.journal_path = journal_path
        if journal_path is not None:
            self._prepare_journal(journal_path)

    def equity(self, price: float) -> float:
        return self.cash + self.position * price

    def target_position(self, target_fraction: float, price: float,
                        reason: str = "", now: Optional[datetime] = None) -> Optional[OrderTicket]:
        """Bringt die Wallet auf den gewünschten Anteil und liefert das Ticket.

        target_fraction ist der Anteil des Kontowerts, der in der Basiswährung
        stehen soll: 1.0 voll investiert, 0.0 flach. Werte außerhalb von null bis
        eins werden abgeschnitten, weil diese Wallet weder Hebel noch Leerverkauf
        kennt.
        """
        moment = now or datetime.now(timezone.utc)
        fraction = max(0.0, min(1.0, float(target_fraction)))
        equity_before = self.equity(price)
        desired_quantity = fraction * equity_before / price
        delta = desired_quantity - self.position
        side = "buy" if delta > 0 else "sell"
        fill_price = price * (1.0 + self.slippage) if delta > 0 else price * (1.0 - self.slippage)

        if delta > 0:
            # Die Gebühr wird aus demselben Bargeld bezahlt wie der Kauf.
            affordable = self.cash / (fill_price * (1.0 + self.fee))
            delta = min(delta, max(0.0, affordable))
        else:
            delta = max(delta, -self.position)

        if abs(delta) * price < self.min_notional:
            return None

        cash_flow = delta * fill_price
        fee_paid = abs(cash_flow) * self.fee
        self.cash -= cash_flow + fee_paid
        self.position += delta

        fill = Fill(time=moment, pair=self.pair, side=side, quantity=abs(delta),
                    price=fill_price, fee=fee_paid, cash_after=self.cash,
                    position_after=self.position, equity_after=self.equity(price),
                    reason=reason)
        self.fills.append(fill)
        self._append_journal(fill)
        return OrderTicket(time=moment, pair=self.pair, side=side, quantity=abs(delta),
                           reference_price=price, reason=reason)

    def snapshot(self, price: float) -> str:
        value = self.equity(price)
        change = value / self.start_cash - 1.0 if self.start_cash else float("nan")
        lines = [
            "Demo-Wallet",
            f"  Bargeld      {self.cash:>14.2f}",
            f"  Position     {self.position:>14.8f}",
            f"  Kurs         {price:>14.2f}",
            f"  Kontowert    {value:>14.2f}",
            f"  Veränderung  {change * 100:>13.2f} %",
            f"  Trades       {len(self.fills):>14d}",
            f"  Gebühren     {sum(f.fee for f in self.fills):>14.2f}",
        ]
        return chr(10).join(lines)

    def _prepare_journal(self, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        if not path.exists():
            with path.open("w", newline="", encoding="utf-8") as handle:
                csv.writer(handle).writerow(JOURNAL_HEADER)

    def _append_journal(self, fill: Fill) -> None:
        if self.journal_path is None:
            return
        with self.journal_path.open("a", newline="", encoding="utf-8") as handle:
            csv.writer(handle).writerow([
                fill.time.isoformat(timespec="seconds"), fill.pair, fill.side,
                round(fill.quantity, 10), round(fill.price, 4), round(fill.fee, 6),
                round(fill.cash_after, 4), round(fill.position_after, 10),
                round(fill.equity_after, 4), fill.reason,
            ])
"""Demo-Wallet: ein Konto, das nur im Arbeitsspeicher und in einer CSV lebt.

Die Wallet kennt Bargeld, eine Position und Kosten. Sie führt Buch über jeden
simulierten Trade und erzeugt zu jeder Änderung ein Ticket: die Beschreibung
dessen, was ein Mensch in der Kraken-Oberfläche eingeben müsste. Ausgeführt
wird nichts.
"""
from __future__ import annotations

import csv
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Optional

JOURNAL_HEADER = ["zeit", "paar", "richtung", "menge", "preis", "gebuehr",
                  "cash_danach", "position_danach", "equity_danach", "anlass"]


@dataclass
class Fill:
    time: datetime
    pair: str
    side: str
    quantity: float
    price: float
    fee: float
    cash_after: float
    position_after: float
    equity_after: float
    reason: str


@dataclass
class OrderTicket:
    """Was ein Mensch eingeben müsste, wenn er dieser Simulation folgen wollte."""

    time: datetime
    pair: str
    side: str
    quantity: float
    reference_price: float
    reason: str

    def render(self) -> str:
        rule = "-" * 52
        lines = [
            rule,
            "ORDER-VORSCHLAG - nicht ausgeführt, nicht übermittelt",
            f"Zeit       {self.time:%Y-%m-%d %H:%M} UTC",
            f"Paar       {self.pair}",
            f"Richtung   {self.side.upper()}",
            f"Menge      {self.quantity:.8f}",
            f"Referenz   {self.reference_price:.2f}",
            f"Anlass     {self.reason}",
            "Prüfen, entscheiden, gegebenenfalls selbst eingeben.",
            rule,
        ]
        return chr(10).join(lines)


class PaperWallet:
    """Simuliertes Konto mit Gebühren, Slippage und Mindestordergröße."""

    def __init__(self, start_cash: float = 1000.0, pair: str = "XBTUSD",
                 fee: float = 0.0026, slippage: float = 0.0005,
                 min_notional: float = 10.0, journal_path: Optional[Path] = None) -> None:
        self.start_cash = float(start_cash)
        self.cash = float(start_cash)
        self.position = 0.0
        self.pair = pair
        self.fee = float(fee)
        self.slippage = float(slippage)
        self.min_notional = float(min_notional)
        self.fills: List[Fill] = []
        self.journal_path = journal_path
        if journal_path is not None:
            self._prepare_journal(journal_path)

    def equity(self, price: float) -> float:
        return self.cash + self.position * price

    def target_position(self, target_fraction: float, price: float,
                        reason: str = "", now: Optional[datetime] = None) -> Optional[OrderTicket]:
        """Bringt die Wallet auf den gewünschten Anteil und liefert das Ticket.

        target_fraction ist der Anteil des Kontowerts, der in der Basiswährung
        stehen soll: 1.0 voll investiert, 0.0 flach. Werte über 1.0 werden
        abgeschnitten, weil diese Wallet kein Fremdkapital kennt.
        """
        moment = now or datetime.now(timezone.utc)
        fraction = max(0.0, min(1.0, float(target_fraction)))
        equity_before = self.equity(price)
        desired_quantity = fraction * equity_before / price
        delta = desired_quantity - self.position
        if abs(delta) * price < self.min_notional:
            return None

        side = "buy" if delta > 0 else "sell"
        fill_price = price * (1.0 + self.slippage) if delta > 0 else price * (1.0 - self.slippage)
        cash_flow = delta * fill_price
        fee_paid = abs(cash_flow) * self.fee
        self.cash -= cash_flow + fee_paid
        self.position += delta

        fill = Fill(time=moment, pair=self.pair, side=side, quantity=abs(delta),
                    price=fill_price, fee=fee_paid, cash_after=self.cash,
                    position_after=self.position, equity_after=self.equity(price),
                    reason=reason)
        self.fills.append(fill)
        self._append_journal(fill)
        return OrderTicket(time=moment, pair=self.pair, side=side, quantity=abs(delta),
                           reference_price=price, reason=reason)

    def snapshot(self, price: float) -> str:
        value = self.equity(price)
        change = value / self.start_cash - 1.0 if self.start_cash else float("nan")
        lines = [
            "Demo-Wallet",
            f"  Bargeld      {self.cash:>14.2f}",
            f"  Position     {self.position:>14.8f}",
            f"  Kurs         {price:>14.2f}",
            f"  Kontowert    {value:>14.2f}",
            f"  Veränderung  {change * 100:>13.2f} %",
            f"  Trades       {len(self.fills):>14d}",
            f"  Gebühren     {sum(f.fee for f in self.fills):>14.2f}",
        ]
        return chr(10).join(lines)

    def _prepare_journal(self, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        if not path.exists():
            with path.open("w", newline="", encoding="utf-8") as handle:
                csv.writer(handle).writerow(JOURNAL_HEADER)

    def _append_journal(self, fill: Fill) -> None:
        if self.journal_path is None:
            return
        with self.journal_path.open("a", newline="", encoding="utf-8") as handle:
            csv.writer(handle).writerow([
                fill.time.isoformat(timespec="seconds"), fill.pair, fill.side,
                round(fill.quantity, 10), round(fill.price, 4), round(fill.fee, 6),
                round(fill.cash_after, 4), round(fill.position_after, 10),
                round(fill.equity_after, 4), fill.reason,
            ])
