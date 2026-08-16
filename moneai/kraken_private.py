"""Lesender Zugriff auf das eigene Kraken-Konto.

Dieser Client kennt nur abfragende Endpunkte. ALLOWED ist abschliessend, alles
andere wirft einen Fehler, bevor eine Anfrage den Rechner verlässt. Es gibt in
diesem Projekt keinen Codepfad, der eine Order erzeugt, verändert oder storniert.

Die zweite und wichtigere Sperre liegt nicht hier, sondern bei Kraken: der
Schlüssel selbst darf kein Handelsrecht besitzen. Software lässt sich ändern,
Rechte am Schlüssel nicht.
"""
from __future__ import annotations

import base64
import hashlib
import hmac
import time
import urllib.parse
from typing import Dict, Optional

import requests

API_URL = "https://api.kraken.com"

ALLOWED = frozenset({
    "Balance",
    "TradeBalance",
    "OpenOrders",
    "ClosedOrders",
    "OpenPositions",
    "Ledgers",
    "TradesHistory",
})

REFUSAL = ("Dieser Client ist absichtlich nur lesend. Orders werden von Hand in "
           "der Kraken-Oberfläche ausgelöst, von einem Menschen.")


class ReadOnlyKrakenClient:
    """Dünne Hülle um Krakens private, aber rein abfragende Endpunkte."""

    def __init__(self, api_key: str, api_secret: str, timeout: int = 20) -> None:
        if not api_key or not api_secret:
            raise ValueError("Keine Zugangsdaten gefunden. Siehe .env.example")
        self._key = api_key
        self._secret = api_secret
        self.timeout = timeout

    def _signature(self, path: str, payload: Dict[str, str]) -> str:
        body = urllib.parse.urlencode(payload)
        digest = hashlib.sha256((payload["nonce"] + body).encode()).digest()
        message = path.encode() + digest
        signed = hmac.new(base64.b64decode(self._secret), message, hashlib.sha512)
        return base64.b64encode(signed.digest()).decode()

    def query(self, endpoint: str, payload: Optional[Dict[str, str]] = None) -> dict:
        if endpoint not in ALLOWED:
            raise PermissionError(endpoint + " ist hier nicht vorgesehen. " + REFUSAL)
        path = "/0/private/" + endpoint
        data = dict(payload or {})
        data["nonce"] = str(int(time.time() * 1000))
        headers = {"API-Key": self._key, "API-Sign": self._signature(path, data)}
        response = requests.post(API_URL + path, data=data, headers=headers, timeout=self.timeout)
        response.raise_for_status()
        parsed = response.json()
        if parsed.get("error"):
            raise RuntimeError("Kraken meldet: " + str(parsed["error"]))
        return parsed["result"]

    def balances(self) -> Dict[str, float]:
        raw = self.query("Balance")
        return {asset: float(amount) for asset, amount in raw.items() if float(amount) != 0.0}

    def equity(self, quote: str = "ZUSD") -> float:
        """Gesamtguthaben in der Bezugswährung, wie Kraken es ausweist."""
        return float(self.query("TradeBalance", {"asset": quote}).get("eb", 0.0))

    def open_orders(self) -> dict:
        return self.query("OpenOrders").get("open", {})

    def summary(self, quote: str = "ZUSD") -> str:
        lines = ["Konto (nur gelesen)"]
        for asset, amount in sorted(self.balances().items()):
            lines.append(f"  {asset:<8} {amount:>18.8f}")
        lines.append(f"  Gesamt in {quote}: {self.equity(quote):.2f}")
        offene = self.open_orders()
        lines.append(f"  Offene Orders: {len(offene)}")
        return chr(10).join(lines)


def place_order(*args, **kwargs):
    """Existiert nur, um beim Namen zu scheitern statt zu handeln."""
    raise PermissionError(REFUSAL)
