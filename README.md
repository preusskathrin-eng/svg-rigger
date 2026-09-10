# SVG Rigger

SVG Rigger macht ein bereits brauchbares Vektorbild beweglich. Das Projekt
erstellt nicht mehr selbst eine möglichst kleine oder „geheilte“ SVG als
Hauptziel. Stattdessen verbindet es drei Arbeitsschritte:

1. optional den Hintergrund eines Rasterbildes entfernen;
2. ein Cutout-SVG mit VTracer erzeugen oder ein extern erzeugtes SVG übernehmen;
3. manuell gezeichnete Masken boolesch anwenden und die entstandenen Teile zu
   einem animierten SVG zusammensetzen.

Das frühere Projekt
[vector-healer](https://github.com/preusskathrin-eng/vector-healer) dokumentiert
die historische Rasterquantisierungs-/Topology-Healing-Pipeline. Diese Schritte
sind hier kein Bestandteil des Kernablaufs.

## Status

Der technische Grundablauf ist implementiert und mit einem kleinen
Zwei-Teile-Beispiel sowie der realen Rocky-Datei getestet. Das Repository
enthält Rockys Komplettfigur, die drei Inkscape-Clip-Pfade für Körper, Kopf und
linken Arm, die Schnittkonfiguration und lauffähige Kopf- und Arm-Animationen. Die
Bewegungsparameter sind ein technisch geprüfter Ausgangspunkt, noch keine
abschließende gestalterische Entscheidung.

VTracer `1.0.0a4` ist eine Vorabversion. Der Pin ist absichtlich exakt, bis ein
neuer Stand mit Rocky erneut visuell und strukturell geprüft wurde.

## Pipeline

```text
Rasterbild
  └─ 00 optional: Hintergrund entfernen
       └─ 01 VTracer: Watershed + Cutout + Spline
            └─ gutes Ausgangs-SVG
                 + manuell gezeichnete SVG-Masken
                      └─ 02 boolesche Teilung
                           └─ einzelne Körperteile
                                + Rig-Konfiguration/Pivots
                                     └─ 03 animiertes SVG
```

Ein mit der VTracer-App erzeugtes SVG kann direkt als Ausgangs-SVG für Schritt
02 verwendet werden. Die CLI-Vektorisierung ist kein Pflichtschritt.

## Rocky-VTracer-Preset

Die am 10. September 2026 übermittelten App-Einstellungen sind unter
`presets/rocky_actual_good_preset.json` versioniert:

| Bereich | Einstellung |
|---|---|
| Clustering | Watershed |
| Detail | 255 |
| Compositing | Cutout |
| Filter Speckle | 6 |
| Curve Fitting | Spline |
| Simplify | 2,5 |
| Path Precision | 0 |
| Max Colors | 60 |
| Fixed Palette | leer |

Der Screenshot zeigt im Feld „Fixed Palette“ nur den Platzhalter
`#112233, #445566`; diese Werte wurden nicht als echte Palette übernommen.

Der App-Lauf vektorisiert auch den Bildhintergrund. Soll er nicht Bestandteil
des SVG werden, muss er vor der Vektorisierung entfernt werden. Eine nachträgliche
Löschung anhand einer angenommenen Hintergrundfarbe wäre bei Cutout-Geometrie
nicht allgemein sicher und wird deshalb nicht automatisch vorgenommen.

Das Preset wurde mit dem vorhandenen Rocky-Rasterbild auch über die Python-API
reproduziert. Mit Hintergrund entstanden 368 Pfade/57 Füllwerte und 102.744
Bytes; mit der bereits freigestellten PNG 417 Pfade/56 Füllwerte und 106.548
Bytes. Beide Varianten waren in einem zweiten Lauf byteidentisch. Die
Freistellung spart in diesem Motiv also nicht automatisch Pfade oder Bytes,
entfernt aber die mitvektorisierten Boden-/Hintergrundflächen. Details und
Hashes stehen in `docs/VALIDATION.md`.

## Installation

Getestete Basis: Python 3.11 unter Windows.

```powershell
python -m venv .venv
& .venv/Scripts/Activate.ps1
python -m pip install -e .
```

Nur wenn die optionale Hintergrundentfernung verwendet werden soll:

```powershell
python -m pip install -e ".[background]"
```

Das von `rembg` verwendete Modell wird nicht im Repository gespeichert. Der
Download kann ungefähr 1 GB beanspruchen; das ist ein Speicher-/Downloadbedarf,
keine pauschale Voraussetzung für eine dedizierte GPU.

## Nutzung

### 00 – Hintergrund optional entfernen

```powershell
svg-rigger-remove-background input/rocky.png work/00_rocky_transparent.png
```

Die Ausgabe muss neu sein; vorhandene Dateien werden nicht überschrieben.
Fell, Schatten und halbtransparente Kanten müssen visuell kontrolliert werden.

### 01 – Vektorisieren

Mit dem voreingestellten Rocky-Preset:

```powershell
svg-rigger-vectorize `
  work/00_rocky_transparent.png `
  work/01_rocky_cutout.svg `
  --preset presets/rocky_actual_good_preset.json
```

Die Ausgabe der VTracer-App kann stattdessen direkt als
`work/01_rocky_cutout.svg` gespeichert werden.

### Manuelle Masken

Für jedes bewegliche Teil wird eine eigene SVG-Datei angelegt, beispielsweise:

```text
masks/
├── body.svg
├── head.svg
└── arm.svg
```

Eine Maskendatei enthält geschlossene, gefüllte Pfade im selben ViewBox-
Koordinatensystem wie das Ausgangs-SVG. Die Maskenfarbe ist beliebig. Nicht
geschlossene Linien, Text, Filter oder Rasterbilder werden nicht als
Maskengeometrie interpretiert.

Gelenkbereiche dürfen sich bewusst überlappen. Das verhindert beim Drehen
sichtbare Löcher; solche Überlappungen müssen in der späteren Z-Order berücksichtigt
werden.

### 02 – Teile boolesch ausschneiden

Eine `cut.json` beschreibt Quelle, Masken und optionale Subtraktionen:

```json
{
  "source_svg": "input/rocky_cutout.svg",
  "sample_step": 0.5,
  "precision": 2,
  "parts": [
    {"id": "body", "mask_svg": "masks/body.svg", "subtract": ["head"]},
    {"id": "head", "mask_svg": "masks/head.svg"},
    {"id": "arm", "mask_svg": "masks/arm.svg"}
  ]
}
```

`subtract` referenziert andere Part-IDs. Im Beispiel wird die Kopfmaske vor dem
Schnitt von der Körpermaske abgezogen.

```powershell
svg-rigger-cut cut.json work/parts
```

Die Ausgaben sind `body.svg`, `head.svg`, `arm.svg` und `cut-report.json`.
Vollständig innerhalb einer Maske liegende, transformfreie VTracer-Pfade werden
mit unverändertem `d` übernommen. Nur von einer Maskenkante geschnittene Pfade
werden für die Shapely-Operation abgetastet und polygonal ausgegeben. Der Report
weist beide Fälle getrennt aus.

### 03 – Rig und Animation bauen

Die Reihenfolge in `rig.json` ist die Zeichenreihenfolge von hinten nach vorn:

```json
{
  "title": "Rocky",
  "parts": [
    {"id": "body", "file": "work/parts/body.svg"},
    {
      "id": "arm",
      "file": "work/parts/arm.svg",
      "animation": {
        "type": "rotate",
        "pivot": [950, 430],
        "values": [-8, 16, -8],
        "duration": "1.4s",
        "repeat": "indefinite"
      }
    },
    {"id": "head", "file": "work/parts/head.svg"}
  ]
}
```

```powershell
svg-rigger-build rig.json work/rocky_animated.svg
svg-rigger-inspect work/parts/*.svg work/rocky_animated.svg
```

Unterstützt werden deklarative SVG-Transformationen vom Typ `rotate`,
`translate` und `scale`. `parent` kann eine andere Part-ID referenzieren; dann
erbt das Kind deren Transformation. Die Pivots müssen derzeit manuell im
ViewBox-Koordinatensystem bestimmt werden. Optional erweitert
`viewbox_padding` die ViewBox gleichmäßig auf allen vier Seiten, ohne die
Koordinaten oder Geometrie der Teile zu verändern. Das schafft Bewegungsraum
für Teile, die im Ausgangsbild dicht am Rand liegen.

## Minimales reproduzierbares Beispiel

```powershell
svg-rigger-cut examples/minimal/cut.json examples/minimal/work/parts
svg-rigger-build examples/minimal/rig.json .validation/minimal-animated.svg
```

```powershell
python -m unittest discover -s tests -p "test_*.py" -v
```

## Reales Rocky-Beispiel

Die bereitgestellte Inkscape-Datei enthält vier Gruppen mit jeweils 336
Quellpfaden: `complete`, `left_arm`, `body` und `head`. Die drei Teilegruppen
referenzieren ihre Masken als Clip-Pfade. `svg-rigger-cut` liest jetzt sowohl
die Quellgruppe als auch die Masken direkt aus dieser einen SVG:

```powershell
svg-rigger-cut examples/rocky/cut.json examples/rocky/work/parts
svg-rigger-build examples/rocky/rig.json .validation/rocky-rebuild.svg
```

| Teil | Ausgabepfade | Bézierpfade unverändert | an Maske polygonisiert |
|---|---:|---:|---:|
| Körper | 129 | 114 | 15 |
| Kopf | 204 | 142 | 62 |
| linker Arm | 39 | 18 | 21 |

Die Maskenunion deckt 99,99 % der sichtbaren Komplettfigur ab. Körper/Kopf und
Körper/Arm überlappen bewusst an den Gelenken; diese Flächen werden nicht
subtrahiert. Der Arm liegt entsprechend der gelieferten Inkscape-Z-Order hinter
dem Körper. Seine Ausgangsrotation und sein Drehpunkt wurden aus der
Teilegruppe übernommen.

<img src="examples/rocky/output/rocky_animated_preview.png" width="420" alt="Aus Masken geschnittener Rocky mit separat animierbarem Kopf und linkem Arm">

Das versionierte [animierte SVG](examples/rocky/output/rocky_animated.svg)
enthält 372 Pfade, 51 Füllwerte, drei Teilegruppen und zwei SMIL-Animationen.
Der linke Arm rotiert zwischen −5° und 8°, der Kopf langsamer zwischen −1,5°
und 1,5°. Für die Kopfbewegung wurde die ViewBox mit 20 Einheiten Rand von
`0 0 1254 1254` auf `-20 -20 1294 1294` erweitert. Zwei in Edge gerenderte
Extrempositionen zeigen weder abgeschnittene Haarspitzen noch abgeschnittene
Armflächen.

## Technische Grenzen

- Boolesche Operationen arbeiten auf abgetasteten Polygonen. An tatsächlichen
  Maskenschnitten gehen Bézierkurven verloren; ungeschnittene Pfade bleiben
  dagegen unverändert.
- Kleine `sample_step`-Werte erhöhen Genauigkeit, Laufzeit und Dateigröße.
- Ungültige Selbstüberschneidungen werden mit `buffer(0)` repariert. Dabei
  können sehr schmale Flächen verschwinden oder aufgeteilt werden.
- Die Farbattribute einfacher gefüllter Pfade bleiben erhalten. Gradienten,
  Muster, Filter, komplexes CSS, Clipping und Masken im Ausgangs-SVG werden
  noch nicht gleichwertig übernommen.
- Gruppen- und Pfadtransformationen werden geometrisch berücksichtigt;
  transformierte Quellpfade können nicht bytegleich erhalten bleiben.
- Gelenke, Drehpunkte, Ebenenreihenfolge und Bewegungsamplitude benötigen
  weiterhin visuelle und manuelle Entscheidungen.
- SMIL-Animationen müssen in den Zielbrowsern getestet werden. Für Umgebungen,
  die nur CSS- oder JavaScript-Animation erlauben, ist noch kein Exportmodus
  implementiert.
- Das Ergebnis ist nicht automatisch weboptimiert. Pfadzahl, Dateigröße,
  Antialiasing-Nähte und Rendering-Kosten bleiben separate Prüfpunkte.

## Repository-Struktur

```text
.
├── presets/                         # versionierte VTracer-Einstellungen
├── examples/minimal/                 # kleine Schnitt-/Animationsfixture
├── examples/rocky/                   # reale Inkscape-Datei, Konfiguration, Ergebnis
├── svg_rigger/
│   ├── background.py                 # optionale Vorstufe
│   ├── vectorize.py                  # VTracer-1-Aufruf
│   ├── geometry.py                   # Kurvenabtastung/Geometrie
│   ├── cut.py                        # maskenbasierter boolescher Schnitt
│   ├── rig.py                        # Zusammenbau und Animation
│   └── inspect.py                    # Strukturkennwerte
├── tests/
├── docs/VALIDATION.md
├── pyproject.toml
└── LICENSE
```
