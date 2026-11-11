# Einsätze: Bewegungen der Geräte, Zuordnung zu den Messungen, Brüche

> Eigene Auswertung, nicht amtlich. Fehler im Verfahren und in der Auswertung können nicht ausgeschlossen werden (ohne Gewähr). Keine der
> Zuordnungen ist von der Verwaltung bestätigt, solange das nicht ausdrücklich dasteht.

## Worum es geht

Die Verwaltung liefert je Messung eine Datei: Standort, Fahrtrichtung, Zeitraum. Eine Datei beschreibt aber nicht immer genau einen Standort.

- **Erst auslesen, dann umhängen:** Meist wurde das Gerät an einem Tag ausgelesen (neue Datei) und erst Tage oder Wochen später umgehängt. Der
  Anfang einer Datei gehört dann noch zum vorigen Standort.
- **Zurückgesetzte Uhr:** Einige Geräte haben 2023 nach dem Einschalten mit der Werkszeit 01.01.2020 12:00 weitergezählt. Diese Daten hat die
  Auswertung je Messung bisher verworfen.
- **Defekte Messungen:** Mehrere Auswertungen hat die Verwaltung selbst als „defekt“ oder „fehlerhaft“ bezeichnet.

Darum setzen wir je Gerät alle Dateien zu einem **Gesamtstrom** zusammen, suchen darin die **Bewegungen** (Umhängen, Inbetriebnahme) und
ordnen die Zeiträume dazwischen den Messungen zu.

| Begriff | Bedeutung |
|---|---|
| **Standort** | physischer Ort (dieselbe Straße, ungefähr derselbe Streckenabschnitt; eine Detailseite) |
| **Messung** | Datei der Verwaltung: Standort, Fahrtrichtung und Zeitraum, wie geliefert |
| **Gesamtstrom** | alle Fahrzeuge eines Geräts aus allen Dateien, in Ortszeit, ohne Doppelte |
| **Bewegung** | Unterbrechung mit minutengenauem Beginn und Ende, nach der sich der Verkehr ändert (Umhängen, Inbetriebnahme) |
| **Aufenthalt** | Zeitraum zwischen zwei Bewegungen: Das Gerät hing an einem Ort |
| **Bruch** | jede andere dauerhafte Änderung des Verkehrs (Tagesauflösung, [abschnitte.md](abschnitte.md)) |
| **Teil** | Stück eines Aufenthalts zwischen zwei Brüchen |
| **Einsatz** | der Zeitraum, in dem ein Gerät tatsächlich an einem Standort in eine Fahrtrichtung gemessen hat: die Teile, die zu einer Messung gehören |

Die **Hauptauswertung folgt den Einsätzen** (Ansicht „Einsätze“ der Übersicht, erste Wahl auf den Detailseiten). Die **Sicht der Verwaltung**
(die Messungen, wie geliefert) bleibt erhalten. Mit ihr vergleichen wir die Mitteilungen. Nur Messungen, die die Verwaltung selbst als defekt
bezeichnet, führen wir nicht als Messung auf (siehe unten).

## Ablauf

1. **Je Messung** (`dsd2csv.py`): Parsen, Uhr, Brüche, Kennzahlen der Sicht der Verwaltung (unverändert, [abschnitte.md](abschnitte.md)).
2. **Gesamtstrom und Bewegungen** (`bewegungen.py`, `uhr_rekonstruktion.py`):
   1. Gesamtstrom aus den Uhr-Segmenten mit gültiger Uhr;
   2. erster Durchgang der Bewegungserkennung;
   3. Rekonstruktion der zurückgesetzten Uhren mit den Montagetagen des ersten Durchgangs als Anker;
   4. zweiter Durchgang mit den rekonstruierten Daten;
   5. Aufenthalte, je Aufenthalt die Bruchsuche wie je Messung ([abschnitte.md](abschnitte.md)).

   Das Ergebnis liegt im Zwischenspeicher (Ebene „bewegungen“); ein Lauf ohne ihn dauert einige Minuten.
