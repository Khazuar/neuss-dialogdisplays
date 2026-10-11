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
   Fahrzeuge bis zur 95-%-Grenze des Rauschbodens plus 1 km/h nicht zerlegt. Wo kein Rauschboden belegt ist, beginnt die Anpassung
   beim kleinsten gemessenen Tempo. Das ist die Erfassungsgrenze der Geräte (bei 83 von 105 Dateien gleich der in der Geräte-
   konfiguration eingestellten „Erfassung ab“); links davon ist die Verteilung nicht erfasst (Schritt 2). Eine frühere Fassung
   nahm einen Haufen am unteren Rand von der Anpassung aus (erstes lokales Minimum unter 30 km/h). Das schnitt bei 38 von 64
   Dateien ohne belegten Rauschboden Fahrzeuge ab (Matthiasstraße 67 %) und verhinderte, dass tiefe Gipfel als Gruppe gefunden
   wurden (Düsseldorfer Straße: Gipfel unter 10 km/h). Fahrzeuge unter dem Rand der Anpassung gibt es nur noch, wo ein Rauschboden
   abgezogen ist; sie erscheinen in der Auswahl als „Unter X km/h (nicht zerlegt)“.
2. **Mischung mit abgeschnittener Verteilung.** Eine Mischung von K Lognormal-Verteilungen wird mit dem EM-Verfahren angepasst
   (mehrere feste Startwerte, die beste gilt; das Ergebnis ist reproduzierbar). Der Bereich links vom Rand der erfassten Daten
   gilt dabei als **nicht erfasst und nicht als null**: Die Dichte der Mischung wird auf den erfassten Bereich normiert, und die
   fehlende Fläche links fließt weder in die Passgüte noch in die Zahl der Fahrzeuge ein. Eine am Rand halbierte, gedrittelte
   oder sonst abgeschnittene Glocke wird deshalb aus der sichtbaren Flanke angepasst; die verdeckte Fläche ergänzt der
   Erwartungsschritt mit den Momenten der abgeschnittenen Normalverteilung. Eine Gruppe muss mindestens zu 25 % im erfassten
   Bereich liegen (`sichtbar_prozent`), sonst ist ihre Lage nicht bestimmbar. Ohne diese Behandlung entstehen schmale
   künstliche Gruppen am Rand: Eine naive Anpassung findet bei einer zur Hälfte abgeschnittenen Gruppe (Wahrheit: Modus 15,
   Streuung 0,25) eine Gruppe bei 17 km/h mit Streuung 0,11, die abgeschnittene Anpassung eine bei 15,2 km/h mit 0,23
   (`test_gruppen.py`). Die Streuung einer Kurve hat eine Untergrenze: nie unter 0,03 und nie schmaler als 0,8 km/h an ihrem
   häufigsten Tempo (die Geräte messen auf 1 km/h genau, eine Kurve soll nicht auf eine einzelne Klasse zusammenfallen). Die
   Grenze gilt am Tempo der Kurve, nicht am Rand der Erfassung: Eine frühere Fassung band sie an die kleinste erfasste
   Geschwindigkeit und zwang bei einer Erfassung ab 4 km/h jede Kurve auf mindestens 0,2, auch den schmalen Gipfel bei 46 km/h.
   Die Abweichung der Nievenheimer Straße (Datei `0000000000000000_12`) sank dadurch von 15,5 auf 3,2 %.
   Nach oben ist die Streuung auf 0,25 begrenzt (`S_MAX`, Festlegung). Eine breitere Lognormal-Kurve hat einen schweren rechten
   Ausläufer, der weit über das Tempo der schnellen Gruppen hinausreicht: Ohne die Grenze hatte in 62 von 97 zerlegten Dateien die
   langsamste Gruppe das größte V99 (Düsseldorfer Straße: Mittel 35 km/h, V99 93 km/h, die Hauptgruppe bei 51 km/h V99 76 km/h), weil
   die breite Kurve, die die flache Schulter bei niedrigem Tempo trifft, die wenigen sehr schnellen Fahrzeuge miterklärt. Mit der
   Grenze (0,3: 12 Dateien, 0,25: 3 Dateien) besteht eine breite Schulter aus mehreren schmaleren Kurven, und der Ausläufer gehört der
   schnellen Gruppe.
