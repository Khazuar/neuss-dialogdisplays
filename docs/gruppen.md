# Zeitscheiben, Zellen und die Auswahl auf den Detailseiten

> Eigene Einschätzung nach festen Regeln, nicht amtlich. Fehler im Verfahren und in der Auswertung können nicht
> ausgeschlossen werden (ohne Gewähr).

`gruppen.py` legt die Zeitscheiben fest und baut die Zellen, aus denen die Detailseiten jede Auswahl nach Tageszeit und Tagen
rechnen. Der Name stammt von den früheren Formgruppen (unten).

## Frühere Formgruppen (entfernt im Oktober 2026)

Bis Oktober 2026 zerlegte `gruppen.py` die Verteilung jeder Datei in eine Mischung von Lognormal-Kurven, zusammengefasst zu Gruppen
nach überlappenden Kernbereichen, mit der Zahl der Kurven aus der Vorhersage der jeweils anderen Hälfte der Messtage. Diese
„Formgruppen“ beschrieben nur die Form der Verteilung; dass sie etwas Eigenes sind, ließ sich so nicht begründen. Sie standen
zuletzt nur noch in der YAML (Block `gruppen`) und sind jetzt ganz entfernt, auch weil die Anpassung den größten Teil der Rechenzeit
je Datei brauchte. Verfahren, Schwellen und Tests stehen im Stand vor dem Entfernen (Commit `80addbb`, `docs/gruppen.md` und
`gruppen.py`).

Was sie gezeigt haben: Die meisten Verteilungen sind nicht eine Glocke (98 von 109 Dateien zerlegt, davon 73 in 2 Gruppen).
Teilte man den Zeitraum in eine erste und eine zweite Hälfte statt in gerade und ungerade Tage, blieb nur bei 53 der 98 Dateien
dieselbe Zerlegung bestehen. Ein großer Teil davon war ein Wechsel im Lauf der Messung; das klären heute die **Abschnitte**
([abschnitte.md](abschnitte.md)). Ob hinter einer Gruppe ein eigenes Verhalten steckt, prüfen die **Verhaltensgruppen**
([verhalten.md](verhalten.md)) an der Vorhersage ungesehener Wochen und einem Placebo-Durchgang.

## Zeitscheiben und Tage

Zeiten sind Ortszeit (siehe [dsd-format.md](dsd-format.md)).

| Zeitscheibe | Stunden | Begründung |
|---|---|---|
| Nacht | 22–6 Uhr | Verkehr unter 2 % je Stunde, das Tempo der schnellen Fahrzeuge liegt +4 bis +10 % über dem Tagesniveau |
| Vormittag | 6–12 Uhr | |
| Nachmittag | 12–19 Uhr | Verkehr zwischen 5 und 7,5 % je Stunde, Tempo flach |
| Abend | 19–22 Uhr | Tempo +2 bis +3 % |
| Schulweg | 7–8 Uhr | überlappt mit dem Vormittag; in den Tabellen Montag bis Freitag |

Die Grenzen folgen dem mittleren Tagesgang über 62 Dateien (Werktag): Das Tempo der schnellen Fahrzeuge (ab 0,6 × Tempolimit)
ist von 7 bis 18 Uhr flach und steigt erst ab 19 Uhr, nachts um bis zu 10 %. Die frühere Grenze „Nachts ab 18 Uhr“ passte
dazu nicht.

Tage: Werktage (Montag bis Freitag), Samstage, Sonn- und Feiertage (gesetzliche Feiertage in Nordrhein-Westfalen, aus dem
Osterdatum berechnet) sowie jeder einzelne Wochentag und „Feiertage an Werktagen und Samstagen“. Schulferien sind nicht
herausgerechnet.

## Auswahl auf den Detailseiten

