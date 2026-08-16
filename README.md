# MoneAI

Ein Research-Framework für systematische Handelsstrategien auf Kryptomärkten.

> **Wichtig:** MoneAI führt keine Orders aus. Das Projekt enthält keinen Code, der
> eine Börse mit Schreibrechten anspricht. Alle Ergebnisse sind Simulationen. Ob
> und was gehandelt wird, entscheidet ausschließlich ein Mensch.

## Idee

Die meisten Strategien, die in Videos und Foren gezeigt werden, überleben keinen
ehrlichen Test. Nicht weil die Idee dumm wäre, sondern weil Gebühren, Spread,
Slippage und Überanpassung an die Vergangenheit den Vorteil auffressen. MoneAI
ist gebaut, um Ideen so schnell und so unbarmherzig wie möglich zu widerlegen.
Was nach diesem Prozess übrig bleibt, ist es wert, weiter untersucht zu werden.

## Aufbau

```
moneai/
  data.py          OHLC-Daten über Krakens öffentliche API (read-only)
  metrics.py       CAGR, Sharpe, Sortino, Max Drawdown, Profit Factor
  backtest.py      Backtester mit Gebühren, Spread, Slippage, Finanzierung
  strategies.py    Beispielstrategien mit einheitlicher Schnittstelle
  walkforward.py   Walk-Forward-Validierung gegen Überanpassung
  config.py        lokale Einstellungen aus .env
  kraken_private.py  Kontostand lesen, ausschließlich lesende Endpunkte
  paper.py         Demo-Wallet mit Journal und Order-Tickets
  runner.py        lokaler Lauf gegen aktuelle Marktdaten
  review.py        Auswertung: Demo gegen Kaufen-und-Halten
examples/
  run_backtest.py  Backtest und Walk-Forward
  run_paper.py     Demo-Wallet live mitlaufen lassen
  review_paper.py  wöchentliche Auswertung des Journals
tests/             Sicherungen gegen Lookahead und vergessene Kosten
docs/
  ARBEITSWEISE.md  Prüfpfad, Abbruchkriterien, Journal
  LOKALES_SETUP.md Schlüssel, Demo-Wallet, Tickets
```

## Schnellstart

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
pytest -q

# 1. Idee historisch prüfen
python examples/run_backtest.py --strategy sma --walkforward

# 2. Demo-Wallet lokal mitlaufen lassen
cp .env.example .env && chmod 600 .env
python examples/run_paper.py --once --account

# 3. nach ein paar Wochen auswerten
python examples/review_paper.py
```

Die öffentliche API liefert nur rund 720 Kerzen. Für belastbare Tests lädt man
Krakens historische OHLCVT-Archive herunter und übergibt sie mit --csv.

## Annahmen des Backtests

Signale werden auf dem Schlusskurs einer Kerze berechnet und frühestens auf der
nächsten Kerze ausgeführt. Das verhindert den häufigsten Fehler überhaupt,
nämlich mit Information zu handeln, die zum Handelszeitpunkt noch nicht
existierte. Jeder Positionswechsel kostet Taker-Gebühr plus halben Spread plus
Slippage, Fremdkapital kostet zusätzlich Finanzierung pro Zeit. Diese Werte sind
bewusst pessimistisch voreingestellt.

## Wann eine Strategie ernst zu nehmen ist

Eine Strategie ist ein Kandidat, wenn sie nach Kosten positiv ist, wenn dieses
Ergebnis aus Zeiträumen stammt, die bei der Parameterwahl nicht sichtbar waren,
wenn sie auf einem breiten Parameter-Plateau statt auf einer einzelnen Spitze
steht, wenn genug Trades vorliegen um Zufall auszuschließen, und wenn der
maximale Drawdown eine Größe hat, die man real aushalten würde. Fällt auch nur
eines dieser Kriterien, ist das Ergebnis eine Zufallsbeobachtung. Der genaue
Prüfpfad steht in [docs/ARBEITSWEISE.md](docs/ARBEITSWEISE.md).

## Zugangsdaten

Den API-Schlüssel legst du selbst an, mit ausschließlich lesenden Rechten. Er
gehört in die lokale Datei .env, die von git ignoriert wird. Der Client in
moneai/kraken_private.py kennt nur abfragende Endpunkte. Details in
[docs/LOKALES_SETUP.md](docs/LOKALES_SETUP.md).

## Was hier bewusst fehlt

Orderausführung, Autotrading, das Spiegeln der Demo-Wallet auf ein echtes Konto.
Der Ablauf endet bei einem Order-Vorschlag auf deinem Bildschirm. Die
Entscheidung trifft ein Mensch.

## Lizenz

Apache-2.0
