# Zuverlässigkeit der Geräteuhren

> Eigene Einschätzung nach festen Regeln, nicht amtlich. Fehler im Verfahren und in der Auswertung können nicht
> ausgeschlossen werden (ohne Gewähr).

Die Auswertung nach Tageszeit steht und fällt mit der Geräteuhr. Die Uhren der Dialogdisplays sind
nicht verlässlich: Sie werden nie auf Sommerzeit umgestellt, manchmal nach einem Stromausfall auf den
2020-01-01 zurückgesetzt und teils um Stunden oder Tage verstellt. Dieses Dokument beschreibt, wie für
jeden zusammenhängenden Abschnitt einer Aufzeichnung entschieden wird, ob man den Zeitstempeln glauben darf.

Die Entscheidung trifft ein Skript (`uhr_belege.py`), nicht eine Person beim Draufschauen. Jedes Urteil
nennt die Belege, auf die es sich stützt. Die Ergebnisse stehen in `belege/uhr-bewertung.json`, lesbar
aufbereitet je Standortordner in `uhr-analyse.md` (neben den DSD-Dateien).

## Abschnitte

Eine Aufzeichnung wird in **Abschnitte** (Uhr-Segmente) zerlegt, siehe `docs/dsd-format.md`: Ein
Rückwärtssprung der Uhr um mehr als 2 Minuten oder eine Lücke von mehr als 3 Tagen beginnt einen neuen
Abschnitt, einzelne Ausreißer-Zeitstempel bilden keinen. Start und Ende eines Abschnitts sind Gerätezeit,
so wie sie in der CSV stehen.

## Urteile

| Urteil | Bedeutung |
|--------|-----------|
| `plausibel` | Die Zeitstempel sind glaubwürdig: mindestens zwei unabhängige Belege bestätigen sie, keiner widerspricht. |
| `eingeschraenkt` | Die Uhr ist womöglich verrutscht (Minuten bis Jahre) oder es liegen nicht genug Belege vor. |
| `unbrauchbar` | Die Zeitstempel sind Unsinn: unmögliches Datum, kein erkennbarer Tagesgang, oder zu kurz zum Rekonstruieren. |

Bei `eingeschraenkt` nennt das Feld `art`, woran es liegt:

- `unzureichend_belegt`: Nichts widerspricht den Zeitstempeln, aber weniger als zwei Belege bestätigen sie.
  Typisch für Straßen mit schwachem Wochenmuster. Diese Abschnitte sind vermutlich in Ordnung, nur nicht
  belegbar.
- `widerspruch`: Mindestens ein Beleg widerspricht, etwa ein um Stunden verschobener Tagesgang.
- `zurueckgesetzt`: Die Uhr wurde nach einem Stromausfall auf das Standarddatum 2020-01-01 12:00 gesetzt.
  Die Uhr lief danach gleichmäßig weiter, relative Zeiten sind also nutzbar. Datum, Wochentag und Uhrzeit
  müssen rekonstruiert werden.

### Urteil für eine ganze Datei

Die Detailseiten fassen die Abschnitte einer Datei zu einem Urteil zusammen (`gesamturteil()` in `uhr_belege.py`,
Schwellen `gesamt_plausibel_min` und `gesamt_unbrauchbar_min`), gewichtet nach Fahrzeugen: `plausibel`, wenn mindestens
99 % der Fahrzeuge in plausiblen Abschnitten liegen, `unbrauchbar`, wenn mindestens die Hälfte in unbrauchbaren liegt,
sonst `eingeschraenkt`. Bei den bisherigen Dateien ist das bei 71 plausibel, bei 36 eingeschränkt und bei 1 unbrauchbar (eine weitere
Datei enthält keine Fahrzeuge).