Jede Detailseite trägt die Zellen der Messung als Datentabelle (JSON in einem `script`-Element). Eine Zelle ist ein
Histogramm (Anzahl Fahrzeuge je km/h) für einen Tagschlüssel (0 bis 6 Montag bis Sonntag, 7 Feiertag) und eine Stunde. Das
kleine Skript `site/filter.js` liest nur diese Tabelle der eigenen Seite und rechnet daraus Kennzahlen (Fahrzeuge, je Stunde,
Mittel, V85/V95/V99, Einhaltung, qualifizierte Einhaltung) und das Histogramm. Es lädt nichts nach und speichert nichts. Ohne
JavaScript bleibt der Abschnitt verborgen, und die Seite zeigt die Tabelle der Kennzahlen je Zeitraum und das Histogramm aller
Fahrzeuge, bei vorhandenem Rauschboden auch dessen Bild (alles entfällt mit JavaScript, weil die Auswahl es ersetzt).

**Gesamtkurve und Auswahl:** Das Histogramm zeigt immer alle Fahrzeuge der ganzen Messung grau (alle Abschnitte, Tageszeiten, Tage und
Wetter) und die Auswahl farbig, in derselben Höhenskala (Anteil an allen Fahrzeugen). So sieht man, wie klein oder groß eine Auswahl ist: Ein
Abschnitt, eine Nacht oder trockene Stunden erscheinen entsprechend niedriger. Mit dem Kästchen „Auswahl isoliert darstellen“ (standardmäßig aus)
bezieht sich die Höhe auf die Auswahl selbst, ohne Gesamtkurve; das ist besser lesbar, wenn die Auswahl sehr klein ist. Die Kennzahlen darüber
gelten immer für die Auswahl.

Gruppen in der Auswahl sind die **Verhaltensgruppen** des gewählten Abschnitts ([verhalten.md](verhalten.md), „Auf den Seiten“, nur im
Labor-Modus) und, wo ein Rauschboden abgezogen wurde, „Rauschboden (herausgerechnet)“: Grau bleiben alle aufgezeichneten Fahrten der ganzen
Messung, farbig ist der herausgerechnete Rauschboden. Die Auswahl „Nur trockene Stunden“ nimmt eigene Zellen nur aus Stunden ohne
Regen ([totzeit.md](totzeit.md)).

Die Zellen enthalten nur vollständig aufgezeichnete Stunden mit nutzbarer Zeit; die Zahl der Fahrzeuge einer Auswahl kann
deshalb geringfügig unter der Zahl in den Tabellen liegen.

Die Zellen liegen als `<Datei>.zellen.json` neben der YAML (`v`, `limit`, `tage`, `z`, `r`, dazu `trocken`, `abschnitte` und `verhalten`
wo vorhanden; Format in `gruppen.py`).

## Zwischenspeicher

`dsd2csv.py --cache ORDNER` speichert Ergebnisse je Datei (`zwischenspeicher.py`). Die Ebene „datei“ (ohne numpy „datei-ohne-numpy“)
gilt für eine DSD-Datei samt Standort und Parametern und hängt vom Inhalt der Datei und vom Hash der Skripte und Belege ab, aus denen
sie entsteht (`CODE_DATEIEN` in `dsd2csv.py`). Die Ebenen „verhalten“ und „vorlagen“ der Verhaltensgruppen beschreibt
[verhalten.md](verhalten.md). Nach einem vollständigen Lauf werden nicht benutzte Einträge gelöscht. In GitHub Actions bleibt der
Ordner zwischen den Läufen erhalten (`actions/cache`).

## Reproduktion

```sh
python3 -I dsd2csv.py . -o ausgabe --keine-csv --cache .zwischenspeicher --jobs 4
python3 -I seiten_bauen.py --auswertung ausgabe/auswertung.json --ziel ausgabe
```

Tests: `test_gruppen.py` (Zellen, Zwischenspeicher), `test_filter.py` (`site/filter.js` mit Node, wird ohne Node
übersprungen), `test_seiten.py`.
