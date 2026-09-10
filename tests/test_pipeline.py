import hashlib
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
                "viewbox_padding": 5,
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
            self.assertEqual(report["viewBox"], "-5 -5 110 110")
            self.assertEqual(ET.parse(output).getroot().get("viewBox"), "-5 -5 110 110")
            groups = {item.get("id") for item in elements(output, "g")}
            self.assertEqual(groups, {"body", "arm"})
            animations = elements(output, "animateTransform")
            self.assertEqual(len(animations), 1)
            self.assertEqual(animations[0].get("type"), "rotate")
            self.assertEqual(
                animations[0].get("values"), "-10 55 45;20 55 45;-10 55 45"
            )

    def test_reads_source_group_and_clip_paths_from_one_inkscape_svg(self):
        combined_svg = """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 10">
  <defs>
    <clipPath id="leftClip"><path d="M0 0H10V10H0Z"/></clipPath>
    <clipPath id="rightClip"><path d="M10 0H20V10H10Z"/></clipPath>
  </defs>
  <g id="complete">
    <path d="M0 0H20V10H0Z" fill="#123456"/>
  </g>
  <g id="left" clip-path="url(#leftClip)">
    <path d="M0 0H20V10H0Z" fill="#123456"/>
  </g>
</svg>"""
        with tempfile.TemporaryDirectory() as directory:
            directory = Path(directory)
            source = directory / "combined.svg"
            source.write_text(combined_svg, encoding="utf-8")
            manifest = {
                "source_svg": "combined.svg",
                "source_group": "complete",
                "sample_step": 1,
                "precision": 1,
                "parts": [
                    {"id": "left", "mask_clip_id": "leftClip"},
                    {"id": "right", "mask_clip_id": "rightClip"},
                ],
            }
            manifest_path = directory / "cut.json"
            manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
            output = directory / "parts"
            report = cut_parts(manifest_path, output)
            self.assertEqual(report["source_group"], "complete")
            self.assertEqual(report["source_paths"], 1)
            self.assertEqual(len(elements(output / "left.svg", "path")), 1)
            self.assertEqual(len(elements(output / "right.svg", "path")), 1)

    def test_real_rocky_fixture_keeps_expected_part_structure(self):
        source = ROOT / "examples" / "rocky" / "input" / "rocky_and_his_parts.svg"
        self.assertEqual(
            hashlib.sha256(source.read_bytes()).hexdigest(),
            "9b46c0f098dc22bed65e88cbf16aa5bd55fbeaf86090ede0068236fcb67e2e8e",
        )
        with tempfile.TemporaryDirectory() as directory:
            report = cut_parts(
                ROOT / "examples" / "rocky" / "cut.json",
                Path(directory) / "parts",
            )
        actual = {
            item["id"]: (
                item["output_paths"],
                item["curves_preserved_unchanged"],
                item["paths_clipped_and_polygonized"],
            )
            for item in report["parts"]
        }
        self.assertEqual(
            actual,
            {
                "body": (129, 114, 15),
                "head": (204, 142, 62),
                "left_arm": (39, 18, 21),
            },
        )


if __name__ == "__main__":
    unittest.main()