3. **Zuordnung und Einsätze** (`einsaetze.py`): Teile den Messungen zuordnen, Einsätze bilden, Brüche erklären.
4. **Je Einsatz** (`einsaetze.py`, Durchgang C): Je Einsatz-Abschnitt Rauschboden und Regenanteil (Wetterstation des Standorts),
   Kennzahlen, Gefährdung, Lärm, Nächte, Zellen der Auswahl und Verhaltensgruppen. Grundlage sind die Stunden des Gesamtstroms (Stunde × km/h,
   vor jedem Abzug).
5. `stadtgruppen.py` bildet Standort- und Stadtgruppen aus den Gruppen der Einsätze; `daten_bauen.py` schreibt `einsaetze.csv`,
   `brueche.csv`, `bewegungen.csv` und die Stundendaten beider Sichten.

## Gesamtstrom

- **Gültige Uhr:** Uhr-Segmente mit gültiger Uhr (`dsd2csv.bewerte_segmente`) gehen ein, wenn sie mindestens 200 Fahrzeuge haben und ihre
  Zeiten zwischen 2019 und dem Tag der Rechnung liegen. Kleinere „gültige“ Segmente sind fast immer Uhr-Müll, etwa die Thywissenstraße 2022.
- **Zurückgesetzte Uhr:** Diese Segmente gehen nur ein, wenn die Rekonstruktion ihre Lage „belegt“ oder „wahrscheinlich“ macht.
- **Doppelte Fahrzeuge** (gleiche Zeit und Geschwindigkeit aus zwei Dateien) zählen einmal. Ein Beispiel sind die Dateien `_7.dsd` der
  Rosellener Schulstraße und der Lanzerather Dorfstraße: Sie sind byteweise gleich.

### Uhr-Rekonstruktion (`uhr_rekonstruktion.py`)

**Hypothese** je Segment mit zurückgesetzter Uhr: Die Uhr begann beim Einschalten bei 01.01.2020 12:00 und lief gleichmäßig weiter, ohne
Sommerzeit. Echte Zeit = Gerätezeit + Delta. Gesucht ist Delta.

**Anker** legen die Lage unabhängig voneinander fest:

| Anker | Bedingung |
|---|---|
| Beginn an Montagetag | Das Einschalten fällt auf einen Tag, an dem ein Gerät sicher montiert wurde (erster Durchgang der Bewegungserkennung). |
| Ende an Auslese-Runde | Das Ende fällt auf einen Tag, an dem mindestens drei Geräte eine Dateigrenze haben. |
| Ende am Exportdatum | Das Ende fällt auf das Datum im Dateinamen (±1 Tag). |
| Ende an nächster Aufzeichnung | Die nächste gültige Aufzeichnung desselben Geräts beginnt direkt nach dem letzten Fahrzeug (±3 Stunden). |
| Zeitumstellung | Der Tagesgang springt in Gerätezeit am amtlichen Umstellungstag (±1 Tag) um eine Stunde. |

**Proben** dürfen nicht widersprechen: Das Wochenmuster (ohne Ferien und Feiertage) muss auf den richtigen Wochentagen liegen. Der
Werktags-Tagesgang darf höchstens 60 Minuten neben dem typischen Verlauf liegen.

**Kandidaten:** Phase (Wochentag und Uhrzeit des Beginns) aus Wochenmuster und Tagesgang in der ersten Woche nach dem Abbau, dann je 7 Tage
weiter bis zur nächsten Aufzeichnung. Der Endanker ist immer ein Kandidat.

**Entscheidung:**

- **belegt:** mindestens zwei Anker, und kein anderer Kandidat hat ebenso viele.
- **wahrscheinlich:** ein Anker, Wochenmuster und Tagesgang bestätigt, und kein anderer Kandidat hat einen Anker mit bestätigtem Wochenmuster.
- **offen:** sonst.

Segmente unter zwei Tagen oder 500 Fahrzeugen werden nicht rekonstruiert. Das betrifft Uhren, die täglich neu gestartet sind, etwa die
Weinstockstraße mit 48 solchen Segmenten.

## Bewegungen (`bewegungen.py`)

### Kandidaten

- **Pause:** mindestens 3 Stunden ohne Fahrzeug, davon mindestens eine Stunde zwischen 7 und 19 Uhr an einem Werktag, oder länger als
  48 Stunden. Nachts ist an ruhigen Straßen oft stundenlang nichts los.
