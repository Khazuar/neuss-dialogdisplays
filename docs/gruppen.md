# Gruppen in der Geschwindigkeitsverteilung

> Eigene Einschätzung nach festen Regeln, nicht amtlich. Fehler im Verfahren und in der Auswertung können nicht
> ausgeschlossen werden (ohne Gewähr).

Viele Verteilungen sind nicht eine einzelne Glocke, sondern mischen mehrere Gruppen (je nach Ort vielleicht Radfahrer,
abbiegende oder anfahrende Fahrzeuge, Fahrer, die sich am Tempolimit oder am Gefühl orientieren). `gruppen.py` beschreibt
die Verteilung jeder Datei als Mischung solcher Gruppen, **soweit die Daten das belegen**, und die Detailseiten erlauben,
Kennzahlen und Histogramm für jede Gruppe sowie für Tageszeit und Wochentag getrennt anzusehen. Was die Gruppen nicht erklären,
steht in einem Rest.

**Was eine Gruppe ist und was nicht.** Eine Gruppe ist ein statistischer Anteil der Verteilung: eine Lognormal-Glocke mit
Anteil, häufigstem Tempo (Modus) und Streuung. Sie ist keine Fahrzeugart. Was sich dahinter verbirgt, lässt sich aus
Geschwindigkeiten allein nicht entscheiden. Plausible Deutungen stehen als Hypothesen in der Diskussion, nicht in den Daten.

## Verfahren

1. **Daten.** Fahrzeuge mit nutzbarer Zeit in vollständig aufgezeichneten Stunden, nach Abzug des Rauschbodens
   ([rauschen.md](rauschen.md)). Was der Abzug übrig lässt, liegt oft noch im Bereich des Rauschbodens; deshalb werden
   Fahrzeuge bis zur 95-%-Grenze des Rauschbodens plus 1 km/h nicht zerlegt. Wo kein Rauschboden belegt ist, bleibt ein Haufen
   am unteren Rand (Sensorgrenze) von der Anpassung ausgenommen (`abschneiden`). Beides erscheint in der Auswahl als
   „Unter X km/h (nicht zerlegt)“.
2. **Mischung mit abgeschnittener Verteilung.** Eine Mischung von K Lognormal-Verteilungen wird mit dem EM-Verfahren angepasst
   (mehrere feste Startwerte, die beste gilt; das Ergebnis ist reproduzierbar). Der Bereich links vom Rand der erfassten Daten
   gilt dabei als **nicht erfasst und nicht als null**: Die Dichte der Mischung wird auf den erfassten Bereich normiert, und die
   fehlende Fläche links fließt weder in die Passgüte noch in die Zahl der Fahrzeuge ein. Eine am Rand halbierte, gedrittelte
   oder sonst abgeschnittene Glocke wird deshalb aus der sichtbaren Flanke angepasst; die verdeckte Fläche ergänzt der
   Erwartungsschritt mit den Momenten der abgeschnittenen Normalverteilung. Eine Gruppe muss mindestens zu 25 % im erfassten
   Bereich liegen (`sichtbar_prozent`), sonst ist ihre Lage nicht bestimmbar. Ohne diese Behandlung entstehen schmale
   künstliche Gruppen am Rand: Eine naive Anpassung findet bei einer zur Hälfte abgeschnittenen Gruppe (Wahrheit: Modus 15,
   Streuung 0,25) eine Gruppe bei 17 km/h mit Streuung 0,11, die abgeschnittene Anpassung eine bei 15,2 km/h mit 0,23
   (`test_gruppen.py`).