Nicht verwechseln mit der **Nutzbarkeit** der Zeitstempel in `dsd2csv.py` (`uhr.nutzbarkeit`, siehe
[dsd-format.md](dsd-format.md)): Sie prüft nur formal, ob Datum, Reset und Sprünge die Zeit unbrauchbar machen, und
steuert, welche Fahrzeuge in die Zeitscheiben (Nacht, Vormittag, Nachmittag, Abend, Schulweg) eingehen. Sie belegt nicht, dass die Uhrzeit stimmt. Dafür
ist dieses Urteil da.

## Belege

Jeder Beleg ist `bestaetigt`, `widerspricht` oder `offen` (nicht prüfbar). Mit Ausnahme des Datums zählen vier
Belege als unabhängig und für `plausibel`:

**Datum.** Das Datum liegt zwischen 2020 und 2030, ist nicht das Standarddatum und springt nicht um mehr als
einen Tag zurück. Ein unmögliches Datum macht den Abschnitt `unbrauchbar`.

**Wochenrhythmus.** Verkehr hat ein Wochenmuster: Sonntag ist am schwächsten, Samstag danach. Für jeden Abschnitt
mit mindestens 21 vollen Tagen wird die Woche (mittlere Fahrzeuge je Wochentag) mit einer typischen Woche
verglichen, in allen sieben Drehungen. Passt die unverschobene Woche mit Korrelation ab 0,75 und klarem Abstand
(0,25) zur zweitbesten Drehung, ist der Beleg bestätigt. Passt eine verschobene Woche, widerspricht er, und die
Drehung nennt den Versatz des Datums in Tagen (modulo 7). Die typische Woche wird aus den Abschnitten berechnet,
deren Wochenmuster eindeutig stimmt (aktuell 71 Abschnitte); sie ergibt Mo bis So = 1,04 1,06 1,08 1,06 1,09 0,94
0,72. Ein Abschnitt wird nie mit sich selbst verglichen.

**Tagesgang.** Der Werktags-Tagesgang (Viertelstunden, mindestens 5 Werktage und 3000 Fahrzeuge) wird mit dem
typischen Tagesgang der Referenzabschnitte verglichen, über alle möglichen Verschiebungen von −12 bis +12
Stunden. Bestätigt bei höchstens ±60 Minuten Verschiebung und Korrelation ab 0,9. Widerspricht bei ±90 Minuten
oder mehr oder bei einer Korrelation unter 0,5 (kein erkennbarer Tagesgang). Positive Werte heißen: Der Verkehr
tritt in Gerätezeit später auf, die Uhr geht vor. War das Gerät nicht lückenlos in Betrieb (Heartbeat-Abdeckung
unter 80 %), ist der Tagesgang abgeschnitten und der Beleg `offen`.

**Zeitumstellung.** Der Verkehr folgt der Ortszeit, die Geräteuhr nicht. In Gerätezeit verschiebt sich der
Tagesgang deshalb genau am Tag der amtlichen Zeitumstellung um eine Stunde. Zwei Prüfungen, für Abschnitte
mit mindestens 21 Tagen vor und nach dem Stichtag:

- *Anker:* An welchem Gerätetag springt der Tagesgang? Liegt der Sprung höchstens 2 Tage neben dem amtlichen
  Umstellungstag (und passen mindestens 80 % der Tage dazu), ist das Datum der Uhr auf den Tag genau verankert.
  Bei den bisher 8 prüfbaren Abschnitten lag der Sprung höchstens einen Tag neben dem amtlichen Tag.
- *Restversatz:* Nach der Sommerzeit-Korrektur dürfen sich Tagesgang vor und nach dem Stichtag um höchstens
  30 Minuten unterscheiden. Ab 45 Minuten widerspricht der Beleg (Ferien, Baustelle oder verstellte Uhr).

