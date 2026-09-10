"""Step 01: create a cutout/spline SVG with the tested VTracer 1 preset."""

import argparse
import importlib.metadata
import json
from pathlib import Path


DEFAULT_PRESET = {
    "clustering": "watershed",
    "watershed_detail": 255,
    "hierarchical": "cutout",
    "filter_speckle": 6,
    "mode": "spline",
    "simplify": 2.5,
    "path_precision": 0,
    "max_colors": 60,
    "palette": None,
}


def load_preset(path=None):
    if path is None:
        return dict(DEFAULT_PRESET)
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    config = data.get("vtracer", data)
    unknown = set(config) - set(DEFAULT_PRESET)
    if unknown:
        raise ValueError(f"unsupported preset keys: {', '.join(sorted(unknown))}")
    result = dict(DEFAULT_PRESET)
    result.update(config)
    return result


def vectorize(input_path, output_path, preset_path=None):
    import vtracer

    input_path = Path(input_path)
    output_path = Path(output_path)
    if not input_path.is_file():
        raise FileNotFoundError(f"input image not found: {input_path}")
    if output_path.exists():
        raise FileExistsError(f"refusing to overwrite existing output: {output_path}")

    version = importlib.metadata.version("vtracer")
    if not version.startswith("1.0.0"):
        raise RuntimeError(f"this preset requires VTracer 1.0; found {version}")

    settings = load_preset(preset_path)
    config = vtracer.Config(**settings)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    config.convert_file(str(input_path), str(output_path))
    return {"output": str(output_path), "vtracer": version, "settings": settings}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input_image", help="Raster input; transparent PNG recommended")
    parser.add_argument("output_svg", help="New SVG output")
    parser.add_argument("--preset", help="JSON preset; defaults to the Rocky settings")
    args = parser.parse_args()
    try:
        report = vectorize(args.input_image, args.output_svg, args.preset)
    except (FileNotFoundError, FileExistsError, RuntimeError, ValueError) as exc:
        parser.error(str(exc))
    print(f"[01] VTracer {report['vtracer']}: {report['output']}")
    print(json.dumps(report["settings"], indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()

