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

Fünf Tests liefen erfolgreich. Sie prüfen das vollständige Rocky-Preset,
Maskenschnitt/Subtraktion, Farberhalt, Kurvenerhalt und die erzeugte
Rotationsanimation. Der reale Rocky-Test prüft zusätzlich Quellhash und die
erwarteten Pfad-/Kurvenerhaltzahlen aller drei Teile.

## Reale kombinierte Rocky-Datei

Quelle: `examples/rocky/input/rocky_and_his_parts.svg`
SHA-256: `9B46C0F098DC22BED65E88CBF16AA5BD55FBEAF86090EDE0068236FCB67E2E8E`

Die in das Repository kopierte Datei ist byteidentisch zur bereitgestellten
lokalen Quelldatei. Die Quelle selbst wurde nicht verändert.

| Element | Inhalt | Clip | Ausgangstransformation |
|---|---:|---|---|
| `complete` | 336 Pfade | keiner | keine |
| `left_arm` | 336 Pfade | `clipPath1011` | `rotate(-2.8823215, 859.58197, 617.32087)` |
| `body` | 336 Pfade | `clipPath1687` | keine |
| `head` | 336 Pfade | `clipPath673` | `rotate(0.01718731, 658.19661, 476.14514)` |

Maskenabdeckung auf der Vereinigung der 336 Komplettpfade, bei einer
Analyse-Schrittweite von 0,75:

| Maske | Schnittfläche mit Motiv |
|---|---:|
| Körper | 464.845,91 |
| Kopf | 254.786,73 |
| linker Arm | 69.444,52 |
| Körper/Kopf-Überlappung | 11.009,86 |
| Körper/Arm-Überlappung | 10.259,63 |
| Kopf/Arm-Überlappung | 0,00 |

Die Maskenunion deckt 767.807,67 von 767.883,05 Flächeneinheiten ab
(99,990 %). 75,38 Einheiten liegen außerhalb der Maskenunion; in der
1254×1254-Edge-Gesamtansicht war daraus kein fehlendes Detail erkennbar.

Schnittergebnisse mit `sample_step=0.5`, `precision=2`:

| Teil | Bytes | Pfade | Füllwerte | unveränderte Kurvenpfade | geschnitten/polygonisiert |
|---|---:|---:|---:|---:|---:|
| Körper | 129.725 | 129 | 34 | 114 | 15 |
| Kopf | 458.422 | 204 | 51 | 142 | 62 |
| linker Arm | 179.699 | 39 | 21 | 18 | 21 |

Das Ergebnis `examples/rocky/output/rocky_animated.svg` hat 769.260 Bytes,
372 Pfade, 51 Füllwerte, drei Gruppen sowie je eine Rotation für Kopf und Arm.
Die optionale Rig-Einstellung `viewbox_padding: 20` erweitert die ViewBox von
`0 0 1254 1254` auf `-20 -20 1294 1294`, ohne Teilekoordinaten zu verändern.
Damit bleibt die Kopfbewegung von ±1,5° einschließlich der oberen Haarspitzen
sichtbar. Der Arm wurde hinter dem Körper einsortiert, entsprechend der
gelieferten Inkscape-Z-Order.

SHA-256:

- animiertes SVG:
  `CDFE18616502B1DFD030C33466A9A91F2905F327D520E9F0A0C3DE4D62168047`
- Vorschau-PNG:
  `9B18599D1C3040B1951FB47CDF2908B5895FA362778AC2DDBF0A78E8BA8F094D`
- animierte GitHub-Vorschau (GIF):
  `6C5894FD721357F5E202B22AFFEB0EDD6E91531559506EC6A9724302E1E688FE`

Zwei Headless-Edge-Frames bei 100 ms und 1.600 ms unterschieden sich in 127.308
Pixeln. Die Differenz-Bounding-Box `(279, 24)–(1091, 744)` umfasst die erwarteten
Kopf- und Armbereiche. Beide gerenderten Positionen bleiben vollständig in der
erweiterten ViewBox sichtbar; der Körper bleibt statisch.

Die GitHub-Vorschau besteht aus 20 in Edge gerenderten Frames bei 480 × 480
Pixeln, 160 ms pro Frame und 3,2 Sekunden Schleifendauer. Sie enthält 20
unterschiedliche Frames und ist 1.045.434 Bytes groß. Kopf- und Armlaufzeit
wurden auf 3,2 beziehungsweise 1,6 Sekunden synchronisiert, damit der GIF-Loop
ohne Zeitsprung wieder am Anfang anschließt.

## Noch nicht validiert

- die Animation des realen Rocky außerhalb von Edge;
- gestalterische Freigabe von Drehpunkt, Amplitude und Geschwindigkeit;
- weitere bewegliche Teile außer Kopf, Körper und linkem Arm;
- CSS- oder JavaScript-Ausgabe als Alternative zu SMIL;
- Gradient-, Filter-, Pattern-, Clip- und komplexe CSS-Eingaben.