- **Lücke:** die längste Lücke eines Werktags zwischen 7 und 19 Uhr, wenn sie länger ist als an jedem anderen Werktag im Umkreis von 21 Tagen
  (mindestens 15 Minuten).
- **Unerwartete Lücke:** eine Lücke ab 10 Minuten zwischen 7 und 19 Uhr an einem Werktag, in der nach dem Verkehr der Stunde davor oder danach
  mindestens 20 Fahrzeuge zu erwarten waren. Beim Wechsel von einer lauten an eine ruhige Straße sind die natürlichen Lücken am neuen Ort länger
  als die Transportlücke; das Längenkriterium allein übersieht dann das Umhängen. Beispiel: Konradstraße, 15.05.2025, 08:52 bis 09:35.
  Diese Kandidaten erben nie die Änderung eines benachbarten Kandidaten (siehe unten).

Kandidaten weniger als 2 Tage auseinander, zwischen denen höchstens 50 Fahrzeuge liegen, sind ein Umbau (etwa abends abgebaut, morgens
aufgehängt). Liegt dazwischen Verkehr, bleiben sie getrennt.

### Änderung über den Kandidaten

Verglichen werden bis zu 7 Werktage davor mit bis zu 7 Werktagen danach, jeweils 7 bis 19 Uhr. Beide Seiten haben denselben Ferienstatus.
Die Fenster reichen höchstens 21 Tage weit und nicht über andere Montagen hinweg.

- **Tempoverteilung:** totale Variation ab 15 km/h.
- **Verkehrsmenge:** |ln| des Verhältnisses der Fahrzeuge je Stunde.
- **z:** robuster z-Wert (Median, MAD) gegen dieselben Größen an den Tagesgrenzen desselben Geräts im Umkreis von 45 Tagen. Tage näher als
  10 Tage an einem Kandidaten bleiben dabei weg. Es zählt der größere der beiden Werte.

### Stufen

| Stufe | Bedingung | trennt Aufenthalte |
|---|---|---|
| **umhaengen** | Lücke oder Pause bis 48 h mit z ≥ 8, oder z ≥ 4 an einem Aktionstag (±1 Tag) | ja |
| **inbetriebnahme** | Pause über 48 h mit z ≥ 2,5; montiert spätestens beim ersten Fahrzeug danach | ja |
| **inbetriebnahme_ungeprueft** | Pause über 48 h ohne Vergleich (zu wenige Werktage davor oder danach) | ja |
| **aktionstag** | an einem Aktionstag ändert sich der Verkehr über den Tag (z ≥ 2,5), mit einer Lücke von mindestens 10 Minuten | ja |
| **eingriff** | Lücke am Tag mit Änderung, aber ohne stimmige Tagesprobe (Wartung, Neuausrichtung?) | nein |
| **pause_gleicher_ort** | Pause über 48 h ohne Änderung (Akku leer?) | nein |
| **moeglich** | z von 4 bis 8 außerhalb eines Aktionstags, oder z von 2,5 bis 4 | nein |

- **Aktionstag:** ein Werktag, an dem ein Gerät mit z ≥ 8 umgehängt oder in Betrieb genommen wurde. Die Annahme dahinter ist, dass ein Trupp an
  einem Tag mehrere Displays umhängt. Die Lücken eines Tages liegen nacheinander, und die Wege dazwischen passen zur Entfernung.
- **Tagesprobe** (für jedes Umhängen und jeden Aktionstag innerhalb eines Tages): Sie sucht den Wechselpunkt im Tagesverlauf aus Tempoverteilung
  und Verkehrsmenge (Poisson-Prozess mit dem Tagesgang der Tage davor und danach).
  - Signifikanz: 300 Vertauschungen, p ≤ 0,01.
  - Die Richtung muss passen.
  - Der Wechselpunkt liegt höchstens 30 Minuten neben der Lücke.

  Ohne stimmige Probe fällt ein Aktionstag weg, und ein Umhängen wird zum Eingriff. Fällt ein Kandidat weg, ist er keine Grenze der
  Vergleichsfenster mehr, und die übrigen werden neu geprüft.