3. **Zahl der Kurven K und Einteilung in Gruppen, je Datei.** K wird für jede Datei einzeln bestimmt: Alle Werte von 2 bis 8 werden geprüft, die Suche bricht nicht ab (auch K = 5 kann\n   gut sein, wenn K = 3 nicht besser ist als K = 2). **Eine Gruppe besteht aus einer oder mehreren Kurven** (ihre Summe):
   Eine Lognormal-Glocke trifft die Form einer Gruppe oft nicht ganz (ein schmaler Gipfel am Rand, eine Schulter), und eine
   zweite Kurve in derselben Gruppe verbessert nur die Form, ohne dass es eine zweite Gruppe wäre. Die Kurven werden deshalb
   eingeteilt (`zusammenfassen`): Kurven, deren häufigstes Tempo weniger als 15 % (im Logarithmus 0,15) auseinanderliegt, bilden
   eine Gruppe. Ist eine Gruppe in einer der beiden Hälften der Messtage oder in der Anpassung an alle Tage zu klein (unter 3 %) oder
   stimmen Lage und Anteil nicht überein, geht die kleinste solche Gruppe in ihre Nachbarin mit dem näheren häufigsten Tempo auf.
   Das wiederholt sich, bis alle Gruppen übereinstimmen (oder nur noch eine bleibt). Eine winzige Kurve (zum Beispiel 1 % bei
   8 km/h) wird so Teil der benachbarten Gruppe, statt dass die großen Gruppen verschmelzen und die Zerlegung scheitert.
   Kurven innerhalb einer Gruppe dürfen zwischen den Hälften Masse tauschen; belegt sein muss die Summe, nicht ihre Aufteilung.
   (Das Prinzip, Komponenten einer Mischung zu Gruppen zusammenzufassen, wo sich die Gruppen nicht trennen lassen, ist in der
   Literatur zur Cluster-Analyse mit Mischungen gebräuchlich, etwa Baudry u. a. 2010 und Hennig 2010.) Eine Kurve mehr gilt nur,
   wenn alles zutrifft:
   - **Gewinn auf den anderen Tagen:** Die Anpassung auf den geraden Messtagen beschreibt die ungeraden Tage um mindestens
     0,005 nats je Fahrzeug besser als die letzte gültige Anpassung mit weniger Kurven (und umgekehrt); der Vergleich gilt nicht\n     nur gegenüber K − 1, denn eine Kurve, die allein wenig bringt, soll eine zweite nicht verhindern, die erst zusammen mit ihr viel\n     bringt. Die Schwelle ist eine
     Effektgröße, kein Signifikanztest: Bei Zehntausenden Fahrzeugen belohnt jede Abweichung von der Lognormal-Form
     mit einem kleinen Gewinn.
   - **Stabil:** Die Gruppen aus den beiden Hälften der Messtage (gerade und ungerade Tage) stimmen in der Zahl, in der Lage
     (häufigstes Tempo der Summenkurve innerhalb von 7 % im Logarithmus, bei breiten Gruppen innerhalb 0,25 × Streuung) und im
     Anteil an den erfassten Fahrzeugen (innerhalb von 6 Prozentpunkten) überein.
   - **Nicht winzig:** Keine Gruppe unter 0,5 % der angepassten Fahrzeuge oder mit weniger als 150 Fahrzeugen, in jeder Hälfte der
     Messtage und in der Anpassung an alle Tage (Festlegung; sie wächst bei kleinen Dateien). Eine frühere Fassung hatte 3 %:
     Ein deutlicher kleiner Gipfel (Nievenheimer Straße, 0,8 % der Fahrzeuge bei 9 km/h, rund 380 Fahrzeuge) wurde damit der
     Nachbargruppe zugeschlagen, obwohl er in beiden Hälften wiederkehrt.
   - **Sichtbar:** Jede Gruppe liegt zu mindestens 25 % im erfassten Bereich.
   - **Getrennt:** Der Ashman-Abstand D = √2 · |μᵢ − μⱼ| / √(σᵢ² + σⱼ²) zwischen allen Gruppen (Mittel und Streuung von ln v der
     Summenkurve) ist mindestens 1. Gibt es dafür keine Lösung, genügt ein Abstand von mindestens 0,5 zwischen allen Gruppen
     (Festlegung, teilweise überlappende Gruppen), ein getrenntes Paar „langsamste Gruppe gegen die nächste“, oder ein Gewinn von
     mindestens 0,02 nats, wenn die beiden langsamsten Gruppen im häufigsten Tempo um mindestens 15 % auseinanderliegen (breite
     Gruppe neben einem schmalen Gipfel). Unter einem Abstand von 1 vermerkt die Seite, dass die Gruppen überlappen. Eine weitere
     Kurve, die die Zahl der Gruppen nicht ändert, braucht nur den Gewinn und die Stabilität.
   Gewählt wird das größte K, das alle Bedingungen erfüllt. Gibt es keins, bleibt es bei einer Gruppe
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
JavaScript bleibt der Abschnitt verborgen, und die Seite zeigt die Tabelle der Kennzahlen je Zeitraum und das Histogramm aller
Fahrzeuge (beides entfällt mit JavaScript, weil die Auswahl es mit „alle Daten“ und der jeweiligen Tageszeit ersetzt). Der Vergleich Tag und Nacht bleibt
in beiden Fällen.

