# Verhaltensgruppen (Forschungsstand)

> Exploration, nicht Teil der Auswertung auf den Seiten. Eigene Berechnung, ohne Gewähr. Alle Zahlen stammen aus den Skripten in
> `tools/verhalten/` (numpy nötig) und lassen sich damit nachrechnen.

## Frage

Die bisherigen Gruppen (`gruppen.py`) sind angepasste Kurven: Sie beschreiben die Form der Geschwindigkeitsverteilung. Ob dahinter etwas steckt,
das sich wie eine eigene Gruppe *verhält*, sagt die Form nicht; die Begründung ist zirkulär, denn die Geschwindigkeit ist zugleich das, worüber die
Auswertung etwas aussagen will. Eine **Verhaltensgruppe** ist hier dagegen ein Teil des Verkehrs mit

1. einem festen Geschwindigkeitsprofil, das in allen Stunden gleich bleibt, und
2. einer eigenen Reaktion seiner Menge auf Tageszeit, Wochentag, Tageslicht, Regen, Temperatur, Wind, Schnee, Schulferien und Feiertage.

Ob es solche Gruppen gibt, entscheidet nicht die Anpassung an die Daten, sondern die **Vorhersage ungesehener Wochen**, und jeder Befund wird gegen
einen **Placebo-Durchgang** geprüft, in dem Wetter, Licht und Ferien um Wochen gegen die Fahrzeuge verschoben sind.

## Verfahren

- **Daten** (`stunden.py`): je Datei und Abschnitt (siehe [abschnitte.md](abschnitte.md), Ferien und Feiertage bei der Bruchsuche ausgenommen)
  eine Tabelle der vollständig aufgezeichneten Stunden mit nutzbarer Uhr: Fahrzeuge je 2-km/h-Klasse von 0 bis 90 km/h (alle Fahrzeuge,
  ohne Abzug des Rauschbodens) und je Stunde: Niederschlag der nächsten DWD-Station zur Messstelle (Stunde und Nachbarstunden), Tagesmittel und
  -minimum der Temperatur, Windspitze, Schnee, Sonnenhöhe an der Messstelle (Tag über 15°, tiefe Sonne 0–15°, Dämmerung −6–0°, Dunkelheit unter
  −6°; Wolken sind nicht erfasst), Wochentag, Stunde, Schulferien und Feiertage in NRW (`kalender.py`).
- **Modell** (`modell.py`), je Abschnitt mit mindestens 14 Tagen und 5.000 Fahrzeugen:
  λ[Stunde, Klasse] = Σₖ exp(X[Stunde] · βₖ) · Hₖ[Klasse].
  Hₖ ist das Geschwindigkeitsprofil der Gruppe k, βₖ ihre Reaktion: 72 Werte für Stunde × Tagtyp (Werktag, Samstag, Sonn- und Feiertag), je ein
  Wert für Dämmerung, tiefe Sonne, Dunkelheit, drei Regenklassen, „nach Regen“, Temperatur, Frost, Wind, Schnee, Schulferien, Feiertag und ein
  langsamer Trend. Angepasst mit EM-Schritten (Profile) und Poisson-Regression (Mengen). K = 1 heißt: eine einzige Verteilung, nur die Menge ändert
  sich.
- **Zahl der Gruppen:** Anpassung auf den geraden Wochen, Vorhersage der ungeraden und umgekehrt; gewählt wird die kleinste Zahl (bis 5), die bis
  auf 0,002 nats je Fahrzeug an die beste Vorhersage herankommt.
- **Vergleich innerhalb des Ortes:** Jede Nebengruppe wird mit der Hauptgruppe (größter Anteil) desselben Abschnitts verglichen. Ort, Stunden und
  Wetter sind dann gleich; was bleibt, ist der Unterschied im Verhalten. Über die Abschnitte wird mit einer Random-Effects-Metaanalyse
  (DerSimonian-Laird) gemittelt (`stadtweit.py`).