3. **Zahl der Kurven K und Einteilung in Gruppen, je Datei.** K wird für jede Datei einzeln bestimmt, von 2 bis höchstens 8 (bei
   den bisherigen Daten endet die Suche nach höchstens 5). **Eine Gruppe besteht aus einer oder mehreren Kurven** (ihre Summe):
   Eine Lognormal-Glocke trifft die Form einer Gruppe oft nicht ganz (ein schmaler Gipfel am Rand, eine Schulter), und eine
   zweite Kurve in derselben Gruppe verbessert nur die Form, ohne dass es eine zweite Gruppe wäre. Die Kurven werden deshalb
   eingeteilt (`zusammenfassen`): Kurven, deren häufigstes Tempo weniger als 15 % (im Logarithmus 0,15) auseinanderliegt, bilden
   eine Gruppe. Stimmen die Gruppen in den beiden Hälften der Messtage dann nicht überein, werden die benachbarten Gruppen mit
   dem kleinsten Abstand der häufigsten Tempi so lange zusammengefasst, bis sie übereinstimmen (oder nur noch eine bleibt).
   Kurven innerhalb einer Gruppe dürfen zwischen den Hälften Masse tauschen; belegt sein muss die Summe, nicht ihre Aufteilung.
   (Das Prinzip, Komponenten einer Mischung zu Gruppen zusammenzufassen, wo sich die Gruppen nicht trennen lassen, ist in der
   Literatur zur Cluster-Analyse mit Mischungen gebräuchlich, etwa Baudry u. a. 2010 und Hennig 2010.) Eine Kurve mehr gilt nur,
   wenn alles zutrifft:
   - **Gewinn auf den anderen Tagen:** Die Anpassung auf den geraden Messtagen beschreibt die ungeraden Tage um mindestens
     0,005 nats je Fahrzeug besser als mit einer Kurve weniger (und umgekehrt). Sonst endet die Suche. Die Schwelle ist eine
     Effektgröße, kein Signifikanztest: Bei Zehntausenden Fahrzeugen belohnt jede Abweichung von der Lognormal-Form
     mit einem kleinen Gewinn.
   - **Stabil:** Die Gruppen aus den beiden Hälften der Messtage (gerade und ungerade Tage) stimmen in der Zahl, in der Lage
     (häufigstes Tempo der Summenkurve innerhalb von 7 % im Logarithmus, bei breiten Gruppen innerhalb 0,25 × Streuung) und im
     Anteil an den erfassten Fahrzeugen (innerhalb von 6 Prozentpunkten) überein.
   - **Nicht winzig:** Keine Gruppe unter 3 % in einer Hälfte.
   - **Sichtbar:** Jede Gruppe liegt zu mindestens 25 % im erfassten Bereich.
   - **Getrennt:** Der Ashman-Abstand D = √2 · |μᵢ − μⱼ| / √(σᵢ² + σⱼ²) zwischen allen Gruppen (Mittel und Streuung von ln v der
     Summenkurve) ist mindestens 1. Gibt es dafür keine Lösung, genügt ein getrenntes Paar „langsamste Gruppe gegen die nächste“,
     oder ein Gewinn von mindestens 0,02 nats, wenn die beiden langsamsten Gruppen im häufigsten Tempo um mindestens 15 %
     auseinanderliegen (breite Gruppe neben einem schmalen Gipfel). In beiden Fällen vermerkt die Seite, dass die Gruppen
     überlappen. Eine weitere Kurve, die die Zahl der Gruppen nicht ändert, braucht nur den Gewinn und die Stabilität.
   Die Suche endet, wenn der Gewinn unter die Schwelle fällt oder zwei Werte von K in Folge nicht stabil, zu klein oder zu
   wenig sichtbar sind. Gewählt wird das größte K, das alle Bedingungen erfüllt. Gibt es keins, bleibt es bei einer Gruppe
   (**keine Zerlegung**). Bei weniger als 5000 Fahrzeugen wird nicht zerlegt.
4. **Feste Kurven für alle Stunden und Tage.** Form und Lage der Gruppen gelten für alle Tageszeiten und Tage gleich; nur
   ihre Anteile werden je Auswahl neu geschätzt. Eine Auswahl (Tageszeit, Wochentag, Gruppe) ist damit eine einfache Summe über
   Zellen plus eine kleine Anpassung der Anteile.

**Warum nicht stündlich anpassen und die Gruppen verfolgen?** Das wurde ausprobiert: je Stunde und Tagtyp eine eigene Anpassung,
die Gruppen über den Tag verfolgt (Kontinuität, Impuls, zyklischer Schluss). Gemessen an 63 zerlegbaren Dateien mit
Training auf geraden und Test auf ungeraden Tagen brachte das gegenüber der festen Zerlegung wenig: 95 % des gesamten
Gewinns kommen schon von der festen Zerlegung, die zusätzliche Freiheit je Stunde bringt im Median 0,009 nats je Fahrzeug,
bei 9 von 63 Dateien ist sie auf ungesehenen Tagen schlechter (Überanpassung). Die Kennzahlen nach Abzug der langsamen
Gruppen weichen zwischen fester Zerlegung und stündlicher Anpassung im Median um 0,01 bis 0,04 km/h im Mittel ab. Das
Verfahren ist deutlich langsamer (rund 15 Sekunden je Datei statt 2 bis 5) und liefert keine besser belegte Identität der Gruppen. (Der Vergleich entstand mit der früheren Anpassung ohne Behandlung des abgeschnittenen Rands; er betrifft die Frage stündlich oder fest, nicht die Zahl der Gruppen.)

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

