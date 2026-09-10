# Validierungsprotokoll

Stand: 10. September 2026
Plattform: Windows, Python 3.11

## Geprüfte Bereiche

- Screenshot-Preset vollständig und ohne Platzhalterpalette übernommen;
- VTracer `1.0.0a4` mit Rocky mit und ohne Hintergrund ausgeführt;
- Wiederholung beider VTracer-Läufe und SHA-256-Vergleich;
- generischer boolescher Maskenschnitt mit Subtraktionsmaske;
- unveränderte Übernahme vollständig abgedeckter Bézierpfade;
- Polygonisierung nur tatsächlich geschnittener Pfade;
- Zusammenbau zweier Teile mit deklarativer Rotationsanimation;
- strukturelle Inspektion und Edge-Rendering des Ergebnis-SVG.

## Rocky-VTracer-Reproduktion

Verwendete Einstellungen:

```json
{
  "clustering": "watershed",
  "watershed_detail": 255,
  "hierarchical": "cutout",
  "filter_speckle": 6,
  "mode": "spline",
  "simplify": 2.5,
  "path_precision": 0,
  "max_colors": 60,
  "palette": null
}
```

| Eingabe | Ausgabe | Bytes | Pfade | Füllwerte | Befehle | `C`-Befehle |
|---|---|---:|---:|---:|---:|---:|
| ursprüngliches PNG mit Hintergrund | `with-background.svg` | 102.744 | 368 | 57 | 7.341 | 6.344 |
| freigestelltes RGBA-PNG | `transparent.svg` | 106.548 | 417 | 56 | 7.694 | 6.528 |

Referenzhashes:

| Datei | SHA-256 |
|---|---|
| Rocky-Eingabe | `3611D2D93E5B15D7E5038513B3D0E32BCEADE096F7153F5B81E17341706F7A7D` |
| freigestellte PNG | `B31CC924D1B3327A9C615840401B5C0716E0D7C4C86ABF711332C1B16420A34C` |
| SVG mit Hintergrund | `D11A45C0BE44178745A8D2B8E7DC1C07B2C3FAB8FF71E93319BE9E65B41F52F0` |
| SVG aus freigestellter PNG | `5BC4C1A3F3F510BF60AAAE93C4713E88F6CDD528B958B160E963EB1E523E5523` |

Der zweite Lauf erzeugte beide SVG-Hashes byteidentisch. Die generierten
Rocky-Dateien liegen absichtlich nur im ignorierten Verzeichnis `.validation`:
Das neue Repository beginnt fachlich beim vom Nutzer ausgewählten guten
Ausgangs-SVG; dieses soll nicht still durch eine lokal reproduzierte Variante
ersetzt werden.

Die Variante mit Hintergrund bewahrt weiße Bild- und Bodenflächen. Die
freigestellte Variante besitzt einen transparenten Außenbereich, enthält aber
mehr einzelne Pfade. Hintergrundentfernung ist deshalb eine semantische
Entscheidung und keine garantierte SVG-Komprimierung.

## Minimaler Masken-/Rig-Test

```powershell
python -m svg_rigger.cut `
  examples/minimal/cut.json `
  examples/minimal/work/parts

python -m svg_rigger.rig `
  examples/minimal/rig.json `
  .validation/minimal-animated.svg

python -m svg_rigger.inspect `
  examples/minimal/work/parts/body.svg `
  examples/minimal/work/parts/arm.svg `
  .validation/minimal-animated.svg
```

Ergebnisse:

- Quelle: 2 Pfade;
- Körper: 1 geschnittener/polygonisierter Pfad;
- Arm: 2 Pfade, davon ein vollständiger Bézierpfad bytegleich im `d` erhalten;
- animiertes SVG: 2 Gruppen, 3 Pfade, 2 Füllwerte, eine
  `animateTransform`-Rotation, 11.315 Bytes;
- Edge stellte die zusammengesetzten Teile erwartungsgemäß dar.

## Automatische Tests

```powershell
python -m compileall -q svg_rigger tests
python -m unittest discover -s tests -p "test_*.py" -v
```

Drei Tests liefen erfolgreich. Sie prüfen das vollständige Rocky-Preset,
Maskenschnitt/Subtraktion, Farberhalt, Kurvenerhalt und die erzeugte
Rotationsanimation.

## Noch nicht validiert

- die von der Projektinhaberin direkt aus der VTracer-App gespeicherte SVG;
- reale Rocky-Masken für Kopf, Körper, Arm und weitere bewegliche Teile;
- Gelenküberdeckungen, Pivots und Z-Order am realen Motiv;
- Animation des realen Rocky in mehreren Zielbrowsern;
- CSS- oder JavaScript-Ausgabe als Alternative zu SMIL;
- Gradient-, Filter-, Pattern-, Clip- und komplexe CSS-Eingaben.