- **Placebo:** derselbe Durchgang mit Wetter um 37 Tage, Sonnenhöhe um 45 Tage und Ferien/Feiertagen um 29 Tage gegen die Stunden verschoben
  (`VERHALTEN_PLACEBO=1`). Tageszeit und Wochentag bleiben echt.

## Ergebnisse

119 Abschnitte aus 99 Dateien.

**1. Das Verhalten macht mehrere Gruppen nötig.**

| | echte Daten | Placebo |
|---|---|---|
| Abschnitte mit mehr als einer Gruppe | 74 von 119 (62 %) | 37 von 119 (31 %) |
| Vorhersagegewinn mit 2 Gruppen (Median, nats je Fahrzeug) | +0,0065 | −0,0176 |
| Abschnitte, in denen 2 Gruppen besser vorhersagen | 61 % | 33 % |

Mit echtem Wetter, Licht und Ferien sagen Modelle mit mehreren Gruppen ungesehene Wochen besser voraus; mit verschobenen nicht. Die Gruppen sind
also nicht nur eine bessere Beschreibung der Verteilung, sondern beschreiben unterschiedliches Verhalten.

**2. Positivkontrolle: Der Rauschboden findet sich selbst.** In 45 Abschnitten an 34 Standorten gibt es eine sehr langsame Gruppe (Modus im Median
8 km/h, Anteil 9 %). Gegenüber der Hauptgruppe am selben Ort ist sie bei 0,5–2 mm Regen 19-mal (95 %-Bereich 11–34), ab 2 mm 55-mal (30–102)
so häufig; 43 von 46 Gruppen einzeln deutlich. Zwischen 0 und 3 Uhr ist sie im Verhältnis zur Hauptgruppe 16- bis 35-mal so stark wie im
Tagesmittel: Sie hängt nicht am Verkehr. Im Placebo
verschwindet der Regeneffekt (Faktor 0,78). Das ist der verkehrsunabhängige Rauschboden mit dem Regenanteil ([rauschen.md](rauschen.md),
[wetter.md](wetter.md)), hier ohne jede Annahme über ihn gefunden. Das Verfahren erkennt also ein bekanntes Phänomen von selbst.

**3. Eine stadtweite „schnelle Gruppe“.** In 48 Abschnitten an 38 Standorten gibt es eine Gruppe, die schneller ist als die Hauptgruppe (Modus im
Median 41 km/h, Anteil 23 %; im Placebo nur 25 Abschnitte an 22 Standorten). Ihr Verhalten gegenüber der Hauptgruppe:

| | Faktor auf die Menge (95 %) | Placebo |
|---|---|---|
| Schulferien | 1,22 (1,11–1,33) | 0,89 |
| Regen ab 2 mm | 0,81 (0,73–0,91) | 0,99 |
| Regen 0,5–2 mm | 0,92 (0,87–0,98) | 1,00 |
| Schnee | 0,73 (0,65–0,84) | 1,01 |
| Dämmerung | 0,91 (0,85–0,97) | 1,04 |

Im Tagesgang ist sie zwischen 0 und 3 Uhr im Verhältnis zur Hauptgruppe etwa 6- bis 12-mal so stark wie im Tagesmittel, um 7 und 8 Uhr nur
0,4-mal (Median über die Abschnitte; die Tageszeit ist im Placebo nicht verschoben und deshalb dort ähnlich).
Sie ist also dann da, wenn die Straße frei ist (nachts, in den Ferien), und weniger, wenn sie nass oder glatt ist. Das Muster kehrt wieder:
Die Effekte der schnellen Gruppen verschiedener Abschnitte sind im Mittel mit 0,23 korreliert (Placebo −0,02). Es nimmt mit der Entfernung nicht
ab (unter 0,3 km 0,38, 0,3–2 km 0,25, 2–4 km 0,16, 4–15 km 0,25; Mantel-Test r = −0,04, p = 0,24): Es ist ein stadtweites Verhalten, kein
örtliches. Gibt es in einem Abschnitt eine schnelle Gruppe, gibt es sie meist auch in den anderen Abschnitten desselben Ordners (74 % gleich,
52 % bei Unabhängigkeit; Placebo 68 gegen 66 %).

