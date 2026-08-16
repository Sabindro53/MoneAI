"""Tests für Demo-Wallet und Auswertung."""
from __future__ import annotations

import csv
import sys
from pathlib import Path

import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from moneai.paper import JOURNAL_HEADER, PaperWallet  # noqa: E402
from moneai.review import review  # noqa: E402


def make_prices() -> pd.DataFrame:
    index = pd.date_range("2024-01-01", periods=5, freq="h", tz="UTC")
    close = pd.Series([100.0, 100.0, 110.0, 110.0, 120.0], index=index)
    return pd.DataFrame({
        "open": close,
        "high": close,
        "low": close,
        "close": close,
        "volume": 1.0,
    })


def write_journal(path: Path) -> None:
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerow(JOURNAL_HEADER)
        writer.writerow(["2024-01-01T01:00:00+00:00", "XBTUSD", "buy", 5.0, 100.0, 1.3,
                         498.7, 5.0, 998.7, "test"])


def test_wallet_kauft_nur_was_das_bargeld_hergibt():
    wallet = PaperWallet(start_cash=1000.0, slippage=0.0, fee=0.0026)
    ticket = wallet.target_position(1.0, 100.0, reason="test")
    assert ticket is not None
    assert ticket.side == "buy"
    # 1000 reichen für 9.974 Einheiten, weil die Gebühr aus demselben Geld kommt.
    assert wallet.position == pytest.approx(9.974067, rel=1e-5)
    assert wallet.cash == pytest.approx(0.0, abs=1e-9)
    assert wallet.fills[0].fee == pytest.approx(2.593258, rel=1e-5)


def test_wallet_ignoriert_winzige_anpassungen():
    wallet = PaperWallet(start_cash=1000.0, slippage=0.0, min_notional=10.0)
    wallet.target_position(1.0, 100.0, reason="einstieg")
    unchanged = wallet.target_position(1.0, 100.0, reason="nochmal")
    assert unchanged is None


def test_wallet_kann_nicht_short_gehen():
    wallet = PaperWallet(start_cash=1000.0, slippage=0.0)
    wallet.target_position(-1.0, 100.0, reason="short")
    assert wallet.position == pytest.approx(0.0)
    assert wallet.cash == pytest.approx(1000.0)


def test_wallet_verkauft_hoechstens_die_position():
    wallet = PaperWallet(start_cash=1000.0, slippage=0.0)
    wallet.target_position(1.0, 100.0, reason="einstieg")
    wallet.target_position(0.0, 100.0, reason="ausstieg")
    assert wallet.position == pytest.approx(0.0)
    assert wallet.cash > 0.0


def test_review_vergleicht_demo_mit_halten(tmp_path):
    journal_path = tmp_path / "journal.csv"
    write_journal(journal_path)
    outcome = review(make_prices(), journal_path=journal_path)
    assert outcome.start_cash == pytest.approx(1000.0)
    assert outcome.paper_end == pytest.approx(1098.7)
    assert outcome.hold_end == pytest.approx(1196.88)
    assert "Rauschen" in outcome.verdict()
    assert "differenz" in outcome.weekly.columns


def test_review_meldet_fehlende_ueberschneidung(tmp_path):
    journal_path = tmp_path / "journal.csv"
    write_journal(journal_path)
    frueher = make_prices()
    frueher.index = frueher.index - pd.Timedelta(days=30)
    with pytest.raises(ValueError):
        review(frueher, journal_path=journal_path)