Gruppen in der Auswahl: „Alle Daten“, „Gruppe 1“ bis „Gruppe n“ (nach häufigstem Tempo geordnet, 1 ist die langsamste), „Rest (nicht
erklärt)“ und, wo ein Rauschboden abgezogen wurde, „Rauschboden (herausgerechnet)“. Ohne Zerlegung (K = 1) gibt es das Feld
„Gruppe“ nicht.

**Gruppen sind ihre Kurven, Fahrzeuge werden nicht zugeordnet.** Eine Gruppe ist die angepasste Kurve, bei mehreren Kurven in
einer Gruppe deren gewichtete Summe (jede Kurve auf Fläche 1 normiert, mal ihr Gewicht in der Gruppe). Für eine Auswahl
(Tageszeit, Tage) schätzt `filter.js` nur die Anteile der Gruppen neu (EM-Verfahren bei festen Kurven; Form und Lage der Gruppen bleiben die
der globalen Anpassung). Die Fahrzeuge einer Gruppe sind dann die Zahl der angepassten Fahrzeuge mal Anteil der Gruppe mal Form
ihrer Kurve. Die Kennzahlen einer Gruppe (Mittel, V85, V95, V99, Einhaltung) sind die der Kurve. Weil das Modell die Daten nie
ganz trifft, bleibt ein **Rest**: Daten minus die Kurven aller Gruppen, an keiner Geschwindigkeit negativ, dazu alle Fahrzeuge
unterhalb der Anpassungsgrenze. Die Anteile der Gruppen und des Rests müssen sich nicht zu 100 % addieren: Wo die Kurven über
den Daten liegen, zählt der Überschuss nicht als negativer Rest. Frühere Fassungen haben jedes Fahrzeug den Gruppen mit dem
Anteil zugeordnet, der an seiner Geschwindigkeit am besten passt. Das schob alles, was das Modell nicht erklärt, in die
Gruppe, deren Kurve dort am höchsten ist, und gab zum Beispiel einer langsamen Gruppe ein V99 von 56 km/h bei einem häufigsten
Tempo von 20 km/h.

**Darstellung.** Bei einer Gruppe oder dem Rest bleiben alle Fahrzeuge der Auswahl im Histogramm grau sichtbar. Farbig (blau bis zum
Tempolimit, orange darüber) ist der Teil, den die Gruppe erklärt, höchstens so hoch wie die graue Säule. Bei einer Gruppe liegt
ihre Kurve zusätzlich als Linie darüber, damit sichtbar bleibt, wo sie die Säulen überragt.

**Passung des Modells.** `modellabweichung_prozent` ist der Anteil der Fahrzeuge, die die angepasste Mischung an einer anderen
Geschwindigkeit sieht als die Daten (halbe Summe der Beträge der Unterschiede je km/h, ab der Anpassungsgrenze). Im Median über die 81
zerlegten Dateien sind es 2,9 % (Quartile 1,7 und 3,8), bei 9 Dateien mehr als 5 %, bei 3 mehr als 10 % (Kreitzweg 15,0 %,
Nievenheimer Straße mit der Datei `0000000000000000_12` 15,5 %, Villestraße `FR GV 0000000000000000_2` 27,7 %). Ab 10 % warnen die
Seiten, dass das Modell schlecht passt. Bei der Villestraße-Datei entsteht die schlechte Passung durch eine Gruppe von 7 % mit dem
häufigsten Tempo 3 km/h, also am Rand der Erfassung (angepasst wird ab 4 km/h); der Rest beträgt dort 29 %. Der
**Rest** ist größer als die Abweichung, weil er auch die Fahrzeuge unter der Anpassungsgrenze enthält: Median 7,6 % der
Fahrzeuge (Quartile 3,8 und 15,8 %). Am größten ist er bei den Dateien, in denen ein Haufen am unteren Rand abgeschnitten wurde
(Matthiasstraße 67 %, Feldstraße 58 %, Bauerbahn 43 %).

Die Zellen enthalten nur vollständig aufgezeichnete Stunden mit nutzbarer Zeit; die Zahl der Fahrzeuge einer Auswahl kann
deshalb geringfügig unter der Zahl in den Tabellen liegen.

## Was in der YAML steht

