"""Lokale Konfiguration. Geheimnisse bleiben auf dem Rechner.

Zugangsdaten stehen in der Datei .env im Projektordner, die von git ignoriert
wird. Diese Datei füllst du selbst aus. Kein Teil dieses Projekts versendet,
protokolliert oder kopiert sie, und __repr__ der Einstellungen zeigt den
Schlüssel nicht an, damit er nicht versehentlich in einem Log landet.
"""
from __future__ import annotations

import os
import stat
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Optional

PROJECT_ROOT = Path(__file__).resolve().parents[1]
ENV_PATH = PROJECT_ROOT / ".env"


def read_env_file(path: Path = ENV_PATH) -> Dict[str, str]:
    """Minimaler Parser, damit keine zusätzliche Abhängigkeit nötig ist."""
    values: Dict[str, str] = {}
    if not path.exists():
        return values
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        name, _, value = line.partition("=")
        values[name.strip()] = value.strip().strip('"').strip("'")
    return values


def permission_warning(path: Path = ENV_PATH) -> Optional[str]:
    """Meldet, wenn die Schlüsseldatei für andere Konten lesbar ist."""
    if os.name == "nt" or not path.exists():
        return None
    mode = stat.S_IMODE(path.stat().st_mode)
    if mode & 0o077:
        return "Die Datei .env ist auch für andere lesbar. Bitte: chmod 600 .env"
    return None


@dataclass(frozen=True)
class Settings:
    api_key: str = ""
    api_secret: str = ""
    pair: str = "XBTUSD"
    interval: int = 60
    start_cash: float = 1000.0

    @property
    def has_credentials(self) -> bool:
        return bool(self.api_key and self.api_secret)

    def __repr__(self) -> str:
        state = "hinterlegt" if self.has_credentials else "leer"
        return f"Settings(pair={self.pair}, interval={self.interval}, zugangsdaten={state})"


def load_settings(path: Path = ENV_PATH) -> Settings:
    """Liest .env, Umgebungsvariablen haben Vorrang."""
    values = read_env_file(path)

    def pick(name: str, fallback: str) -> str:
        return os.environ.get(name, values.get(name, fallback))

    return Settings(
        api_key=pick("KRAKEN_API_KEY", ""),
        api_secret=pick("KRAKEN_API_SECRET", ""),
        pair=pick("MONEAI_PAIR", "XBTUSD"),
        interval=int(pick("MONEAI_INTERVAL", "60")),
        start_cash=float(pick("MONEAI_START_CASH", "1000")),
    )
