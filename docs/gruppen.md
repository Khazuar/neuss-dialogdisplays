# Gruppen in der Geschwindigkeitsverteilung

> Eigene Einschätzung nach festen Regeln, nicht amtlich. Fehler im Verfahren und in der Auswertung können nicht
> ausgeschlossen werden (ohne Gewähr).

Viele Verteilungen sind nicht eine einzelne Glocke, sondern mischen mehrere Gruppen: eine langsame Nebengruppe (je nach Ort
vielleicht Radfahrer, abbiegende oder anfahrende Fahrzeuge), die Hauptmenge, manchmal weitere. `gruppen.py` zerlegt die
Verteilung jeder Datei in solche Gruppen, **soweit die Daten das belegen**, und die Detailseiten erlauben, Kennzahlen und
Histogramm für jede Gruppe sowie für Tageszeit und Wochentag getrennt anzusehen.

**Was eine Gruppe ist und was nicht.** Eine Gruppe ist ein statistischer Anteil der Verteilung: eine Lognormal-Glocke mit
Anteil, häufigstem Tempo (Modus) und Streuung. Sie ist keine Fahrzeugart. Was sich dahinter verbirgt, lässt sich aus
Geschwindigkeiten allein nicht entscheiden. Plausible Deutungen stehen als Hypothesen in der Diskussion, nicht in den Daten.

## Verfahren

1. **Daten.** Fahrzeuge mit nutzbarer Zeit in vollständig aufgezeichneten Stunden, nach Abzug des Rauschbodens
   ([rauschen.md](rauschen.md)). Was der Abzug übrig lässt, liegt oft noch im Bereich des Rauschbodens; deshalb werden
   Fahrzeuge bis zur 95-%-Grenze des Rauschbodens plus 1 km/h nicht zerlegt. Wo kein Rauschboden belegt ist, bleibt ein Haufen
   am unteren Rand (Sensorgrenze) von der Anpassung ausgenommen (`abschneiden`). Beides erscheint in der Auswahl als
   „Unter X km/h (nicht zerlegt)“.
2. **Mischung.** Eine Mischung von K Lognormal-Verteilungen wird mit dem EM-Verfahren angepasst (mehrere feste Startwerte,
   die beste gilt; das Ergebnis ist reproduzierbar).
3. **Zahl der Gruppen K, je Datei.** K wird für jede Datei einzeln bestimmt, von 2 bis höchstens 8 (die Suche endet bei den bisherigen Daten nach spätestens 6). Eine Gruppe mehr gilt nur,
   wenn alles zutrifft:
   - **Kein Überanpassen:** Die Anpassung auf den geraden Messtagen beschreibt die ungeraden Tage um mindestens 0,002 nats
     je Fahrzeug besser als mit einer Gruppe weniger (und umgekehrt). Sonst endet die Suche.
   - **Stabil:** Die Gruppen aus den beiden Hälften der Messtage (gerade und ungerade Tage) liegen in Lage (Modus innerhalb von
     7 % im Logarithmus) und Anteil (innerhalb 6 Prozentpunkten) beieinander.
   - **Nicht winzig:** Keine Gruppe unter 3 % in einer Hälfte.
   - **Kein Randartefakt:** Die langsamste Gruppe hat ihr häufigstes Tempo mehr als 1 km/h über der unteren Grenze der Anpassung.
     Sonst beschreibt sie nur den abgeschnittenen Rand der Daten und keine echte Gruppe.
   - **Getrennt:** Der Ashman-Abstand D = √2 · |μᵢ − μⱼ| / √(σᵢ² + σⱼ²) zwischen allen Gruppen ist mindestens 1. Gibt es dafür
     keine Lösung, genügt ein getrenntes Paar „langsamste Gruppe gegen die nächste“, und die Seite vermerkt, dass die oberen
     Gruppen überlappen.
   Die Suche endet, wenn der Gewinn unter die Schwelle fällt oder zwei Werte von K in Folge nicht stabil oder zu klein sind.
   Gewählt wird das größte K, das alle Bedingungen erfüllt. Gibt es keins, bleibt es bei einer Gruppe (**keine Zerlegung**).
   Bei weniger als 5000 Fahrzeugen wird nicht zerlegt.
4. **Feste Gruppen für alle Stunden und Tage.** Die Zerlegung gilt für alle Tageszeiten und Tage gleich. Der Anteil einer
   Gruppe an Fahrzeugen mit einer bestimmten Geschwindigkeit hängt dann nur von dieser Geschwindigkeit ab. Ein Fahrzeug
   zählt anteilig zu den Gruppen. Das macht jede Auswahl (Tageszeit, Wochentag, Gruppe) zur einfachen Summe über Zellen.