Block `gruppen` je Messung: `geprueft`, `anzahl` (Zahl der Gruppen), `kurven` (K, Zahl der angepassten Kurven; größer als
`anzahl`, wo eine Gruppe aus mehreren Kurven besteht), `obere_gruppen_ueberlappen`, `angepasst_ab_kmh`, `fahrzeuge`,
`fahrzeuge_unter_grenze`, `grund` (bei einer Gruppe), `auswahl` (je geprüftem K: `gruppen`, `stabil`, `klein`, `sichtbar_min`, `d_unten`, `d_alle`, `modus_abstand`, `cv_gewinn`),
`modellabweichung_prozent`, `gruppen` (Nummer, `kurven` je Gruppe, Anteil, Modus, Streuung im Logarithmus, `sichtbar_prozent`, Mittel, V85, Einhaltung,
qualifizierte Einhaltung; alles für die Summenkurve der Gruppe) und `rest` (Anteil und Kennzahlen dessen, was die Kurven nicht erklären,
einschließlich der Fahrzeuge unter der Anpassungsgrenze). Die Zellen liegen als `<Datei>.zellen.json` neben der YAML (Format
siehe `gruppen.py`, `analysiere`; je Gruppe `pi` (Anteil an den angepassten Fahrzeugen) und `kurven` mit `mu`, `s` und Gewicht `c` je
Kurve; die Form der Gruppe ist die Summe der Kurven, jede auf Fläche 1 normiert, mal `c`). Wie die Masse innerhalb einer Gruppe auf
ihre Kurven verteilt ist, wird nicht ausgewiesen, weil sie zwischen den Hälften der Messtage wechselt.

## Grenzen

- Eine Glocke ist keine Fahrzeugart. Zusammenhänge mit Tageszeit, Wochentag oder Wetter können Hinweise geben, beweisen aber
  keine Zuordnung. Wetterdaten sind nicht eingebunden.
- Bei überlappenden Gruppen ist die Trennung unsicher, auch wenn die Zerlegung stabil ist. Die Schwellen (0,005 und 0,02 nats, 7 %,
  6 Prozentpunkte, 3 %, D ≥ 1, 15 % Abstand der Modi) sind Festlegungen, kein Befund. Bei 28 der 109 Dateien gibt es keine Zerlegung
  (10 sind zu klein, bei 18 ist keine belegt); bei den übrigen 81 sind es 2 Gruppen (78 Dateien) oder 3 Gruppen (3), bei 7 davon
  mit überlappenden Gruppen. Bei 69 Dateien besteht jede Gruppe aus einer Kurve (66 mit 2 und 3 mit 3 Gruppen), bei 12 besteht
  eine der beiden Gruppen aus zwei Kurven (2 Gruppen aus 3 Kurven). Gegenüber der Zählung mit einer Kurve je Gruppe ändert sich bei
  13 Dateien etwas; bei 9 davon sinkt die Modellabweichung deutlich (zum Beispiel Hoistener Schulstraße von 7,8 auf 1,2 %).
- **Die Hälften der Messtage (gerade/ungerade) sind ein mildes Kriterium.** Gerade und ungerade Tage wechseln sich ab und haben
  dieselbe Mischung aus Wochentagen und Jahreszeit. Teilt man stattdessen den Zeitraum in eine erste und eine zweite Hälfte
  (einmalige Prüfung, nicht Teil des Verfahrens), bleibt von 81 Zerlegungen nur bei 38 dieselbe Zerlegung bestehen; bei 38 entsteht auf der
  zweiten Teilung keine, bei 5 eine andere. Das ist mit und ohne das Zusammenfassen von Kurven ähnlich (ohne: 41 von 80 gleich, 38 keine). Die Aussage ist
  deshalb: Die Gruppen sind in einer Messung über gemischte Tage stabil; ihre Anteile und teils ihre Lage können von der Zeit
  (Jahreszeit, Wochentag, Baustellen) abhängen. Das ist kein Beleg, dass sie falsch sind, aber ein Grund, die Anteile nicht als
  feste Größe eines Standorts zu lesen.
- Die Lognormal-Form ist eine Annahme, und die Gruppen hängen davon ab. Eine Lognormal-Kurve ist nach rechts schief; wo der
  Verkehr am Tempolimit gestaut wird, ist die Verteilung eher nach links schief (Schulter unterhalb des Limits, steile rechte
  Flanke). Ein Versuch mit schiefen Normalverteilungen (skew-normal, beide Schieflagen) senkte die Abweichung bei der
  Nievenheimer Straße (`0000000000000000_12`, Limit 50) von 15,5 auf 2,7 %, verschob dabei aber, was „die langsame Gruppe“ ist
  (statt eines Gipfels bei 20 km/h eine breite Gruppe von 18 bis 55 km/h). Gruppenparameter sind also Beschreibungen für die
  gewählte Kurvenform und keine Messgrößen. Der Versuch ist nicht übernommen: Die Anpassung ist dort etwa 20-mal langsamer.
  Verhalten wie ein Spitzer genau am Tempolimit wird als eigene schmale Gruppe beschrieben.
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