### Brüche in den Aufenthalten und ihre Verfeinerung

Die Bruchsuche ([abschnitte.md](abschnitte.md)) läuft je Aufenthalt. Sie liefert nur den Tag eines Bruchs und braucht auf jeder Seite
mindestens **7 volle Tage** (24 Stunden mit Daten, ohne Ferien und Feiertage). Diese Mindestlänge ist eine Festlegung, keine Eigenschaft der
Daten: Jeder Abschnitt soll jeden Wochentag einmal enthalten, damit Werktag und Wochenende sich ausgleichen und der Mittelwert stabil ist. Die
Folgen:

- Ein Wechsel in den ersten 7 vollen Tagen eines Aufenthalts kann nicht am richtigen Tag stehen. Er wird übersehen oder auf den 8. Tag
  geschoben (der angebrochene Montagetag zählt nicht).
- Eine Episode unter 7 Tagen kann kein eigener Abschnitt sein. Episoden bis 21 Tage, nach denen der Verkehr zum alten Niveau zurückkehrt, gelten
  als Ausschlag.

Darum wird jeder Bruch **auf Fahrzeugebene verfeinert**: im Fenster von 9 Tagen vor bis 2 Tagen nach dem Bruchtag der Wechselpunkt der
Log-Likelihood aus Tempoverteilung und Verkehrsmenge (Poisson mit dem Tagesgang je Werktag, Samstag, Sonntag) der Seiten davor und danach. Die
Seiten werden einmal mit dem neuen Zeitpunkt neu geschätzt. Liegt das Ergebnis am Rand des Fensters, bleibt es beim Bruchtag. Die Teile werden am
verfeinerten Zeitpunkt getrennt.

**Ohne Bruchsuche trennen die Dateigrenzen.** Ist die Bruchsuche in einem Aufenthalt nicht möglich (weniger als 14 volle Tage) oder sieht sie
den Verkehr am Tag nicht (weniger als die Hälfte der Werktagsstunden von 9 bis 17 Uhr mit Fahrzeugen), wird der Aufenthalt an den
Dateigrenzen geteilt. Diese Grenzen heißen „ungeprüft“: Dort ist die Angabe der Verwaltung der einzige Hinweis, es gibt keinen Schnitt.
Beispiel: Das Gerät an Krupp- und Berghäuschensweg zählte von Oktober 2022 bis März 2023 werktags zwischen etwa 9 und 18 Uhr keine Fahrzeuge,
während die Uhr weiterlief. Beispiel: Viersener Straße, Bruch am 14.05.2025 (Bruchsuche) → 14.05.2025, 07:18 (verfeinert); dort wurde das
Tempolimit auf 30 gesenkt.

Die Uhrzeiten sind das letzte Fahrzeug vor und das erste nach der Lücke. An ruhigen Straßen kann die Arbeit am Mast etwas früher oder später
gewesen sein. Bei einer Inbetriebnahme ist das erste Fahrzeug nur „spätestens“.

## Zuordnung der Teile zu den Messungen (`einsaetze.py`)

Jedes Teil gehört zu einer Messung desselben Geräts oder zu keiner. Die **Reihenfolge der Messungen** gilt als richtig: Sortiert wird nach dem
ersten Fahrzeug ihrer Datei im Gesamtstrom. Jede Messung bekommt einen zusammenhängenden Block von Teilen.

| Beleg | Punkte |
|---|---|
| Anteil der Tage des Teils in der Datei der Messung | × 3 × Größe (Tage / 14, höchstens 1) |
| Anteil des Teils im Erfassungszeitraum der Mitteilung (`belege/korrekturen.json`) | × 3; ohne Überlappung −1 |
| Beginn bzw. Ende gleich dem des Erfassungszeitraums (±1 Tag) | je +1 |
| V85 passt nicht zum Limit (Limit ab 50: V85 unter 35; Limit bis 30: V85 über Limit + 20) | −1 |
| Teil keiner Messung zugeordnet | −0,5 × Größe |
| Zwei Aufenthalte nacheinander in derselben Messung, deutlich verschieden (TVD über 0,1 oder Menge außerhalb 0,7–1,4) | −3 |
| Ein Aufenthalt auf zwei Messungen verteilt (Wechsel an einem Bruch, ohne Bewegung) | −2 |
| Messung, deren Datei Daten im Gesamtstrom hat, bekommt kein Teil | −2 |