Gruppen in der Auswahl: „Alle Daten“, „Gruppe 1“ bis „Gruppe n“ (nach Anteil geordnet: Gruppe 1 ist die größte, vermutlich die Hauptgruppe; bei gleichem Anteil die langsamere), „Rest (nicht
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
Geschwindigkeit sieht als die Daten (halbe Summe der Beträge der Unterschiede je km/h, ab der Anpassungsgrenze). Im Median über die 97
zerlegten Dateien sind es 2,1 % (Quartile 1,6 und 2,7), bei keiner mehr als 5 % (höchstens 4,0 %). Ab 10 % warnen die
Seiten, dass das Modell schlecht passt. Bei 11 Gruppen liegt das häufigste Tempo nicht über dem Rand der Anpassung: Die Glocke ist
dort am Rand abgeschnitten und wird aus ihrer sichtbaren Flanke angepasst (Schritt 2), das ist gewollt. Der **Rest** (Daten minus
die Kurven, nie negativ) beträgt im Median 2,9 % der Fahrzeuge (Quartile 2,0 und 4,7 %). Er enthält auch die Fahrzeuge unter der
Anpassungsgrenze; die gibt es nur, wo ein Rauschboden abgezogen ist (41 der 97 Dateien) und der Abzug einen Teil der Fahrzeuge unterhalb der
Grenze lässt (Rest bei der Feldstraße 58 % der Fahrzeuge, bei der Bauerbahn 42 %, bei der Martinstraße 41 %, fast alles davon unter der Grenze).

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
  6 Prozentpunkte, 3 %, D ≥ 1 und D ≥ 0,5, 15 % Abstand der Modi, Streuung höchstens 0,25) sind Festlegungen, kein Befund. Bei 12 der 109 Dateien gibt es keine Zerlegung
  (10 sind zu klein, bei 2 ist keine belegt); bei den übrigen 97 sind es 2 Gruppen (43 Dateien), 3 Gruppen (37), 4 Gruppen (12), 5 (3) oder 6 (2),
  bei 6 davon mit überlappenden Gruppen. Bei 31 Dateien besteht jede Gruppe aus einer Kurve, bei 66 besteht mindestens eine Gruppe aus mehreren
  Kurven (im Mittel 4,0 Kurven je Datei, bis zu 7). Gruppen unter 3 % der Fahrzeuge gibt es in 20 Dateien (27 Gruppen).