Ob das eine Gruppe von *Menschen* ist oder eine *Lage* (freie Fahrt bei wenig Verkehr), trennt das Modell nicht: Beides erzeugt dasselbe Muster.
Die Verkehrsdichte als eigenes Merkmal wäre der nächste Test.

**4. Eine langsame, regenscheue Gruppe in Tempo-30-Straßen.** In 11 Abschnitten an 10 Standorten (alle Tempo 30) gibt es eine Gruppe mit Modus
um 21 km/h (12–28 km/h, Anteil im Median 30 %), die bei 0,5–2 mm Regen seltener wird: Faktor 0,77 (0,65–0,91), Placebo 0,99. Ab 2 mm Regen und für
die Temperatur ist der Effekt nicht gesichert (0,91 und 1,07). Im Placebo entstehen nur 3 solche Gruppen. Das passt zu Radfahrenden, die bei
Regen fernbleiben; mehr als ein Kandidat ist es nicht. Rennradfahrer lassen sich nicht abtrennen.

**Nicht gesichert:** Die geringere Häufigkeit der sehr langsamen Gruppe bei Wärme (Faktor 0,71) tritt im Placebo ebenso auf (0,65): Die
Jahreszeit steckt darin, nicht das Wetter. Gleiches gilt für ihren Ferieneffekt. Die Einzeltests je Gruppe sind zu optimistisch (auch im Placebo
sind viele Gruppen einzeln „deutlich“); belastbar sind nur die Metaanalyse über viele Abschnitte und der Vergleich mit dem Placebo.

**5. Verkehrsdichte als Merkmal** (`VERHALTEN_DICHTE=1`): Als weiteres Merkmal kommt die Zahl der Fahrzeuge ab dem halben Tempolimit in der
Stunde dazu (Logarithmus). Damit wird die Geschwindigkeit teilweise mit sich selbst verglichen; das ist gewollt, denn es trennt „wer fährt“
von „wie voll ist die Straße“.

- Mehr Abschnitte brauchen dann mehrere Gruppen (81 statt 74 von 119), und der Vorhersagegewinn mit zwei Gruppen verdoppelt sich (Median
  +0,0135 statt +0,0065 nats je Fahrzeug).
- **Rauschboden:** Die sehr langsame Gruppe wird bei 2,7-mal so viel Verkehr gegenüber der Hauptgruppe auf das 0,26-Fache seltener
  (0,21–0,33; 47 von 53 Gruppen einzeln deutlich). Das heißt: Ihre Menge hängt nicht vom Verkehr ab; genau das nimmt das Rauschbodenmodell
  an ([rauschen.md](rauschen.md)). Ihr Regeneffekt bleibt (Faktor 43 ab 2 mm).
- **Schnelle Gruppe:** Ihr Ferieneffekt (vorher 1,22) und ihr Regeneffekt (vorher 0,81) verschwinden (1,02 und 0,97), Schnee (0,73) und
  Dämmerung (0,91) bleiben. In den Ferien und bei Regen ändert sich also vor allem die Verkehrsmenge, und die schnelle Gruppe folgt ihr; Schnee und
  Dämmerung wirken darüber hinaus. Bei gleicher Stunde und gleichem Wochentag hängt ihr Anteil kaum von der Verkehrsmenge ab (Faktor 0,97); die
  nächtliche Häufung steckt in Stunde und Wochentag und lässt sich von der Verkehrsmenge mit diesen Daten nicht trennen. Ob die schnelle Gruppe
  eine Gruppe von Menschen oder die Lage „freie Straße“ ist, bleibt damit offen; die Verkehrsmenge erklärt einen Teil ihres Verhaltens, nicht alles.

