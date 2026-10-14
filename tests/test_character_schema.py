"""El contrato del juego también se valida sin cargar dependencias de IA."""

from copy import deepcopy
import math
import unittest

from draw_to_life.character_schema import RigError, validate_manifest


def character():
    return {"schema_version": 1, "canvas": [512, 512], "layers": [
        {"id": "eye", "parent": "head", "pivot": [207, 224], "texture": "textures/eye.png"},
        {"id": "head", "parent": "body", "pivot": [256, 298], "texture": "textures/head.png"},
        {"id": "body", "parent": None, "pivot": [256, 442], "texture": "textures/body.png"}],
        "animations": {"idle": {"duration": 3.2, "breath_scale": .018, "head_degrees": 1.5},
                       "blink": {"duration": .18, "interval": 4.3},
                       "react": {"duration": .85, "jump": .025, "tilt_degrees": 8}}}


class CharacterSchemaTests(unittest.TestCase):
    def test_out_of_order_parents_are_valid_and_not_mutated(self):
        rig = character()
        before = deepcopy(rig)
        validate_manifest(rig)
        self.assertEqual(before, rig)

    def test_incompatible_version(self):
        for invalid in (None, [], {"schema_version": 2}):
            with self.subTest(invalid=invalid), self.assertRaises(RigError):
                validate_manifest(invalid)

    def test_missing_parent(self):
        rig = character()
        rig["layers"][1]["parent"] = "missing"
        with self.assertRaisesRegex(RigError, "inexistente"):
            validate_manifest(rig)

    def test_cycles(self):
        rig = character()
        rig["layers"][2]["parent"] = "eye"
        with self.assertRaisesRegex(RigError, "ciclo"):
            validate_manifest(rig)

    def test_duplicate_ids(self):
        rig = character()
        rig["layers"].append(deepcopy(rig["layers"][0]))
        with self.assertRaisesRegex(RigError, "únicos"):
            validate_manifest(rig)

    def test_malformed_layer_lists(self):
        for layers in (None, {}, [None], ["head"]):
            rig = character()
            rig["layers"] = layers
            with self.subTest(layers=layers), self.assertRaises(RigError):
                validate_manifest(rig)

    def test_nonfinite_pivots(self):
        for number in (math.nan, math.inf, -math.inf):
            rig = character()
            rig["layers"][0]["pivot"][0] = number
            with self.subTest(number=number), self.assertRaisesRegex(RigError, "Pivote"):
                validate_manifest(rig)

    def test_relative_texture_paths(self):
        for path in ("../private.png", "/private.png", "textures/eye.jpg",
                     "C:/private.png", "C:private.png", r"\private.png", r"..\private.png"):
            rig = character()
            rig["layers"][0]["texture"] = path
            with self.subTest(path=path), self.assertRaisesRegex(RigError, "Ruta"):
                validate_manifest(rig)

    def test_canvas_dimensions(self):
        for canvas in ([0, 512], [512, 4096], [True, 512], [512], "512"):
            rig = character()
            rig["canvas"] = canvas
            with self.subTest(canvas=canvas), self.assertRaisesRegex(RigError, "Lienzo"):
                validate_manifest(rig)

    def test_missing_animations(self):
        rig = character()
        del rig["animations"]["blink"]
        with self.assertRaisesRegex(RigError, "Faltan"):
            validate_manifest(rig)

    def test_invalid_duration_and_interval(self):
        for duration in (0, -1, math.nan, "slow"):
            rig = character()
            rig["animations"]["idle"]["duration"] = duration
            with self.subTest(duration=duration), self.assertRaisesRegex(RigError, "Duración"):
                validate_manifest(rig)
        rig = character()
        rig["animations"]["blink"]["interval"] = .05
        with self.assertRaisesRegex(RigError, "intervalo"):
            validate_manifest(rig)


if __name__ == "__main__":
    unittest.main()
