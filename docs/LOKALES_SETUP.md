# Lokales Setup: Demo-Wallet mit Ticket-Ausgabe

Alles in dieser Anleitung läuft auf deinem Rechner. Der Schlüssel bleibt in
einer lokalen Datei, die Demo-Wallet existiert nur bei dir, und es geht keine
Order an die Börse.

## 1. Schlüssel selbst anlegen

Den API-Schlüssel erzeugst du selbst bei Kraken unter Settings, API, Add key.
Ich lege ihn nicht für dich an und ich trage ihn auch nicht ein. Aktiviere
ausschliesslich lesende Rechte:

* Query Funds
* Query Open Orders and Trades
* Query Closed Orders and Trades
* Query Ledger Entries

Nicht aktivieren: Create and Modify Orders, Cancel/Close Orders, Withdraw
Funds, Margin Trading. Ein Schlüssel ohne Handelsrecht kann selbst dann keinen
Schaden anrichten, wenn Software fehlerhaft ist, dein Rechner kompromittiert
wird oder du später fremden Code einbindest. Das ist die einzige Sperre, die
nicht von Software abhängt.

## 2. Datei anlegen

```bash
cp .env.example .env
chmod 600 .env
```

Danach trägst du Key und Secret in .env ein. Die Datei steht in .gitignore und
gehört nirgendwo anders hin: nicht in ein Repository, nicht in einen Chat,
nicht in eine Cloud-Notiz.

## 3. Lauf starten

```bash
source .venv/bin/activate
python examples/run_paper.py --once --account
python examples/run_paper.py --strategy sma --poll-seconds 300
```

Der erste Aufruf macht einen einzelnen Durchgang und zeigt zusätzlich deine
tatsächlichen Bestände, damit du siehst, dass der Schlüssel funktioniert. Der
zweite läuft dauerhaft und prüft alle fünf Minuten, ob sich auf der letzten
abgeschlossenen Kerze etwas geändert hat. Beenden mit Strg+C. Wer es dauerhaft
laufen lassen will, nimmt tmux, screen oder einen launchd-Dienst - der Prozess
liest nur, er kann nichts auslösen.

## 4. Was du bekommst

Bei jeder Änderung erscheint ein Ticket mit Zeit, Paar, Richtung, Menge,
Referenzkurs und Anlass. Parallel schreibt die Demo-Wallet jede simulierte
Ausführung nach results/paper_journal.csv, mit Gebühr, Bargeld, Position und
Kontowert. Diese Datei ist der eigentliche Wert des Aufbaus: nach ein paar
Wochen siehst du schwarz auf weiss, wie oft die Strategie handelt, wie viel
davon Gebühren sind und wie tief der Drawdown wirklich wird.

## 5. Warum es keine automatische Spiegelung gibt

Ein Dienst, der die Demo-Wallet auf das echte Konto überträgt, wäre derselbe
automatische Handel wie vorher, nur mit einem Zwischenschritt. Der
Zwischenschritt, der wirklich zählt, ist der Mensch, der schaut und entscheidet
- und der bei einer Marktstörung, einem Datenfehler oder einem Bug in der
Strategie einfach nichts tut. Genau diese Pause fällt bei einer Spiegelung weg,
und sie fällt immer im schlechtesten Moment weg. Deshalb endet dieses Projekt
beim Ticket.

## 6. Der ehrliche Vergleich nach ein paar Wochen

Stelle drei Zahlen nebeneinander: Kontowert der Demo-Wallet, Kaufen-und-Halten
über denselben Zeitraum, und was du tatsächlich gemacht hättest. Wenn die
Demo-Wallet nach Gebühren nicht deutlich besser ist als einfach halten, hat die
Strategie keinen Vorteil - unabhängig davon, wie gut sich der Aufbau anfühlt.
Das früh zu erkennen ist kein Rückschlag, das ist der Ertrag dieser Arbeit.
