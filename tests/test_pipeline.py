import json
import tempfile
import unittest
import xml.etree.ElementTree as ET
from pathlib import Path

from svg_rigger.cut import cut_parts
from svg_rigger.rig import build_rig
from svg_rigger.vectorize import DEFAULT_PRESET, load_preset


ROOT = Path(__file__).resolve().parents[1]
EXAMPLE = ROOT / "examples" / "minimal"


def elements(path, name):
    root = ET.parse(path).getroot()
    return [item for item in root.iter() if item.tag.split("}")[-1] == name]


class PipelineTests(unittest.TestCase):
    def test_rocky_preset_matches_supplied_app_settings(self):
        preset = load_preset(ROOT / "presets" / "rocky_actual_good_preset.json")
        self.assertEqual(preset, DEFAULT_PRESET)
        self.assertEqual(preset["clustering"], "watershed")
        self.assertEqual(preset["watershed_detail"], 255)
        self.assertEqual(preset["hierarchical"], "cutout")
        self.assertEqual(preset["filter_speckle"], 6)
        self.assertEqual(preset["mode"], "spline")
        self.assertEqual(preset["simplify"], 2.5)
        self.assertEqual(preset["path_precision"], 0)
        self.assertEqual(preset["max_colors"], 60)
        self.assertIsNone(preset["palette"])

    def test_cut_preserves_fully_covered_curves_and_reports_boolean_cuts(self):
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "parts"
            report = cut_parts(EXAMPLE / "cut.json", output)
            arm_paths = elements(output / "arm.svg", "path")
            source_paths = elements(EXAMPLE / "source.svg", "path")
            self.assertTrue((output / "body.svg").is_file())
            self.assertEqual(len(report["parts"]), 2)
            self.assertGreater(
                sum(item["paths_clipped_and_polygonized"] for item in report["parts"]),
                0,
            )
            self.assertIn(source_paths[1].get("d"), [item.get("d") for item in arm_paths])
            self.assertEqual(
                {item.get("fill") for item in arm_paths}, {"#78685f", "#4d403b"}
            )

    def test_builds_declarative_rotation_animation(self):
        with tempfile.TemporaryDirectory() as directory:
            directory = Path(directory)
            parts = directory / "parts"
            cut_parts(EXAMPLE / "cut.json", parts)
            config = {
                "title": "Test rig",
                "parts": [
                    {"id": "body", "file": str(parts / "body.svg")},
                    {
                        "id": "arm",
                        "file": str(parts / "arm.svg"),
                        "animation": {
                            "type": "rotate",
                            "pivot": [55, 45],
                            "values": [-10, 20, -10],
                            "duration": "1s",
                        },
                    },
                ],
            }
            config_path = directory / "rig.json"
            config_path.write_text(json.dumps(config), encoding="utf-8")
            output = directory / "animated.svg"
            report = build_rig(config_path, output)

            self.assertEqual(report["parts"], 2)
            self.assertEqual(report["animations"], 1)
            groups = {item.get("id") for item in elements(output, "g")}
            self.assertEqual(groups, {"body", "arm"})
            animations = elements(output, "animateTransform")
            self.assertEqual(len(animations), 1)
            self.assertEqual(animations[0].get("type"), "rotate")
            self.assertEqual(
                animations[0].get("values"), "-10 55 45;20 55 45;-10 55 45"
            )


if __name__ == "__main__":
    unittest.main()
