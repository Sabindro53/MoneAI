# Arbeitsweise

Diese Datei ist die Arbeitsanweisung für das Projekt. Sie legt fest, in welcher
Reihenfolge geprüft wird, wann eine Idee verworfen wird und was hier nicht
passiert. Sie existiert, damit Ergebnisse nicht davon abhängen, wie gut die
Laune am Testtag war.

## Was das Projekt tut und was nicht

MoneAI misst, wie sich eine Regel in der Vergangenheit nach Kosten geschlagen
hätte. MoneAI sendet keine Orders, hält keine Schlüssel mit Handelsrechten und
verwaltet kein Kapital. Jede Entscheidung über echtes Geld trifft ein Mensch,
bewusst, einzeln und außerhalb dieses Repositories.

## Der Prüfpfad

**Erstens, Hypothese vor Code.** Notiere in einem Satz, warum der Effekt
existieren sollte: wer verliert hier Geld an wen, und warum hört der oder die
nicht damit auf? Ideen ohne diese Antwort brauchen keinen Test. Die meisten
Video-Strategien scheitern schon hier.

**Zweitens, Daten prüfen.** Zeitzone, Lücken, Ausreißer, Handelsstopps.
moneai.data bricht bei kaputten Daten absichtlich ab, statt still
weiterzurechnen. Eine Strategie, die nur auf einer einzigen Datenquelle
funktioniert, funktioniert nicht.

**Drittens, erste Messung mit pessimistischen Kosten.** Voreingestellt sind
Taker-Gebühr, halber Spread und Slippage. Wenn ein Ergebnis nur mit
Maker-Gebühren überlebt, muss die Strategie beweisen, dass sie tatsächlich
passiv ausgeführt werden kann.

**Viertens, Walk-Forward.** Parameter werden nur auf dem Trainingsfenster
gewählt, bewertet wird ausschließlich auf den Testfenstern. Nur diese Zahl wird
berichtet. Wandern die gewählten Parameter von Fenster zu Fenster stark, war es
Rauschen.

**Fünftens, Urteil und Journal.** Jeder Test wird eingetragen, auch und gerade
der gescheiterte. Wer nur Treffer notiert, baut sich seine eigene Statistik.

## Abbruchkriterien

Eine Idee wird verworfen, wenn das Out-of-Sample-Ergebnis nach Kosten negativ
ist, wenn weniger als etwa dreissig Trades vorliegen, wenn das Ergebnis an einem
einzelnen Parameterwert hängt statt auf einem Plateau zu stehen, wenn der
maximale Drawdown größer ist als das, was man ruhig aussitzen würde, oder wenn
sie Kaufen-und-Halten nicht risikobereinigt schlägt. Verworfen heißt verworfen,
nicht "noch einmal mit anderen Parametern".

## Zum Thema enge Stops

Ein Stop bei einem Prozent klingt nach Sicherheit. Bei stundengenauen
Kryptodaten liegt die normale Schwankung einer Kerze oft in derselben
Größenordnung. Der Stop wird dann nicht von Fehlentscheidungen ausgelöst,
sondern von Rauschen, und jedes Auslösen kostet Gebühr und Spread. Der Schalter
--stop-loss existiert, damit dieser Effekt sichtbar wird, nicht als Empfehlung.
Wer einen Stop setzt, leitet ihn aus der gemessenen Schwankungsbreite ab, nicht
aus einer runden Zahl.

## Zum Thema Hebel

Hebel vervielfacht das Ergebnis in beide Richtungen und verschiebt die
Liquidationsschwelle in Reichweite normaler Bewegungen. Im Backtester kostet
Fremdkapital deshalb Finanzierung pro Zeit. Eine Strategie, die ohne Hebel kein
Geld verdient, verdient auch mit Hebel keines - sie verliert nur schneller.

## Journal-Eintrag

Datum, Hypothese in einem Satz, Datenquelle und Zeitraum, Strategie und
Parameterraster, Kostenannahmen, Out-of-Sample-Kennzahlen, Urteil, und ein Satz
dazu, was du beim nächsten Mal anders machst. Sechs Zeilen reichen.

## Falls es irgendwann um echtes Geld geht

Das ist deine Entscheidung, nicht die des Repositories, und nichts hier ist eine
Anlageempfehlung. Sinnvoll ist in dem Fall: erst über Monate manuell und in
kleinstem Umfang mitlaufen lassen, eine feste Obergrenze für den Gesamtverlust
vorher schriftlich festlegen, und bei Regelbruch pausieren statt nachzulegen.
Wenn der Wunsch, Verluste zurückzuholen, die Entscheidung trägt, ist Pause die
einzige richtige Antwort. Bei größeren Beträgen gehört eine unabhängige,
qualifizierte Beratung dazu.
