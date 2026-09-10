"""Shared SVG path sampling and polygon serialization helpers."""

import math
import re
import xml.etree.ElementTree as ET
from pathlib import Path

from shapely.geometry import GeometryCollection, MultiPolygon, Polygon
from shapely.ops import orient, unary_union
from svgelements import Close, Matrix, Move, Path as SvgPath


SVG_NS = "http://www.w3.org/2000/svg"
TRANSFORMABLE = {"svg", "g", "path"}


def local_name(tag):
    return tag.split("}")[-1]


def parse_style(text):
    result = {}
    for item in (text or "").split(";"):
        if ":" in item:
            key, value = item.split(":", 1)
            result[key.strip()] = value.strip()
    return result


def repair(geometry):
    if geometry is None or geometry.is_empty:
        return None
    if geometry.is_valid:
        return geometry
    repaired = geometry.buffer(0)
    return None if repaired.is_empty else repaired


def signed_area(points):
    return sum(
        x1 * y2 - x2 * y1
        for (x1, y1), (x2, y2) in zip(points, points[1:] + points[:1])
    ) / 2


def sample_path(path_data, matrix=None, sample_step=0.5, fill_rule="nonzero"):
    path = SvgPath(path_data)
    if matrix is not None and not matrix.is_identity():
        path *= matrix

    rings = []
    for subpath in path.as_subpaths():
        segments = list(subpath)
        if not segments:
            continue
        points = []
        closed = False
        for segment in segments:
            if isinstance(segment, Move):
                points.append((float(segment.end.x), float(segment.end.y)))
                continue
            if isinstance(segment, Close):
                closed = True
            try:
                length = float(segment.length(error=1e-5))
            except Exception:
                length = abs(segment.end - segment.start)
            count = max(1, min(2048, int(math.ceil(length / sample_step))))
            for index in range(1, count + 1):
                point = segment.point(index / count)
                value = (float(point.x), float(point.y))
                if not points or value != points[-1]:
                    points.append(value)
        if not closed or len(points) < 3:
            continue
        if points[0] == points[-1]:
            points.pop()
        if len(points) < 3:
            continue
        polygon = repair(Polygon(points))
        if polygon is not None:
            rings.append((polygon, signed_area(points)))

    if not rings:
        return None
    if fill_rule == "evenodd":
        result = GeometryCollection()
        for polygon, _ in rings:
            result = polygon if result.is_empty else result.symmetric_difference(polygon)
        return repair(result)

    rings.sort(key=lambda item: item[0].area, reverse=True)
    exterior_sign = 1 if rings[0][1] >= 0 else -1
    result = GeometryCollection()
    for polygon, area in rings:
        if (1 if area >= 0 else -1) == exterior_sign:
            result = polygon if result.is_empty else result.union(polygon)
        else:
            result = result.difference(polygon)
    return repair(result)


def iter_visible_paths(root):
    ignored_containers = {"defs", "clipPath", "mask", "pattern", "symbol"}

    def walk(element, parent_matrix, inherited_fill, inherited_rule, ignored=False):
        name = local_name(element.tag)
        ignored = ignored or name in ignored_containers
        style = parse_style(element.get("style"))
        fill = element.get("fill", style.get("fill", inherited_fill))
        fill_rule = element.get(
            "fill-rule", style.get("fill-rule", inherited_rule or "nonzero")
        )
        local_matrix = Matrix(element.get("transform", "")) if name in TRANSFORMABLE else Matrix()
        matrix = local_matrix * parent_matrix
        if name == "path" and not ignored and fill not in (None, "none") and element.get("d"):
            yield element, matrix, fill, fill_rule
        for child in list(element):
            yield from walk(child, matrix, fill, fill_rule, ignored)

    yield from walk(root, Matrix(), None, "nonzero")


def load_path_records(path, sample_step=0.5):
    root = ET.parse(path).getroot()
    records = []
    skipped = 0
    for element, matrix, fill, fill_rule in iter_visible_paths(root):
        geometry = sample_path(element.get("d"), matrix, sample_step, fill_rule)
        if geometry is None:
            skipped += 1
            continue
        records.append(
            {
                "geometry": geometry,
                "fill": fill,
                "fill_rule": fill_rule,
                "d": element.get("d"),
                "matrix_identity": matrix.is_identity(),
                "opacity": element.get("opacity"),
                "fill_opacity": element.get("fill-opacity"),
            }
        )
    return root, records, skipped


def load_mask(path, sample_step=0.5):
    _, records, skipped = load_path_records(path, sample_step)
    if not records:
        raise ValueError(f"mask contains no usable closed filled paths: {path}")
    geometry = repair(unary_union([record["geometry"] for record in records]))
    if geometry is None:
        raise ValueError(f"mask geometry is empty after repair: {path}")
    return geometry, {"paths": len(records), "skipped": skipped}


def fmt(value, precision):
    text = f"{value:.{precision}f}".rstrip("0").rstrip(".")
    return "0" if text in {"-0", ""} else text


def polygon_to_d(polygon, precision):
    polygon = orient(polygon, sign=1.0)
    rings = [polygon.exterior, *polygon.interiors]
    parts = []
    for ring in rings:
        coordinates = list(ring.coords)
        if len(coordinates) < 4:
            continue
        start_x, start_y = coordinates[0]
        commands = [f"M{fmt(start_x, precision)},{fmt(start_y, precision)}"]
        commands.extend(
            f"L{fmt(x, precision)},{fmt(y, precision)}"
            for x, y in coordinates[1:-1]
        )
        commands.append("Z")
        parts.append("".join(commands))
    return "".join(parts)


def geometry_to_d(geometry, precision=2):
    if geometry is None or geometry.is_empty:
        return ""
    if isinstance(geometry, Polygon):
        return polygon_to_d(geometry, precision)
    if isinstance(geometry, MultiPolygon):
        return "".join(polygon_to_d(item, precision) for item in geometry.geoms)
    if isinstance(geometry, GeometryCollection):
        return "".join(
            geometry_to_d(item, precision)
            for item in geometry.geoms
            if isinstance(item, (Polygon, MultiPolygon))
        )
    return ""


def svg_canvas_attributes(root):
    result = {"version": "1.1"}
    for name in ("viewBox", "width", "height"):
        if root.get(name):
            result[name] = root.get(name)
    if "viewBox" not in result and root.get("width") and root.get("height"):
        number = re.compile(r"[-+]?(?:\d*\.\d+|\d+)")
        width = number.match(root.get("width"))
        height = number.match(root.get("height"))
        if width and height:
            result["viewBox"] = f"0 0 {width.group()} {height.group()}"
    return result