**Mitteilungen der Verwaltung.** Die Mitteilungen aus dem Ratsinformationssystem der Stadt Neuss nennen Orte und
Erfassungszeiträume. Der Beleg ist bestätigt, wenn der Ortsname der Messstelle im Dokument vorkommt und ein
genannter Zeitraum zum Abschnitt passt (der Abschnitt liegt innerhalb, und Beginn oder Ende stimmt auf den Tag
überein, Toleranz 1 Tag). Er widerspricht nie, weil die Zuordnung nur über den Namen läuft: Die Ruhrstraße
gibt es dreimal, die Villestraße für zwei Fahrtrichtungen. Die Dokumente stammen aus
`tools/ris_sammeln.py` und `tools/ris_auswerten.py`, die Auswertung steht in `belege/ris.json`.
Die Mitteilungen sind eine vom Gerät unabhängige Datumsquelle, ihre Zahlen (V85 usw.) stammen aber vermutlich
aus denselben DSD-Daten und sind kein unabhängiger Beleg für Messwerte.

**Kontinuität** wird nur berichtet (Heartbeat-Abdeckung, Uhrsprünge), sie geht nicht ins Urteil ein.

## Wie weit die Belege reichen

- Der Wochenrhythmus belegt den **Wochentag** (modulo 7), nicht den Tag. Eine um genau 7 oder 14 Tage
  verstellte Uhr fällt dadurch nicht auf.
- Der Tagesgang belegt die **Tageszeit nur auf etwa ±1 Stunde**. Eine schon beim Stellen um 30 Minuten falsche Uhr
  ist nicht erkennbar. Straßen mit untypischem Verkehr (z. B. 20er-Zone in einer Wohnstraße) weichen vom
  Referenzverlauf ab und fallen auf `eingeschraenkt`, obwohl ihre Uhr stimmen kann.
- Den Tag exakt belegen nur die Zeitumstellung (nur Abschnitte, die eine Umstellung überspannen) und die
  Mitteilungen der Verwaltung (bei 27 von 105 Dateien mit mindestens 2000 Fahrzeugen).
- Die typische Woche und der typische Tagesgang entstehen aus denselben Daten. Ein Fehler, der fast alle
  Geräte gleich betrifft, bliebe unentdeckt. Dagegen spricht, dass der Wochenrhythmus mit dem Kalender
  übereinstimmt (Sonntag am schwächsten) und die Sprünge an der Zeitumstellung am amtlichen Tag liegen.
- Die Mitteilungen nennen Zeiträume nur für einen Teil der Messungen. Bei den übrigen Dateien bleibt dieser
  Beleg `offen`.

## Schätzungen

Bei Abschnitten, deren Wochenmuster oder Tagesgang verschoben ist, steht unter `schaetzung`, um wie viele Tage
(`wochentag_versatz_tage`) und Minuten (`tageszeit_abweichung_min`) die Uhr danebenliegt. Diese Werte werden
**nicht angewendet**. Sie sind Ansatzpunkte, um zurückgesetzte Uhren zu rekonstruieren: Der Wochentag-Versatz
sagt, um wie viele Tage das Etikett der Uhr vom wahren Tag abweicht, die Tageszeit-Abweichung, wie weit die
Uhr in Stunden daneben liegt. Bei Abschnitten, die am 2020-01-01 beginnen, läuft die Uhr gleichmäßig und der
Wochenrhythmus ist erkennbar, bei einigen aber um einen Tag verschoben. Ob und wann diese Daten tatsächlich
erhoben wurden, ist damit noch nicht geklärt.

## Reproduktion

```sh
# Mitteilungen aus dem Ratsinformationssystem holen (Netz, ca. 5 Minuten) und auswerten
python3 -I tools/ris_sammeln.py ris_roh
PYPDF_PFAD=<Ordner mit pypdf> python3 -I tools/ris_auswerten.py ris_roh . belege/ris.json

# Urteile berechnen: belege/uhr-bewertung.json und <Standortordner>/uhr-analyse.md
python3 -I uhr_belege.py .
```

`ris_roh/` steht nicht im Repository. pypdf ist nur für `ris_auswerten.py` nötig. `uhr_belege.py` selbst
benötigt nur die Standardbibliothek. Alle Schwellen stehen in `SCHWELLEN` in `uhr_belege.py`, die Tests in
`test_uhr_belege.py`.