Die beste Gesamtzuordnung findet eine dynamische Programmierung. **Sicherheit** je Teil: Abstand der besten Lösung zur besten, in der das Teil
woanders hingehört. Ab 1,5 Punkten gilt die Zuordnung als sicher. Der Datei-Anteil ist ein Hinweis, kein Beweis: Nach dem Muster „erst
auslesen, dann umhängen“ beginnt eine Datei oft noch am vorigen Standort.

## Einsätze

Je Messung gibt es einen Einsatz aus ihren Teilen. Jedes Teil ist ein **Einsatz-Abschnitt**. Rauschboden, Regenanteil und Verhaltensgruppen
werden je Einsatz-Abschnitt geschätzt.

| Grenze | Bedeutung | ausgenommen |
|---|---|---|
| Bewegung | Umhängen oder Inbetriebnahme, minutengenau | die Lücke selbst (keine Daten) |
| Bewegung ohne Wechsel der Messung | gleicher Standort laut Zuordnung; ungeklärt (anderer Mast, andere Richtung, Neuausrichtung?) | die Lücke |
| Bruch | bleibt im Einsatz; erklärt durch Ereignis oder unerklärt | nichts |
| Ortswechsel ohne Bewegung | Wechsel der Messung an einem Bruch, ohne erkennbare Transportlücke | Tag des verfeinerten Wechsels (ohne Verfeinerung: Bruchtag und Vortag) |
| Wechsel der Messung am selben Standort | etwa neues Tempolimit nach dem Auslesen (Viersener Straße) | wie beim Ortswechsel ohne Bewegung |
| Dateigrenze, ungeprüft | ohne Bruchsuche: die Datei der Verwaltung entscheidet | nichts |

| Status | Bedeutung |
|---|---|
| `identisch` | nur Daten der eigenen Datei, alle Daten der Datei im Einsatz |
| `ergaenzt` | wie identisch, aber mit Daten außerhalb des Erfassungszeitraums der Mitteilung oder mit rekonstruierter Uhr |
| `gekuerzt` | ein Teil der eigenen Datei gehört zu einem anderen Einsatz oder zu keinem Standort mit Messung |
| `abgeleitet` | enthält Daten aus Dateien anderer Messungen desselben Geräts |
| `unsicher` | wie abgeleitet oder gekürzt, aber eine der Grenzen beruht auf einer unsicheren Zuordnung |

Der **Erfassungszeitraum der Mitteilung** ist für die Einsätze nur ein Beleg der Zuordnung. Daten außerhalb gehören zum Einsatz, wenn das Gerät
dort hing. Für die Ansicht „Messung“ bleibt er maßgeblich ([abschnitte.md](abschnitte.md)).

**Nicht zugeordnete Teile** (`nicht_zugeordnet` in `einsaetze.json`) und **Messungen ohne Einsatz** (`messungen_ohne_einsatz`) sind offene
Fragen. Ein Beispiel ist die Kreitzweg-Datei: Sie setzt nach unserer Zuordnung nur die Nievenheimer Straße fort.

## Brüche der Messungen

Die Brüche je Messung (`dsd2csv.py`) werden in dieser Rangfolge erklärt:

1. **Angabe der Verwaltung** (`belege/brueche-verwaltung.json`): bestätigt.
2. **Bewegung:** Eine trennende Bewegung desselben Geräts liegt kurz vor dem Bruch, höchstens 8 gewöhnliche Tage davor oder einen Tag danach.
   Ferien und Feiertage zählen dabei nicht. Die Bruchsuche braucht auf jeder Seite mindestens 7 Tage und lässt Ferien aus; darum liegt der
   Bruch oft einige Tage nach dem Umhängen. Beispiel: Die Brüche am ersten Schultag nach den Osterferien 2025 (27.04.) gehen auf das
   Umhängen am 14./15.04.2025 zurück.
