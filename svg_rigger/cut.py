"""Step 02: cut a source SVG into independently movable parts using SVG masks."""

import argparse
import json
import re
import xml.etree.ElementTree as ET
from pathlib import Path

from .geometry import (
    SVG_NS,
    geometry_to_d,
    load_mask,
    load_mask_element,
    load_path_records,
    repair,
    svg_canvas_attributes,
)


SAFE_ID = re.compile(r"^[A-Za-z_][A-Za-z0-9_.-]*$")


def resolve(base, value):
    path = Path(value)
    return path if path.is_absolute() else (base / path).resolve()


def load_manifest(path):
    manifest_path = Path(path).resolve()
    data = json.loads(manifest_path.read_text(encoding="utf-8"))
    parts = data.get("parts")
    if not isinstance(parts, list) or not parts:
        raise ValueError("manifest must contain a non-empty 'parts' list")
    identifiers = [item.get("id") for item in parts]
    if any(not value or not SAFE_ID.match(value) for value in identifiers):
        raise ValueError("every part needs a safe XML id")
    if len(set(identifiers)) != len(identifiers):
        raise ValueError("part ids must be unique")
    return manifest_path, data


def write_part(output_path, canvas, records):
    ET.register_namespace("", SVG_NS)
    root = ET.Element(f"{{{SVG_NS}}}svg", canvas)
    for record in records:
        attributes = {
            "d": record["d"],
            "fill": record["fill"],
            "fill-rule": record.get("fill_rule", "evenodd"),
        }
        if record.get("opacity"):
            attributes["opacity"] = record["opacity"]
        if record.get("fill_opacity"):
            attributes["fill-opacity"] = record["fill_opacity"]
        ET.SubElement(root, f"{{{SVG_NS}}}path", attributes)
    tree = ET.ElementTree(root)
    ET.indent(tree, space="  ")
    tree.write(output_path, encoding="utf-8", xml_declaration=True)


def cut_parts(manifest_path, output_dir):
    manifest_path, manifest = load_manifest(manifest_path)
    base = manifest_path.parent
    source_path = resolve(base, manifest["source_svg"])
    sample_step = float(manifest.get("sample_step", 0.5))
    precision = int(manifest.get("precision", 2))
    if sample_step <= 0 or precision < 0 or precision > 8:
        raise ValueError("sample_step must be positive and precision between 0 and 8")

    output_dir = Path(output_dir)
    if output_dir.exists() and any(output_dir.iterdir()):
        raise FileExistsError(f"output directory must be new or empty: {output_dir}")
    output_dir.mkdir(parents=True, exist_ok=True)

    source_root, source_records, source_skipped = load_path_records(
        source_path,
        sample_step,
        element_id=manifest.get("source_group"),
    )
    if not source_records:
        raise ValueError(f"source SVG contains no usable paths: {source_path}")

    masks = {}
    mask_reports = {}
    for part in manifest["parts"]:
        if "mask_svg" in part and "mask_clip_id" in part:
            raise ValueError(
                f"part {part['id']!r} must use either mask_svg or mask_clip_id"
            )
        if "mask_clip_id" in part:
            masks[part["id"]], mask_reports[part["id"]] = load_mask_element(
                source_path,
                part["mask_clip_id"],
                sample_step,
            )
        elif "mask_svg" in part:
            mask_path = resolve(base, part["mask_svg"])
            masks[part["id"]], mask_reports[part["id"]] = load_mask(
                mask_path, sample_step
            )
        else:
            raise ValueError(
                f"part {part['id']!r} needs mask_svg or mask_clip_id"
            )

    canvas = svg_canvas_attributes(source_root)
    report = {
        "source_svg": str(source_path),
        "source_group": manifest.get("source_group"),
        "source_paths": len(source_records),
        "source_paths_skipped": source_skipped,
        "sample_step": sample_step,
        "precision": precision,
        "parts": [],
    }

    for part in manifest["parts"]:
        part_id = part["id"]
        clip = masks[part_id]
        for subtract_id in part.get("subtract", []):
            if subtract_id not in masks:
                raise ValueError(
                    f"part {part_id!r} subtracts unknown mask {subtract_id!r}"
                )
            clip = repair(clip.difference(masks[subtract_id]))
            if clip is None:
                raise ValueError(f"part {part_id!r} became empty after subtraction")

        output_records = []
        preserved = 0
        clipped = 0
        removed = 0
        for source in source_records:
            geometry = source["geometry"]
            if not geometry.intersects(clip):
                removed += 1
                continue
            if source["matrix_identity"] and clip.covers(geometry):
                output_records.append(dict(source))
                preserved += 1
                continue
            intersection = repair(geometry.intersection(clip))
            if intersection is None:
                removed += 1
                continue
            path_data = geometry_to_d(intersection, precision)
            if not path_data:
                removed += 1
                continue
            output_records.append(
                {
                    "d": path_data,
                    "fill": source["fill"],
                    "fill_rule": "evenodd",
                    "opacity": source.get("opacity"),
                    "fill_opacity": source.get("fill_opacity"),
                }
            )
            clipped += 1

        output_path = output_dir / f"{part_id}.svg"
        write_part(output_path, canvas, output_records)
        report["parts"].append(
            {
                "id": part_id,
                "file": output_path.name,
                "mask": mask_reports[part_id],
                "subtract": part.get("subtract", []),
                "output_paths": len(output_records),
                "curves_preserved_unchanged": preserved,
                "paths_clipped_and_polygonized": clipped,
                "source_paths_outside_mask": removed,
                "bytes": output_path.stat().st_size,
            }
        )

    report_path = output_dir / "cut-report.json"
    report_path.write_text(
        json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("manifest", help="JSON cut manifest")
    parser.add_argument("output_dir", help="New or empty part output directory")
    args = parser.parse_args()
    try:
        report = cut_parts(args.manifest, args.output_dir)
    except (FileNotFoundError, FileExistsError, KeyError, ValueError) as exc:
        parser.error(str(exc))
    print(f"[02] Source paths: {report['source_paths']}")
    for part in report["parts"]:
        print(
            f"[02] {part['id']}: {part['output_paths']} paths; "
            f"{part['curves_preserved_unchanged']} unchanged, "
            f"{part['paths_clipped_and_polygonized']} clipped"
        )


if __name__ == "__main__":
    main()
