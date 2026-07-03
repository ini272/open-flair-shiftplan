# Einteilungslogik

Diese Datei beschreibt die aktuelle automatische Schichteinteilung in verständlicher Sprache.

## Grundidee

Der Planer ist ein heuristischer, schrittweiser Planer.

Das bedeutet:

- Er geht Schicht für Schicht durch.
- Für jede Schicht betrachtet er nur die aktuell passenden Personen oder Teams.
- Dann wählt er die im Moment beste Option nach festen Regeln aus.

Er sucht also **nicht** die mathematisch perfekte Gesamtlösung über alle Schichten auf einmal.
Für diese App ist das bewusst so gewählt, weil die Logik dadurch gut nachvollziehbar und schnell bleibt.

## Planungseinheiten

Der Planer arbeitet nicht nur mit Einzelpersonen.

Es gibt zwei Arten von Planungseinheiten:

- einzelne Personen
- ganze Teams

Teams werden als gemeinsame Einheit behandelt und nicht aufgeteilt.

## Harte Ausschlüsse

Bevor überhaupt gescored wird, fliegen Kandidaten raus, wenn eine dieser Bedingungen gilt:

- die Schicht ist für die Person oder ein Teammitglied als `nicht möglich` markiert
- das Team passt von der Größe nicht in die freie Kapazität der Schicht
- die Person oder das Team hätte eine Zeitüberschneidung mit einer schon zugeteilten Schicht
- eine Person in der Einheit hat bereits das Limit `max_shifts_per_user` erreicht
- eine Person ist unter 16 und die Schicht beginnt ab `20:00` oder liegt nach Mitternacht

Diese Regeln sind hart. Dagegen wird nie eingeplant.

| Bereich | Regel | Wirkung |
| --- | --- | --- |
| Verfügbarkeit | Slot ist abgewählt / Opt-out gesetzt | Kandidat fliegt raus |
| Kapazität | Person oder Team passt nicht in die freie Schichtkapazität | Kandidat fliegt raus |
| Zeitkonflikt | Überschneidung mit bereits zugeteilter Schicht | Kandidat fliegt raus |
| Maximalgrenze | `max_shifts_per_user` erreicht | Kandidat fliegt raus |
| U16 | Schicht startet ab `20:00` oder nach Mitternacht | Kandidat fliegt raus |

## Reihenfolge der Schichten

Die Schichten werden nicht zufällig abgearbeitet.

Vereinfacht gilt:

1. Donnerstag-, Freitag- und Samstagabend ab 20:00 zuerst
2. dann nach Tages- und Slot-Reihenfolge
3. knappe Schichten mit wenigen möglichen Kandidaten früher

Dadurch versucht der Planer zuerst die schwierigen Stellen zu lösen.

## Aktuelle Score-Werte

Die folgende Tabelle beschreibt die **konkreten Punktwerte**, die aktuell in den Score einfließen.

| Kriterium | Wert | Effekt |
| --- | ---: | --- |
| Bereits vergebene Schichten | `-30` pro Schicht | drückt Personen/Teams mit hoher Gesamtlast nach unten |
| Wenige verfügbare Slots | `+(10 - verfügbare Slots) * 3`, mindestens `0` | bevorzugt knappe, wenig flexible Einheiten |
| Neuer Einsatztag | `+34` | belohnt Verteilung über mehrere Festivaltage |
| Neuer Einsatztag bei mehreren möglichen Tagen | zusätzlich `+18` | verstärkt Tagesverteilung für flexible Einheiten |
| Schon auf diesem Tag, andere Tage noch offen | `-18` | bremst Ballungen auf einem Tag |
| Schon auf diesem Tag, keine anderen Tage mehr offen | `+4` | kleiner Ausgleich, wenn Tagesballung unvermeidlich ist |
| Bereits belegte Slots am selben Tag | `-8` pro Slot | bevorzugt weniger Schichten auf einem Tag |
| Genau zwei direkte Slots hintereinander | `+6` | kleine Belohnung für kompakte Blöcke |
| Mehr als zwei direkte Slots hintereinander | `-90` pro zusätzlichem Slot über 2 | vermeidet Dreier- oder längere Ketten |
| Ein-Slot-Lücke im Tagesmuster | `-45` | vermeidet unpraktische Pausen zwischen zwei Einsätzen |
| Prioritäts-Abendschicht ohne bisherige Abendschicht | `+55` | verteilt unbeliebte Abend-/Nachtzeiten fairer |
| Nur genau eine mögliche Prioritäts-Abendschicht | zusätzlich `+15` | schützt knappe Abendoptionen |
| Bereits vorhandene Prioritäts-Abendschichten | `-35` pro Abendschicht | verhindert, dass dieselben Leute alle Prime-Time-Slots bekommen |
| Standortpräferenz trifft | `+14` | weiche Bevorzugung von `Weinzelt` oder `Bierwagen` |
| Standortpräferenz trifft nicht | `-8` | kleiner Malus, aber keine harte Sperre |

## Hauptkriterien im Scoring

Wenn mehrere Kandidaten grundsätzlich möglich sind, bekommen sie Punkte oder Abzüge.

### 1. Faire Gesamtverteilung

Wer schon viele Schichten hat, wird unattraktiver.

- pro bereits vergebener Schicht gibt es deutlichen Abzug

Ziel:

- niemand soll unnötig viele Schichten bekommen, solange andere noch frei sind

### 2. Knappe Personen oder Teams bevorzugen

Wer nur wenige mögliche Slots hat, bekommt Bonus.

Ziel:

- wenig flexible Personen oder Teams sollen nicht am Ende übrig bleiben

