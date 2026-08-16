# MoneAI

Ein Research-Framework für systematische Handelsstrategien auf Kryptomärkten.

> **Wichtig:** MoneAI führt keine Orders aus. Das Projekt enthält keinen Code, der
> eine Börse mit Schreibrechten anspricht, und benötigt keinen API-Key. Alle
> Ergebnisse sind Simulationen auf historischen Daten. Ob und was gehandelt wird,
> entscheidet ausschließlich ein Mensch.

## Idee

Die meisten Strategien, die in Videos und Foren gezeigt werden, überleben keinen
ehrlichen Test. Nicht weil die Idee dumm wäre, sondern weil Gebühren, Spread,
Slippage und Überanpassung an die Vergangenheit den Vorteil auffressen. MoneAI
ist gebaut, um Ideen so schnell und so unbarmherzig wie möglich zu widerlegen.
Was nach diesem Prozess übrig bleibt, ist es wert, weiter untersucht zu werden.

## Aufbau

```
moneai/
  data.py         OHLC-Daten über Krakens öffentliche API (read-only, kein Key)
  metrics.py      Kennzahlen: CAGR, Sharpe, Sortino, Max Drawdown, Profit Factor
  backtest.py     Vektorisierter Backtester mit Gebühren, Spread und Slippage
  strategies.py   Beispielstrategien mit einheitlicher Schnittstelle
  walkforward.py  Walk-Forward-Validierung gegen Überanpassung
examples/
  run_backtest.py Kommandozeilen-Einstieg
tests/
  test_backtest.py Sicherungen gegen Lookahead und vergessene Kosten
docs/
  ARBEITSWEISE.md  Prüfpfad, Abbruchkriterien, Journal
```

## Schnellstart

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

pytest -q
python examples/run_backtest.py --pair XBTUSD --interval 60 --strategy sma
python examples/run_backtest.py --csv XBTUSD_60.csv --strategy sma --walkforward
```

Die öffentliche API liefert nur rund 720 Kerzen. Für belastbare Tests lädt man
Krakens historische OHLCVT-Archive herunter und übergibt sie mit --csv.

## Annahmen des Backtests

Signale werden auf dem Schlusskurs einer Kerze berechnet und frühestens auf der
nächsten Kerze ausgeführt. Das verhindert den häufigsten Fehler überhaupt, nämlich
mit Information zu handeln, die zum Handelszeitpunkt noch nicht existierte. Jeder
Positionswechsel kostet Taker-Gebühr plus einen halben Spread plus einen
Slippage-Aufschlag, Fremdkapital kostet zusätzlich Finanzierung pro Zeit. Diese
Werte sind bewusst pessimistisch voreingestellt.

## Wann eine Strategie ernst zu nehmen ist

Eine Strategie ist ein Kandidat, wenn sie nach Kosten positiv ist, wenn dieses
Ergebnis aus Zeiträumen stammt, die bei der Parameterwahl nicht sichtbar waren,
wenn sie auf einem breiten Parameter-Plateau statt auf einer einzelnen Spitze
steht, wenn genug Trades vorliegen um Zufall auszuschließen, und wenn der maximale
Drawdown eine Größe hat, die man real aushalten würde. Fällt auch nur eines dieser
Kriterien, ist das Ergebnis eine Zufallsbeobachtung. Der genaue Prüfpfad steht in
[docs/ARBEITSWEISE.md](docs/ARBEITSWEISE.md).

## Was hier bewusst fehlt

Orderausführung, Hebel-Logik im Live-Betrieb, API-Keys mit Handelsrechten,
Autotrading. Diese Bausteine gehören nicht in ein Repository, dessen Strategien
noch nicht über Jahre out-of-sample bestanden haben.

## Lizenz

Apache-2.0
