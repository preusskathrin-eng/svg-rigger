"""Inspect structural SVG metrics used by the rigging pipeline."""

import argparse
import json
import re
import xml.etree.ElementTree as ET
from pathlib import Path


COMMAND_RE = re.compile(r"[MmLlHhVvCcSsQqTtAaZz]")


def local_name(tag):
    return tag.split("}")[-1]


def inspect_svg(path):
    path = Path(path)
    root = ET.parse(path).getroot()
    paths = [item for item in root.iter() if local_name(item.tag) == "path"]
    commands = [
        command
        for item in paths
        for command in COMMAND_RE.findall(item.get("d", ""))
    ]
    fills = {item.get("fill") for item in paths if item.get("fill") not in (None, "none")}
    return {
        "file": str(path),
        "bytes": path.stat().st_size,
        "viewBox": root.get("viewBox"),
        "width": root.get("width"),
        "height": root.get("height"),
        "paths": len(paths),
        "fills": len(fills),
        "commands": len(commands),
        "cubic_commands": sum(item.lower() == "c" for item in commands),
        "groups": sum(local_name(item.tag) == "g" for item in root.iter()),
        "animations": sum(
            local_name(item.tag) in {"animate", "animateTransform"}
            for item in root.iter()
        ),
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("svg", nargs="+", help="SVG file(s)")
    args = parser.parse_args()
    print(json.dumps([inspect_svg(path) for path in args.svg], indent=2))


if __name__ == "__main__":
    main()