### 3. Über Tage verteilen

Ein neuer Einsatztag ist besser als noch eine weitere Schicht auf einem Tag.

Ziel:

- Einsätze möglichst über mehrere Festivaltage verteilen

### 4. Nicht zu viele Schichten am selben Tag

Jede weitere Schicht am selben Tag kostet Punkte.

Ziel:

- Tagesballungen vermeiden

### 5. Direkt aufeinanderfolgende Schichten

Zwei direkte Slots hintereinander sind grundsätzlich erlaubt und sogar leicht bevorzugt.

Ziel:

- kleine zusammenhängende Blöcke können praktisch sein

### 6. Drei direkte Slots hintereinander

Drei hintereinander sollen vermieden werden, **wenn es eine Alternative gibt**.

Aktuelle Regel:

- wenn für die aktuelle Schicht mindestens eine andere passende Einheit ohne Dreierblock existiert, werden Einheiten mit entstehendem Dreierblock für diese Entscheidung aussortiert
- wenn es keine andere Möglichkeit gibt, bleibt der Dreierblock als Fallback erlaubt

Ziel:

- keine unnötig harten Marathon-Blöcke
- aber auch keine künstlich offen gelassenen Schichten

### 7. Ein-Slot-Lücken vermeiden

Muster wie:

- 14-16 arbeiten
- 16-18 frei
- 18-20 wieder arbeiten

bekommen Abzug.

Ziel:

- unpraktische Lücken im Tagesablauf vermeiden

### 8. Donnerstag-, Freitag- und Samstagabend fair verteilen

Späte Schichten an Donnerstag, Freitag und Samstag sind besonders sensibel.

Regel:

- wer noch keine solche Schicht hat, bekommt deutlichen Bonus
- wer schon mehrere solche Schichten hat, bekommt Abzug

Ziel:

- unbeliebtere Prime-Time-Schichten fair verteilen

### 9. Standortwunsch

`Weinzelt` oder `Bierwagen` ist eine **weiche Präferenz**.

Regel:

- passender Standort gibt Bonus
- unpassender Standort gibt kleinen Malus
- trotzdem bleibt eine Zuteilung dorthin möglich, wenn es sonst sinnvoll ist

Ziel:

- Wünsche berücksichtigen, ohne die Gesamtplanung zu blockieren

## Nicht direkt Score, aber trotzdem entscheidend

Ein paar Dinge beeinflussen die Auswahl, ohne als Punkte in `score_unit_for_shift(...)` zu stehen.

| Mechanik | Bedeutung |
| --- | --- |
| Schicht-Slots statt Einzelschichten | Parallele Schichten mit gleicher Uhrzeit werden zusammen betrachtet |
| Slot-Reihenfolge | Donnerstag-/Freitag-/Samstagabend zuerst, dann nach Slot-Reihenfolge und Knappheit |
| Standort-Reihenfolge innerhalb eines Parallel-Slots | Die Location mit mehr passend präferierenden Einheiten wird zuerst betrachtet |
| Dreierblock-Vorfilter | Wenn es Alternativen ohne entstehenden Dreierblock gibt, fliegen Kandidaten mit Dreierblock schon vor dem eigentlichen Score raus |
| Sortierung nach Score | Erst höherer Score, dann weniger bisherige Schichten, dann feste `sort_order` |
| Randomisierung | Kandidaten innerhalb eines kleinen Score-Fensters werden zufällig aus einer Top-Gruppe gewählt statt immer starr der erste |

## Aktuelles Randomisierungsfenster

Der Planer nutzt aktuell ein Fenster von `3.0` Score-Punkten.

Das heißt:

- wenn mehrere Kandidaten maximal `3.0` Punkte hinter dem besten Score liegen
- kommen sie alle in dieselbe Top-Gruppe
- daraus wird zufällig ausgewählt

Dadurch entstehen alternative, aber ähnlich gute Planvorschläge.

## Zufall bei fast gleich guten Kandidaten

Wenn mehrere Kandidaten fast gleich gut sind, wählt der Planer nicht immer denselben.

Stattdessen:

- die besten Kandidaten innerhalb eines kleinen Score-Fensters kommen in eine Top-Gruppe
- daraus wird zufällig ausgewählt

Ziel:

- wiederholtes `Planvorschlag erstellen` liefert sinnvolle Alternativen
- trotzdem bleibt die Qualität ähnlich

## Was der Planer bewusst nicht ist

Der Planer ist kein exakter Optimierer wie ein ILP- oder CP-SAT-Modell.

Das wäre theoretisch möglich, würde aber deutlich mehr Komplexität bedeuten:

- formale Zielfunktion
- Nebenbedingungen als mathematisches Modell
- höherer Pflegeaufwand
- schwerer für spontane Regeländerungen

Für diese Anwendung ist der aktuelle Ansatz fachlich vernünftig:

- nachvollziehbar
- pragmatisch
- schnell
- gut anpassbar

## Gesamtbewertung

Objektiv ist das eine solide Heuristik für einen kleinen bis mittleren Festival-Schichtplan.

Sie ist nicht akademisch optimal, aber sie ist auch kein wildes Sonderkonstrukt.
Viele reale Planungstools in diesem Größenbereich arbeiten zuerst genau mit solchen gewichteten Heuristiken, bevor man zu schwereren Optimierungsverfahren greift.

Der aktuelle Stand ist deshalb:

- fachlich plausibel
- technisch konsistent
- für eure App absolut vertretbar

Der wichtigste Punkt ist nur:

- harte Regeln klar von weichen Präferenzen trennen

Das ist im aktuellen Stand grundsätzlich sauber gelöst.