3. **Ereignis, plausibel:** erster Schultag nach Ferien oder erster Ferientag (±1 Tag), Beginn oder Ende eines länger dauernden Ereignisses
   (`belege/ereignisse.json`). Kurze Ereignisse werden nur als zeitliche Nähe genannt.
4. **Unerklärt:** Diese Brüche sind Fragen an die Verwaltung.

Die Brüche in den Aufenthalten (Bruchsuche auf dem Gesamtstrom) werden genauso erklärt, ohne Schritt 2. Sie stehen als Grenzen der
Einsatz-Abschnitte in `einsaetze.json`. Messung und Gesamtstrom finden nicht immer dieselben Brüche: Die Fenster sind verschieden. Die Brüche der
Messungen aus denen des Gesamtstroms abzuleiten, ist der nächste Schritt.

## Defekte Messungen

Für einige Messungen von 2023 hat die Verwaltung ein PDF beigelegt, das sie selbst „defekt“ oder „fehlerhaft“ nennt. Ein solches PDF liegt im
Ordner der Messung oder im obersten Ordner darüber; trägt sein Name ein Datum, ist es das Datum im Namen der Datei. Diese Messungen führen wir
nicht als Messung auf: Zeitraum und Zuordnung der Verwaltung sind dort nach ihrer eigenen Angabe falsch. Ihre Daten gehen in die Einsätze ein,
soweit die Zuordnung sie trägt. Auf der Detailseite steht dann nur der Einsatz, mit einem Hinweis.

## Ergebnis (Stand November 2026)

**Gesamtstrom:** 11,4 Millionen Fahrzeuge an 12 Geräten.

- **Uhr-Rekonstruktion:** Von den Segmenten mit zurückgesetzter Uhr sind 7 belegt und 1 wahrscheinlich, zusammen rund 217.000 Fahrzeuge aus
  2023. Davon betroffen sind Cyriakusstraße, Lanzerather Dorfstraße, Rosellener Schulstraße, Buscherhofstraße, Weinstockstraße,
  Holzheimer Weg 109 und Kuhweg.
- **Nicht rekonstruiert:** Ein Segment bleibt offen (Kuhweg, 08.09. oder 13.09.2023). 57 sehr kurze Segmente werden nicht rekonstruiert;
  das sind Uhren, die täglich neu gestartet sind.

**Bewegungen:**

| Stufe | Anzahl |
|---|---|
| Umhängen mit Transportlücke | 39 |
| Umhängen am Aktionstag | 1 |
| Inbetriebnahme nach Pause | 39 |
| Inbetriebnahme ohne Vergleich | 13 |
| Eingriff, Pause am selben Ort, möglich (trennen nichts) | 55 |

Es gibt 52 Aktionstage. **99 Einsätze** in 112 Einsatz-Abschnitten; 87 davon beginnen mit einer erkannten Bewegung.

| Status | Anzahl |
|---|---|
| identisch | 25 |
| abgeleitet | 43 |
| gekürzt | 21 |
| unsicher | 10 |

**Befunde 2023:**

- **19.07.2023:** Das war nur eine Auslese-Runde. Umgehängt wurde erst vom 06. bis 13.09.2023.
- **Kuhweg, Holzbüttgener Straße, Nierenhofstraße:** Diese Dateien beginnen mit sieben Wochen Daten vom jeweils vorigen Standort.
- **Defekte Messungen:** Hinter den Auswertungen, die die Verwaltung „defekt“ nennt, stecken meist zurückgesetzte Uhren. Die Daten gehören zum
  Standort, an dem das Gerät nach dem Auslesen hing.

**Brüche der Messungen:** Von 34 Brüchen sind

- 29 durch eine Bewegung belegt;
- 2 durch eine Inbetriebnahme ohne Vergleich plausibel;
- 3 unerklärt: Schluchenhausstraße 10.02.2023, Hermannstraße 06.09.2023, Ruhrstraße 09.07.2026.

Darunter sind auch die früher nur mit den Ferien erklärten Brüche nach Ostern und den Sommerferien 2025. Dort wurde am 14./15.04. bzw. am
17.07.2025 umgehängt.

**Offene Fälle:**