**Warum nicht stündlich anpassen und die Gruppen verfolgen?** Das wurde ausprobiert: je Stunde und Tagtyp eine eigene Anpassung,
die Gruppen über den Tag verfolgt (Kontinuität, Impuls, zyklischer Schluss). Gemessen an 63 zerlegbaren Dateien mit
Training auf geraden und Test auf ungeraden Tagen brachte das gegenüber der festen Zerlegung wenig: 95 % des gesamten
Gewinns kommen schon von der festen Zerlegung, die zusätzliche Freiheit je Stunde bringt im Median 0,009 nats je Fahrzeug,
bei 9 von 63 Dateien ist sie auf ungesehenen Tagen schlechter (Überanpassung). Die Kennzahlen nach Abzug der langsamen
Gruppen weichen zwischen fester Zerlegung und stündlicher Anpassung im Median um 0,01 bis 0,04 km/h im Mittel ab. Das
Verfahren ist deutlich langsamer (rund 15 Sekunden je Datei statt 2 bis 5) und liefert keine besser belegte Identität der Gruppen.

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
JavaScript bleibt der Abschnitt verborgen, und die Seite zeigt die übrigen Tabellen.

Gruppen in der Auswahl: „Alle Fahrzeuge (ohne Rauschboden)“, „Rauschboden“ (das, was herausgerechnet wurde, soweit belegt),
„Gruppe 1“ bis „Gruppe K“ (nach Modus geordnet, 1 ist die langsamste), „Hauptmenge“ (ohne die langsamen Gruppen) und „Unter X
km/h“ (der nicht zerlegte Rand).

Die Zellen enthalten nur vollständig aufgezeichnete Stunden mit nutzbarer Zeit; die Zahl der Fahrzeuge einer Auswahl kann
deshalb geringfügig unter der Zahl in den Tabellen liegen.

## Langsame Gruppen

Eine Gruppe gilt als langsam, wenn ihr Modus höchstens 0,6 × Tempolimit beträgt, nicht alle Gruppen langsam sind und die
langsamen zusammen höchstens die Hälfte der Fahrzeuge ausmachen. Die „Hauptmenge ohne die langsamen Gruppen“ in der YAML und
auf den Seiten ist eine Ergänzung der Kennzahlen, kein Ersatz: Sie zeigt, wie die Quote aussähe, wenn die langsamen Gruppen
nicht in die Rechnung eingingen. Warum die Gruppe langsam ist, ist offen.

## Was in der YAML steht

Block `gruppen` je Messung: `geprueft`, `anzahl` (K), `obere_gruppen_ueberlappen`, `angepasst_ab_kmh`, `fahrzeuge`,
`fahrzeuge_unter_grenze`, `grund` (bei K = 1), `auswahl` (je geprüftem K: `stabil`, `klein`, `d_unten`, `d_alle`, `cv_gewinn`),
`gruppen` (Nummer, Anteil, Modus, Streuung im Logarithmus, Mittel, V85, Einhaltung, qualifizierte Einhaltung, `langsam`) und
`hauptmenge_ohne_langsame`. Die Zellen liegen als `<Datei>.zellen.json` neben der YAML (Format siehe `gruppen.py`,
`analysiere`).

## Grenzen

- Eine Glocke ist keine Fahrzeugart. Zusammenhänge mit Tageszeit, Wochentag oder Wetter können Hinweise geben, beweisen aber
  keine Zuordnung. Wetterdaten sind nicht eingebunden.
- Bei überlappenden Gruppen ist die Trennung unsicher, auch wenn die Zerlegung stabil ist. Die Schwellen (0,002 nats, 7 %,
  6 Prozentpunkte, 3 %, D ≥ 1) sind Festlegungen, kein Befund. Bei 50 der 109 Dateien gibt es keine Zerlegung (10 sind zu klein, bei 40 ist keine belegt); bei den übrigen 59 sind es 2 Gruppen (48 Dateien), 3 Gruppen (10) oder 4 Gruppen (1).
- Die Lognormal-Form ist eine Annahme. Verhalten wie ein Spitzer genau am Tempolimit passt nicht gut dazu und wird als eigene
  schmale Gruppe beschrieben.
- Die Anpassung ist deterministisch, aber nicht eindeutig: Andere Startwerte können bei knappen Fällen eine andere Zerlegung
  finden.

## Zwischenspeicher

`dsd2csv.py --cache ORDNER` speichert Ergebnisse je Datei (`zwischenspeicher.py`). Die Ebene „datei“ gilt für eine DSD-Datei
samt Standort und Parametern und hängt vom Inhalt der Datei und vom Hash von `dsd2csv.py`, `rauschen.py` und `gruppen.py` ab.
Die Ebene „gruppen“ (die aufwendige Zerlegung) hängt nur von den Zählwerten und `gruppen.py` ab; ändert sich nur die
Darstellung oder ein anderes Skript, wird sie wiederverwendet. Nach einem vollständigen Lauf werden nicht benutzte Einträge
gelöscht. In GitHub Actions bleibt der Ordner zwischen den Läufen erhalten (`actions/cache`).

## Reproduktion

```sh
python3 -I dsd2csv.py . -o ausgabe --keine-csv --cache .zwischenspeicher --jobs 4
python3 -I seiten_bauen.py --auswertung ausgabe/auswertung.json --ziel ausgabe
```

Tests: `test_gruppen.py` (Zerlegung, Zellen, Zwischenspeicher), `test_filter.py` (`site/filter.js` mit Node, wird ohne Node
übersprungen), `test_seiten.py`.
