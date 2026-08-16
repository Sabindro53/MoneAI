"""Marktdaten über Krakens öffentliche REST-API.

Es werden ausschließlich öffentliche Endpunkte verwendet: kein API-Key, keine
Signatur, kein Kontozugriff. Sollte dieses Modul jemals Zugangsdaten benötigen,
stimmt etwas nicht.

Grenze der öffentlichen API: der OHLC-Endpunkt liefert höchstens 720 Kerzen pro
Anfrage und keine tiefe Historie. Für ernsthafte Tests lädt man Krakens
CSV-Archive (Support-Seite, OHLCVT) herunter und liest sie mit load_csv ein.
720 Stundenkerzen sind rund ein Monat - viel zu wenig, um über eine Strategie
zu urteilen.
"""
from __future__ import annotations

import time
from pathlib import Path
from typing import Optional, Union

import pandas as pd
import requests

PUBLIC_BASE = "https://api.kraken.com/0/public"
CACHE_DIR = Path(__file__).resolve().parents[1] / "data_cache"
VALID_INTERVALS = (1, 5, 15, 30, 60, 240, 1440, 10080, 21600)
RAW_COLUMNS = ["time", "open", "high", "low", "close", "vwap", "volume", "count"]
OHLC_COLUMNS = ["open", "high", "low", "close", "volume"]


def fetch_ohlc(pair: str = "XBTUSD", interval: int = 60,
               since: Optional[int] = None, timeout: int = 20) -> pd.DataFrame:
    """Holt OHLC-Kerzen von Kraken. Rein lesend, ohne Authentifizierung."""
    if interval not in VALID_INTERVALS:
        raise ValueError("interval muss aus " + str(VALID_INTERVALS) + " stammen")
    params = {"pair": pair, "interval": interval}
    if since is not None:
        params["since"] = int(since)
    response = requests.get(PUBLIC_BASE + "/OHLC", params=params, timeout=timeout)
    response.raise_for_status()
    payload = response.json()
    if payload.get("error"):
        raise RuntimeError("Kraken meldet: " + str(payload["error"]))
    result = payload["result"]
    key = next(name for name in result if name != "last")
    frame = pd.DataFrame(result[key], columns=RAW_COLUMNS)
    return _normalise(frame)


def load_csv(path: Union[str, Path]) -> pd.DataFrame:
    """Liest eine OHLC-Datei ein, mit oder ohne Kopfzeile.

    Krakens Archivdateien haben keine Kopfzeile und die Spaltenfolge
    time, open, high, low, close, volume, count.
    """
    probe = pd.read_csv(path, nrows=1, header=None)
    has_header = any(isinstance(value, str) for value in probe.iloc[0].tolist())
    if has_header:
        frame = pd.read_csv(path)
        frame.columns = [str(name).strip().lower() for name in frame.columns]
        if "timestamp" in frame.columns:
            frame = frame.rename(columns={"timestamp": "time"})
    else:
        names = ["time", "open", "high", "low", "close", "volume", "count"]
        frame = pd.read_csv(path, header=None, names=names[: probe.shape[1]])
    return _normalise(frame)


def cached_ohlc(pair: str = "XBTUSD", interval: int = 60,
                max_age_hours: float = 6.0) -> pd.DataFrame:
    """fetch_ohlc mit lokalem Zwischenspeicher, damit Tests offline laufen."""
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    path = CACHE_DIR / (pair + "_" + str(interval) + "m.csv")
    if path.exists():
        age_hours = (time.time() - path.stat().st_mtime) / 3600.0
        if age_hours < max_age_hours:
            return load_csv(path)
    frame = fetch_ohlc(pair=pair, interval=interval)
    dump = frame.copy()
    dump.insert(0, "time", dump.index.astype("int64") // 10 ** 9)
    dump.to_csv(path, index=False)
    return frame


def _normalise(frame: pd.DataFrame) -> pd.DataFrame:
    frame = frame.copy()
    frame.columns = [str(name).strip().lower() for name in frame.columns]
    for column in frame.columns:
        frame[column] = pd.to_numeric(frame[column], errors="coerce")
    frame["time"] = pd.to_datetime(frame["time"], unit="s", utc=True)
    frame = frame.set_index("time").sort_index()
    frame = frame[~frame.index.duplicated(keep="last")]
    missing = [column for column in OHLC_COLUMNS if column not in frame.columns]
    if missing:
        raise ValueError("Spalten fehlen: " + ", ".join(missing))
    frame = frame.dropna(subset=OHLC_COLUMNS)
    _sanity_check(frame)
    return frame


def _sanity_check(frame: pd.DataFrame) -> None:
    """Lieber laut abbrechen als still auf kaputten Daten backtesten."""
    if frame.empty:
        raise ValueError("Nach dem Bereinigen sind keine Zeilen übrig.")
    if (frame["high"] < frame["low"]).any():
        raise ValueError("high liegt unter low - die Datei ist fehlerhaft.")
    if (frame[["open", "high", "low", "close"]] <= 0).any().any():
        raise ValueError("Nicht positive Preise gefunden.")


def describe(frame: pd.DataFrame) -> str:
    start = frame.index[0].strftime("%Y-%m-%d %H:%M")
    end = frame.index[-1].strftime("%Y-%m-%d %H:%M")
    return f"{len(frame)} Kerzen von {start} bis {end} UTC"
