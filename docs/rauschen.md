# Rauschboden

> Eigene Einschätzung nach festen Regeln, nicht amtlich. Fehler im Verfahren und in der Auswertung können nicht
> ausgeschlossen werden (ohne Gewähr).

Die Geräte zeichnen auch sehr langsame Messwerte auf, die kaum von Fahrzeugen stammen dürften: Fußgänger, Tiere, Echos,
Störungen. Was es ist, sagen die Daten nicht. Statt einer festen Mindestgeschwindigkeit schätzt `rauschen.py` für jede
Datei, welcher Teil der Messwerte **nicht vom Verkehr abhängt**, und rechnet ihn aus allen Kennzahlen heraus. Die CSV-Dateien
bleiben vollständig.

## Warum keine Mindestgeschwindigkeit

Früher nahmen wir Werte unter 5 km/h heraus (`--min-kmh`). Das war eine Annahme („kein Fahrzeug im Sinne der StVO bewegt sich
regelmäßig so langsam“). Die Daten tragen mehr: Bei vielen Messstellen fällt die Zahl der Fahrten nachts auf 3 bis 20 % der
Tagesrate, bei den sehr langsamen Werten aber nicht. In der Föhrenstraße liegt das Verhältnis Nacht zu Tag bei 0,5 bis 0,7
bis etwa 8 km/h und fällt erst bei 9 bis 12 km/h auf das Niveau des Verkehrs (etwa 0,03 bis 0,1). Nachts zwischen 0 und 5 Uhr
bestehen dort 45 % der aufgezeichneten „Fahrzeuge“ aus Werten unter 10 km/h. Die Grenze liegt je Messstelle verschieden, und
bei Geräten, die erst ab 9 oder 10 km/h erfassen, ist nur der Auslauf sichtbar.

## Modell

Je Zelle aus **Tagtyp** (Werktag, Samstag, Sonn- und Feiertag in NRW) und **Stunde** gilt für die Fahrten je Stunde mit der
Geschwindigkeit v

    y(v, Zelle) = a(v) + b(v) · Verkehr(Zelle)

- `Verkehr(Zelle)` sind die Fahrten je Stunde ab der Verkehrsschwelle (70 % des Tempolimits, mindestens 15 km/h).
- `a(v)` ist die **verkehrsunabhängige** Rate, der Rauschboden. `b(v)` ist der Teil, der mit dem Verkehr geht. Zu `b(v)`
  gehören auch die echten langsamen Fahrer (Radfahrer, Abbieger …): Sie nehmen nachts im selben Maß ab wie der Verkehr.
- Es zählt nur der Zeitverlauf, keine Annahme über die Form der Verteilung. Die Schätzung nutzt gewichtete kleinste Quadrate
  mit Poisson-Gewichten und einem Ausgleich für Überstreuung; `a` und `b` sind nicht negativ.
- `a(v)` zählt nur, wenn es mindestens **3 Standardfehler** über 0 liegt (`SIGMA`).
- Geschätzt wird nur unterhalb der Verkehrsschwelle und nur aus Zeiten mit nutzbarer Uhr und aus Stunden, die ein Abschnitt
  vollständig abdeckt. Zellen mit weniger als 3 Tagen bleiben draußen.

## Wann der Abzug gilt

Eine Datei braucht mindestens 3000 Fahrzeuge mit nutzbarer Zeit und ein bekanntes Tempolimit. Der Rauschboden gilt als **belegt**
und wird abgezogen, wenn

1. a(v) überhaupt nachweisbar ist,
2. 95 % der Rauschmasse unter **15 km/h** liegen (reicht das „Rauschen“ weiter, ist es nicht von langsamem Verkehr zu trennen),
3. der Anteil in den Hälften der Messtage (gerade und ungerade Tage) **stabil** ist: Unterschied höchstens 1,5 Prozentpunkte
   oder höchstens die Hälfte des größeren Werts.

Sonst steht in der YAML unter `rauschen.grund`, warum nicht, und es wird **nichts** herausgerechnet. Bei den jetzigen Dateien:
41 belegt, 34 ohne nachweisbaren Rauschboden, 17 nicht stabil, 7 mit Obergrenze über 15 km/h, 10 zu klein.

## Abzug

Jedes Fahrzeug zählt anteilig als Rauschen: Die erwartete Zahl je Zelle und km/h ist `a(v) · Stunden`, höchstens die dort
gemessene Zahl (nachts liegt die Rate des Rauschens oft unter dem Mittel). Entfernt werden ganze Fahrzeuge, gleichmäßig
über die Zeit verteilt, Rundungsreste laufen in die nächste Zelle. So bleibt jede weitere Auswertung (V85, Einhaltung,
Gefährdung, Lärm, Nächte, Histogramme) unverändert aufgebaut. Für Fahrten ohne nutzbare Uhr (Gesamtwerte) gilt derselbe Anteil
je Geschwindigkeit.

In der YAML steht unter `rauschen`: `belegt`, `abgezogen_fahrzeuge`, `anteil_prozent` (Schätzung des Modells),
`abgezogen_anteil_prozent` (tatsächlich entfernt), `mittel_kmh`, `obergrenze_kmh` (95 %), `stabil`, die Anteile der Hälften
und `spektrum` (Fahrten je 1000 Stunden: `rausch` und `alle`). `fahrzeuge_in_datei` ist die Zahl vor dem Abzug,
`anzahl_fahrzeuge` danach. Die Detailseiten zeigen das Spektrum.

## Grenzen

- Das Modell nimmt eine **konstante** Rate an. Nachts liegt sie oft niedriger. Der tatsächlich entfernte Anteil ist deshalb
  etwas kleiner als der geschätzte. Eine Abhängigkeit vom Wetter (Regen, Wind, Temperatur) ist nicht modelliert und könnte
  die Tag-zu-Tag-Schwankung erklären, die bei 17 Dateien die Stabilitätsprüfung auslöst.
- Eine Ground Truth gibt es nicht. Überprüft ist nur, dass der Anteil nicht von der gewählten Verkehrsschwelle abhängt (Median
  der Änderung bei 50 % und 90 % statt 70 % des Limits: 0,03 Prozentpunkte) und dass er sich in Hälften der Messtage
  bei den meisten Dateien wiederholt.
- Der Abzug ist ein statistischer Anteil. Er sagt nicht, welches einzelne Fahrzeug Rauschen ist.
- Bei verkehrsberuhigten Bereichen (Tempolimit 10 km/h) und bei Geräten, die erst ab 9 oder 10 km/h erfassen, ist oft nichts
  nachweisbar. Dort bleibt alles in der Auswertung.
- Wie das Rauschen von echten langsamen Fahrern (Radfahrer, Abbieger, langsame Autos) und von der Hauptmenge zu trennen ist,
  ist ein eigener Schritt (Gruppenerkennung) und noch nicht Teil der Kennzahlen.

## Reproduktion

```sh
python3 -I dsd2csv.py .          # rauschen.py wird eingebunden; Ergebnis steht unter "rauschen" in jeder YAML
python3 -m unittest -v test_rauschen
```

Alle Schwellen stehen oben in `rauschen.py` (`SIGMA`, `MIN_TAGE`, `MIN_FAHRZEUGE`, `OBERGRENZE_KMH`, `INSTABIL_PP`, `INSTABIL_REL`).