- **Kreitzweg 2023:** Die Datei setzt die Nievenheimer Straße fort, ohne Bewegung und ohne Bruch. Sie hat keinen eigenen Einsatz.
- **Krupp- und Berghäuschensweg (2022/23):** Das Gerät zählte werktags tagsüber nichts; die Bruchsuche sieht nur Nächte und Wochenenden.
  Getrennt wird an den Dateigrenzen (ungeprüft).
- **Gerät 17385, 04. bis 08.05.2023:** Fünf Tage an einem Ort ohne Messung (68 Fahrzeuge je Stunde, V85 34).
- **Gerät 16734, 09. bis 15.05.2025:** Sechs Tage an einem lauten Ort ohne Messung (rund 1.400 Fahrzeuge am Tag, V85 47), dann Umhängen am
  15.05.2025 zwischen 08:52 und 09:35 an die Konradstraße. Die Datei der Konradstraße beginnt am 09.05.
- **Liedberger Straße:** Am 28.11.2025 wurde umgehängt. Davor zählte das Gerät 841 Fahrzeuge am Tag bei V85 44, danach 126 bei V85 32.
  Beides liegt im Erfassungszeitraum der Mitteilung, die V85 44 nennt. Welcher Ort ist die Liedberger Straße?
- **Viersener Straße:** Am 14.04.2025 von 13:53 bis 14:18 wurde umgehängt, die Dateien wechseln aber erst am 15.05. (Tempo 50 auf 30). Wir
  ordnen die Zeit ab dem 14.04. der Tempo-30-Messung zu. War es ein Richtungswechsel?
- **Villestraße (stationär):** Drei aufeinanderfolgende Dateien je Richtung (März 2023 bis März 2024) zeigen weder Bewegung noch Bruch. Sie
  bilden je einen Einsatz.
- **Brüche kurz nach der Inbetriebnahme:** Norfer Kirchstraße 2023 hat einen Bruch, verfeinert auf den 20.09.2023, eine Woche nach der
  Inbetriebnahme. In der ersten Woche fuhren 32 bis 37 % schneller als erlaubt, danach 45 bis 55 %. Bei der Konradstraße 2025 war es dagegen
  ein übersehenes Umhängen (siehe oben).

## Grenzen und Gegenhypothesen

- **Eine Lücke ist nicht immer ein Umhängen.** Darum braucht ein Umhängen eine deutliche Änderung des Verkehrs (z ≥ 8, an Aktionstagen ≥ 4) und
  eine stimmige Tagesprobe. Eine Baustelle, die am selben Tag beginnt, an dem das Gerät gewartet wird, sähe genauso aus.
- **Verschiedene Orte gleichen Typs sehen sich ähnlich.** Ein Umhängen zwischen zwei ähnlichen Straßen ohne Lücke bleibt unentdeckt. Dann liegt
  es in einem Aufenthalt, und die Zuordnung kann es nur an einem Bruch trennen.
- **Die Uhr-Rekonstruktion ist eine Hypothese.** Sie beruht auf gleichmäßig laufender Uhr und unabhängigen Ankern. Jede Entscheidung steht mit
  ihren Ankern in `einsaetze.json` (`geraete[].rekonstruktion`).
- **Alle Schwellen sind Festlegungen, kein Befund.** Sie stehen als Konstanten in `bewegungen.py`, `uhr_rekonstruktion.py` und `einsaetze.py`.
- **Kennzahlen eines Einsatzes** beruhen auf Stunden des Gesamtstroms (Stundenauflösung). Für Kennzahlen, Rauschboden und Verhaltensgruppen
  reicht das.
- **Die Messungen sind die Gegenprobe:** Sie bleiben ohne Zusammensetzen und zeigen, was die Verwaltung geliefert hat.

## Reproduktion

```sh
python3 -I einsaetze.py --auswertung _vorschau/auswertung.json --aggregat _vorschau-aggregat --cache .zwischenspeicher --jobs 8
python3 -I tools/einsatz_v85.py   # V85 der Einsätze gegen Messung und Verwaltung
```

`lokal_bauen.py` und der Workflow rufen es nach `dsd2csv.py` auf. Tests: `test_bewegungen.py`, `test_einsaetze.py`.