- **Die Hälften der Messtage (gerade/ungerade) sind ein mildes Kriterium.** Gerade und ungerade Tage wechseln sich ab und haben
  dieselbe Mischung aus Wochentagen und Jahreszeit. Teilt man stattdessen den Zeitraum in eine erste und eine zweite Hälfte
  (einmalige Prüfung, nicht Teil des Verfahrens), bleibt von 97 Zerlegungen nur bei 39 dieselbe Zerlegung bestehen (gleiche Zahl der Gruppen, Lage innerhalb von 15 %, Anteil innerhalb von
  8 Prozentpunkten); bei 17 entsteht auf der zweiten Teilung keine, bei 41 eine andere (eine Datei wird nur auf der zweiten Teilung
  zerlegt). Mit mehr Gruppen und kleineren Gruppen (ab 0,5 %) ändert sich bei einer anderen Teilung häufiger die Zahl der Gruppen. Vor der
  Zusammenfassung von Kurven und der vollständigen Suche nach K war es ähnlich (von 81 Zerlegungen 38 gleich, 39 keine, 4 andere). Die Aussage ist
  deshalb: Die Gruppen sind in einer Messung über gemischte Tage stabil; ihre Anteile und teils ihre Lage können von der Zeit
  (Jahreszeit, Wochentag, Baustellen) abhängen. Das ist kein Beleg, dass sie falsch sind, aber ein Grund, die Anteile nicht als
  feste Größe eines Standorts zu lesen.
- Die Lognormal-Form ist eine Annahme, und die Gruppen hängen davon ab. Eine Lognormal-Kurve ist nach rechts schief; wo der
  Verkehr am Tempolimit gestaut wird, ist die Verteilung eher nach links schief (Schulter unterhalb des Limits, steile rechte
  Flanke). Ein früherer Versuch mit schiefen Normalverteilungen (skew-normal, beide Schieflagen) senkte die Abweichung bei der
  Nievenheimer Straße (`0000000000000000_12`, Limit 50) von 15,5 auf 2,7 %, verschob dabei aber, was „die langsame Gruppe“ ist
  (statt eines Gipfels bei 20 km/h eine breite Gruppe von 18 bis 55 km/h). Gruppenparameter sind also Beschreibungen für die
  gewählte Kurvenform und keine Messgrößen. Der Versuch ist nicht übernommen: Die Anpassung ist dort etwa 20-mal langsamer. Er
  entstand vor der Korrektur der Untergrenze der Streuung (Schritt 2); mit ihr erreichen Lognormal-Kurven dort 3,2 %, der größte
  Teil der damaligen Abweichung kam also von dieser Untergrenze und nicht von der Kurvenform.
  Verhalten wie ein Spitzer genau am Tempolimit wird als eigene schmale Gruppe beschrieben.
- Die Anpassung ist deterministisch, aber nicht eindeutig: Andere Startwerte können bei knappen Fällen eine andere Zerlegung
  finden. Ein Versuch, jede weitere Kurve dort zu starten, wo die Daten das bisherige Modell am stärksten übersteigen (der markanteste
  noch nicht gedeckte Gipfel, wie man von Hand vorginge), erhöhte die Likelihood leicht, ließ aber zum Beispiel bei der Düsseldorfer
  Straße die breite Gruppe bei 22 km/h in der Gruppe bei 36 km/h aufgehen (2 statt 3 Gruppen); mit Startwerten aus Quantilen und
  Zufall bleiben die drei Gipfel getrennt. Der Versuch ist nicht übernommen. Bei gleich guten Anpassungen entscheidet damit die
  Wahl der Startwerte darüber, wie die Masse auf Kurven und Gruppen verteilt wird.

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