**6. Rauschboden zweimal** (`rauschboden.py`): In 47 von 97 Dateien gibt es die sehr langsame Gruppe. In 32 Dateien, in denen `rauschen.py`
keinen Regenanteil belegen kann, findet das Verhaltensmodell sie mit einem Regenfaktor (ab 2 mm, gegenüber der Hauptgruppe) von im Median 64;
in 28 davon über 3. Wo beide Verfahren den Regenanteil schätzen (15 Dateien), ordnen sie die Dateien ähnlich (Korrelation der Logarithmen der
zusätzlichen Datensätze je Regenstunde 0,78), die Höhe unterscheidet sich aber um den Faktor 10 im Median (Quartile 2,5–32). Diese Rechnung ist
grob: Die Grundrate der Gruppe enthält Regenstunden, und ihr Profil reicht über die Obergrenze des Abzugs hinaus. Bevor die Gruppe den Abzug
ergänzt oder ersetzt, muss dieser Unterschied geklärt sein.

## Was daraus folgt

- **Gruppen lassen sich über Verhalten belegen.** Für die sehr langsame und die schnelle Gruppe ist das gelungen, für die langsame ein Anfang.
  Die bisherigen Verteilungsgruppen werden dadurch nicht bestätigt; sie sind eine andere Größe.
- **Rauschboden:** Zwei unabhängige Wege (Modell des Rauschbodens, Verhaltensgruppen) finden dieselbe Störung. Die Verhaltensgruppe könnte den
  Abzug später prüfen oder ersetzen, auch dort, wo das bisherige Modell keinen Regenanteil belegen kann.
- **Auswertungen ohne eine Gruppe:** Erst mit einer belegten Gruppe ist es sinnvoll, sie auszuschließen (etwa die langsame Gruppe bei der
  Einhaltungsquote) oder getrennt auszuwerten (etwa die schnelle Gruppe für die Gefährdung nachts).

## Grenzen

- Die Gruppen sind Teile des Verkehrs, keine Fahrzeuge: Kein einzelnes Fahrzeug wird zugeordnet.
- Die Hauptgruppe ist der Bezug; wo sie selbst Verhalten zeigt (etwa Pendler), stehen die Effekte der Nebengruppen relativ dazu.
- Die Sonnenhöhe misst das mögliche Licht, nicht das tatsächliche (Bewölkung, Straßenbeleuchtung fehlen).
- Die Gerätesperre (ein Fahrzeug je etwa 5 s) dünnt dichte Stunden aus; das trifft schnelle und langsame Gruppen gleich, verändert aber
  die Mengen in Spitzenstunden.
- Schwellen (14 Tage, 5.000 Fahrzeuge, 0,002 nats, Stabilität 0,9, Klassengrenzen 12/28 km/h) sind von Hand gewählt.

## Nachrechnen

```sh
NUMPY_PFAD=<Ordner mit numpy> python3 -I tools/verhalten/stunden.py --jobs 8     # braucht _vorschau/auswertung.json (lokal_bauen.py)
NUMPY_PFAD=... python3 -I tools/verhalten/modell.py --jobs 8                     # etwa 25 Minuten
NUMPY_PFAD=... VERHALTEN_PLACEBO=1 python3 -I tools/verhalten/modell.py --jobs 8
NUMPY_PFAD=... python3 -I tools/verhalten/stadtweit.py                            # Ergebnisse 1-4 (echte Daten)
NUMPY_PFAD=... python3 -I tools/verhalten/stadtweit.py modell_placebo.json        # Placebo
NUMPY_PFAD=... python3 -I tools/verhalten/entfernung.py [modell_placebo.json]     # Wiederkehr und Entfernung
NUMPY_PFAD=... python3 -I tools/verhalten/langsam.py                              # langsame Gruppen einzeln
NUMPY_PFAD=... VERHALTEN_DICHTE=1 python3 -I tools/verhalten/modell.py --jobs 8   # mit Verkehrsdichte -> modell_dichte.json
NUMPY_PFAD=... python3 -I tools/verhalten/stadtweit.py modell_dichte.json
NUMPY_PFAD=... python3 -I tools/verhalten/rauschboden.py                           # Vergleich mit rauschen.py
```

Zwischenergebnisse liegen in `_verhalten/` (nicht im Repository).
