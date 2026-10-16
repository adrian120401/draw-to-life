from copy import deepcopy
import zipfile

import numpy as np
import pytest

from draw_to_life.expressions import texture_entries, with_expressions
from draw_to_life.rig import SPECIES, RigError, export_package, load_puppet, make_guide, validate_manifest


@pytest.mark.parametrize("species", [*SPECIES, "unknown"])
def test_old_bases_gain_expressions_without_changing_anatomy_or_art(species, tmp_path):
    old = make_guide(species)
    # Emular un catálogo anterior: las variantes no son requisito de v1.
    for layer in old.manifest["layers"]:
        layer.pop("expressions", None)
        layer.pop("mouth_anchor", None)
    old.textures = {layer["id"]: old.textures[layer["id"]] for layer in old.manifest["layers"]}
    before = deepcopy(old.manifest)
    upgraded = with_expressions(old)
    assert old.manifest == before
    assert [layer["id"] for layer in upgraded.manifest["layers"]] == list(old.textures)
    for key in old.textures:
        assert np.array_equal(np.array(old.textures[key]), np.array(upgraded.textures[key]))
    for layer in upgraded.manifest["layers"]:
        for name in layer.get("expressions", {}):
            variant = upgraded.textures[f"{layer['id']}__{name}"]
            assert variant.size == old.textures[layer["id"]].size
            assert variant.getchannel("A").getbbox()
    archive = export_package(upgraded, tmp_path / "character")
    loaded = load_puppet(tmp_path / "character", require_generated=False)
    assert loaded.manifest == upgraded.manifest
    assert loaded.textures.keys() == upgraded.textures.keys()
    with zipfile.ZipFile(archive) as bundle:
        assert {path for _, path in texture_entries(upgraded.manifest)} <= set(bundle.namelist())
        document = bundle.read("index.html")
        assert b'data-action="feed"' in document and b'data-action="pet"' in document


def test_mouth_expressions_preserve_nose_pixels():
    puppet = make_guide("dog")
    original = np.array(puppet.textures["mouth"])
    for name in ("happy", "open", "chew"):
        variant = np.array(puppet.textures[f"mouth__{name}"])
        assert np.array_equal(original[:280], variant[:280])
        assert not np.array_equal(original[280:], variant[280:])


@pytest.mark.parametrize("bad", [None, [], {"happy": "../private.png"}, {"other": "textures/other.png"}])
def test_invalid_expression_paths_and_maps_are_rejected(bad):
    puppet = make_guide("dog")
    puppet.manifest["layers"][-1]["expressions"] = bad
    with pytest.raises(RigError):
        validate_manifest(puppet.manifest)
