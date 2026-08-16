"""Auswertung des Demo-Journals: drei Zahlen nebeneinander.

Verglichen werden der Kontowert der Demo-Wallet, dieselbe Summe einfach
gehalten, und die Gebühren, die unterwegs angefallen sind. Die Wochentabelle
zeigt, ob ein Vorsprung stetig ist oder aus einer einzelnen Woche stammt. Das
ist der Unterschied zwischen einem Vorteil und einem Glücksgriff.

Hinweis zu den Kursdaten: Krakens öffentliche API liefert nur die letzten rund
720 Kerzen. Reicht das Journal weiter zurück, lädt man ein CSV-Archiv und
übergibt es der Auswertung.
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Optional, Union

import pandas as pd

from . import metrics

DEFAULT_JOURNAL = Path("results/paper_journal.csv")


def load_journal(path: Union[str, Path] = DEFAULT_JOURNAL) -> pd.DataFrame:
    location = Path(path)
    if not location.exists():
        raise FileNotFoundError("Kein Journal unter " + str(location)
                                + ". Erst examples/run_paper.py laufen lassen.")
    frame = pd.read_csv(location)
    if frame.empty:
        raise ValueError("Das Journal ist leer, es gab bisher keinen simulierten Trade.")
    frame["zeit"] = pd.to_datetime(frame["zeit"], utc=True)
    return frame.sort_values("zeit").reset_index(drop=True)


def rebuild_equity(journal: pd.DataFrame, prices: pd.DataFrame, start_cash: float) -> pd.Series:
    """Bewertet Bargeld und Position des Journals an jeder Kerze neu."""
    marks = journal.set_index("zeit")[["cash_danach", "position_danach"]]
    marks = marks[~marks.index.duplicated(keep="last")]
    merged = marks.reindex(prices.index.union(marks.index)).sort_index().ffill()
    aligned = merged.reindex(prices.index)
    cash = aligned["cash_danach"].fillna(float(start_cash))
    position = aligned["position_danach"].fillna(0.0)
    return cash + position * prices["close"].astype(float)


def buy_and_hold_equity(prices: pd.DataFrame, start_cash: float, fee: float = 0.0026) -> pd.Series:
    """Einmal kaufen, liegen lassen. Die Einstiegsgebühr wird fair mitgerechnet."""
    first_price = float(prices["close"].iloc[0])
    quantity = float(start_cash) * (1.0 - fee) / first_price
    return quantity * prices["close"].astype(float)


def _weekly_percent(series: pd.Series) -> pd.Series:
    weekly = series.resample("W").last()
    previous = weekly.shift(1)
    previous.iloc[0] = float(series.iloc[0])
    return (weekly / previous - 1.0) * 100.0


def weekly_table(paper: pd.Series, hold: pd.Series) -> pd.DataFrame:
    table = pd.DataFrame({
        "demo": _weekly_percent(paper),
        "halten": _weekly_percent(hold),
    })
    table["differenz"] = table["demo"] - table["halten"]
    table.index = table.index.strftime("%Y-%m-%d")
    return table.round(2)


@dataclass
class Review:
    journal: pd.DataFrame
    paper_equity: pd.Series
    hold_equity: pd.Series
    weekly: pd.DataFrame
    start_cash: float

    @property
    def paper_end(self) -> float:
        return float(self.paper_equity.iloc[-1])

    @property
    def hold_end(self) -> float:
        return float(self.hold_equity.iloc[-1])

    @property
    def fees(self) -> float:
        return float(self.journal["gebuehr"].sum())

    def verdict(self) -> str:
        trades = len(self.journal)
        if trades < 30:
            return ("Bisher " + str(trades) + " Trades. Unter etwa dreissig Trades ist jeder "
                    "Unterschied Rauschen, in beide Richtungen.")
        if self.paper_end <= self.hold_end:
            return ("Kein Vorteil: einfach halten war gleich gut oder besser. Das ist ein "
                    "vollwertiges Ergebnis und es hat nichts gekostet.")
        edge = self.paper_end / self.hold_end - 1.0
        if edge < 0.02:
            return "Vorsprung unter zwei Prozent. Das kann eine einzelne gute Woche sein."
        return (f"Vorsprung von {edge * 100:.1f} Prozent. Vor jedem weiteren Schritt in der "
                "Wochentabelle prüfen, ob er stetig ist oder aus einer Woche stammt.")

    def report(self) -> str:
        start = self.paper_equity.index[0].strftime("%Y-%m-%d")
        end = self.paper_equity.index[-1].strftime("%Y-%m-%d")
        head = [
            "Auswertung " + start + " bis " + end,
            "",
            f"Startkapital        {self.start_cash:>12.2f}",
            f"Demo-Wallet         {self.paper_end:>12.2f}",
            f"Nur gehalten        {self.hold_end:>12.2f}",
            f"Unterschied         {self.paper_end - self.hold_end:>12.2f}",
            f"Gebühren gesamt     {self.fees:>12.2f}",
            f"Trades              {len(self.journal):>12d}",
            "",
        ]
        paper_stats = metrics.summary(self.paper_equity.pct_change().fillna(0.0))
        hold_stats = metrics.summary(self.hold_equity.pct_change().fillna(0.0))
        body = [
            metrics.format_summary(paper_stats, "Demo-Wallet"),
            "",
            metrics.format_summary(hold_stats, "Nur gehalten"),
            "",
            "Woche für Woche in Prozent",
            self.weekly.to_string(),
            "",
            self.verdict(),
        ]
        return chr(10).join(head + body)


def review(prices: pd.DataFrame, journal_path: Union[str, Path] = DEFAULT_JOURNAL,
           start_cash: Optional[float] = None, fee: float = 0.0026) -> Review:
    journal = load_journal(journal_path)
    window = prices.loc[prices.index >= journal["zeit"].iloc[0]]
    if window.empty:
        raise ValueError("Kursdaten und Journal überschneiden sich nicht. "
                         "Historie als CSV laden und mit --csv übergeben.")
    if start_cash is None:
        first = journal.iloc[0]
        start_cash = (float(first["cash_danach"])
                      + float(first["position_danach"]) * float(first["preis"])
                      + float(first["gebuehr"]))
    paper = rebuild_equity(journal, window, start_cash)
    hold = buy_and_hold_equity(window, start_cash, fee)
    return Review(journal=journal, paper_equity=paper, hold_equity=hold,
                  weekly=weekly_table(paper, hold), start_cash=float(start_cash))
