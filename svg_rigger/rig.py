"""Step 03: assemble cut part SVGs and add declarative SVG animations."""

import argparse
import copy
import json
import re
import xml.etree.ElementTree as ET
from pathlib import Path

from .geometry import SVG_NS, local_name, svg_canvas_attributes


SAFE_ID = re.compile(r"^[A-Za-z_][A-Za-z0-9_.-]*$")


def resolve(base, value):
    path = Path(value)
    return path if path.is_absolute() else (base / path).resolve()


def animation_attributes(animation):
    kind = animation.get("type")
    values = animation.get("values")
    if kind not in {"rotate", "translate", "scale"}:
        raise ValueError(f"unsupported animation type: {kind!r}")
    if not isinstance(values, list) or len(values) < 2:
        raise ValueError("animation values must contain at least two entries")

    if kind == "rotate":
        pivot = animation.get("pivot")
        if not isinstance(pivot, list) or len(pivot) != 2:
            raise ValueError("rotate animation requires pivot: [x, y]")
        rendered_values = ";".join(
            f"{float(value):g} {float(pivot[0]):g} {float(pivot[1]):g}"
            for value in values
        )
    elif kind == "translate":
        if any(not isinstance(value, list) or len(value) != 2 for value in values):
            raise ValueError("translate values must be [x, y] pairs")
        rendered_values = ";".join(
            f"{float(value[0]):g} {float(value[1]):g}" for value in values
        )
    else:
        rendered = []
        for value in values:
            if isinstance(value, list):
                if len(value) not in {1, 2}:
                    raise ValueError("scale values must contain one or two numbers")
                rendered.append(" ".join(f"{float(item):g}" for item in value))
            else:
                rendered.append(f"{float(value):g}")
        rendered_values = ";".join(rendered)

    attributes = {
        "attributeName": "transform",
        "attributeType": "XML",
        "type": kind,
        "values": rendered_values,
        "dur": str(animation.get("duration", "1s")),
        "repeatCount": str(animation.get("repeat", "indefinite")),
        "additive": "sum",
    }
    for source, target in (
        ("begin", "begin"),
        ("key_times", "keyTimes"),
        ("calc_mode", "calcMode"),
        ("key_splines", "keySplines"),
    ):
        if source in animation:
            value = animation[source]
            attributes[target] = ";".join(map(str, value)) if isinstance(value, list) else str(value)
    return attributes


def assert_acyclic(parts):
    parents = {item["id"]: item.get("parent") for item in parts}
    for identifier, parent in parents.items():
        if parent is not None and parent not in parents:
            raise ValueError(f"part {identifier!r} has unknown parent {parent!r}")
        seen = set()
        current = identifier
        while current is not None:
            if current in seen:
                raise ValueError(f"cycle in rig hierarchy at {identifier!r}")
            seen.add(current)
            current = parents[current]


def build_rig(config_path, output_path):
    config_path = Path(config_path).resolve()
    base = config_path.parent
    config = json.loads(config_path.read_text(encoding="utf-8"))
    parts = config.get("parts")
    if not isinstance(parts, list) or not parts:
        raise ValueError("rig config must contain a non-empty 'parts' list")
    identifiers = [item.get("id") for item in parts]
    if any(not value or not SAFE_ID.match(value) for value in identifiers):
        raise ValueError("every part needs a safe XML id")
    if len(identifiers) != len(set(identifiers)):
        raise ValueError("part ids must be unique")
    assert_acyclic(parts)

    output_path = Path(output_path)
    if output_path.exists():
        raise FileExistsError(f"refusing to overwrite existing output: {output_path}")

    loaded = []
    canvas = None
    for part in parts:
        part_path = resolve(base, part["file"])
        part_root = ET.parse(part_path).getroot()
        part_canvas = svg_canvas_attributes(part_root)
        comparable = {key: part_canvas.get(key) for key in ("viewBox", "width", "height")}
        if canvas is None:
            canvas = part_canvas
            expected_canvas = comparable
        elif comparable != expected_canvas:
            raise ValueError(f"part canvas differs from first part: {part_path}")
        unsupported = [
            local_name(child.tag)
            for child in list(part_root)
            if local_name(child.tag) != "path"
        ]
        if unsupported:
            raise ValueError(
                f"part {part_path} contains unsupported top-level elements: "
                + ", ".join(sorted(set(unsupported)))
            )
        loaded.append((part, part_path, part_root))

    ET.register_namespace("", SVG_NS)
    root = ET.Element(f"{{{SVG_NS}}}svg", canvas)
    if config.get("title"):
        ET.SubElement(root, f"{{{SVG_NS}}}title").text = str(config["title"])
    if config.get("description"):
        ET.SubElement(root, f"{{{SVG_NS}}}desc").text = str(config["description"])

    groups = {}
    for part, _, part_root in loaded:
        attributes = {"id": part["id"]}
        if part.get("transform"):
            attributes["transform"] = str(part["transform"])
        group = ET.Element(f"{{{SVG_NS}}}g", attributes)
        for child in list(part_root):
            group.append(copy.deepcopy(child))
        if part.get("animation"):
            animation = ET.Element(
                f"{{{SVG_NS}}}animateTransform",
                animation_attributes(part["animation"]),
            )
            group.insert(0, animation)
        groups[part["id"]] = group

    for part in parts:
        group = groups[part["id"]]
        parent = part.get("parent")
        (groups[parent] if parent else root).append(group)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    tree = ET.ElementTree(root)
    ET.indent(tree, space="  ")
    tree.write(output_path, encoding="utf-8", xml_declaration=True)
    return {
        "output": str(output_path),
        "parts": len(parts),
        "animations": sum(bool(item.get("animation")) for item in parts),
        "bytes": output_path.stat().st_size,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("config", help="Rig JSON configuration")
    parser.add_argument("output_svg", help="New animated SVG")
    args = parser.parse_args()
    try:
        report = build_rig(args.config, args.output_svg)
    except (FileNotFoundError, FileExistsError, KeyError, ValueError) as exc:
        parser.error(str(exc))
    print(
        f"[03] Built {report['output']}: {report['parts']} parts, "
        f"{report['animations']} animations, {report['bytes']} bytes"
    )


if __name__ == "__main__":
    main()
