from copy import deepcopy
from dataclasses import replace
import json
from pathlib import Path
import zipfile

import numpy as np
from PIL import Image
import pytest

from draw_to_life.characters import CharacterFactory
from draw_to_life.config import Settings
from draw_to_life.description import CharacterDescription, identify_species, parse_description
from draw_to_life.generation import Generated
from draw_to_life.pipeline import Pipeline
from draw_to_life.preview import preview_document
from draw_to_life.processing import load_image, preprocess
from draw_to_life.rig import (SPECIES, RigError, apply_palette, catalog_status, composite,
                              export_package, free_guide, load_puppet, make_guide,
                              save_puppet, validate_manifest)


@pytest.fixture
def settings(tmp_path):
    return replace(Settings.from_env(), catalog_dir=tmp_path / "catalog", output_dir=tmp_path / "outputs")


@pytest.fixture
def fake_factory(settings, monkeypatch):
    factory = CharacterFactory(settings)
    monkeypatch.setattr(factory.generator, "generate", lambda *args, **kwargs: Generated(
        args[1].copy(), "cpu", kwargs["prompt_override"], kwargs["negative_override"], []))
    monkeypatch.setattr(factory.generator, "unload", lambda: None)
    return factory


PATHS = {"image": Path("image-revision"), "control": Path("control-revision"), "vision": Path("vision-revision")}


@pytest.mark.parametrize("species", SPECIES)
def test_guides_have_complete_layers_and_valid_attachments(species):
    puppet = make_guide(species)
    validate_manifest(puppet.manifest)
    assert {"body", "head", "eye_left", "eye_right", "mouth"} <= puppet.textures.keys()
    assert composite(puppet).getchannel("A").getbbox()
    for layer in puppet.manifest["layers"]:
        assert puppet.textures[layer["id"]].size == (512, 512)
        assert puppet.textures[layer["id"]].getchannel("A").getbbox()


def test_species_ambiguity_and_word_boundaries():
    assert identify_species("happy puppy") == "dog"
    assert identify_species("bearded cartoon creature") == "unknown"
    assert identify_species("a cat or a dog") == "unknown"
    desc = parse_description('{"creature":"dog", "species":"dog", "species_uncertain":true}')
    assert desc.species_uncertain
    assert parse_description('{"creature":"duckling"}').species == "duck"
    with pytest.raises(ValueError):
        parse_description('{"creature":"dog", "species_uncertain":"false"}')


def test_palette_changes_skin_without_mutating_geometry_or_face():
    base = make_guide("dog")
    changed = apply_palette(base, ["#61B8F0", "#FFD179", "#ED7CAA"])
    assert changed.manifest["layers"] == base.manifest["layers"]
    assert changed.manifest["palette"] != base.manifest["palette"]
    for name in base.textures:
        assert np.array_equal(np.array(base.textures[name])[:, :, 3], np.array(changed.textures[name])[:, :, 3])
    assert np.array_equal(np.array(base.textures["eye_left"]), np.array(changed.textures["eye_left"]))
    assert not np.array_equal(np.array(base.textures["head"]), np.array(changed.textures["head"]))


def test_one_color_drawing_keeps_a_complete_three_color_palette():
    guide = make_guide("unknown", palette=["#408FCC"])
    assert guide.manifest["palette"] == ["#408FCC", "#FFE2A8", "#F39AA8"]
    colored = apply_palette(make_guide("dog"), ["#408FCC"])
    assert colored.manifest["palette"][0] == "#408FCC"
    assert len(colored.manifest["palette"]) == 3


def test_guides_are_never_published_as_generated_bases(settings):
    save_puppet(make_guide("dog"), settings.catalog_dir / "dog")
    with pytest.raises(RigError, match="generada"):
        load_puppet(settings.catalog_dir / "dog")
    assert "dog" not in catalog_status(settings.catalog_dir)["ready"]


def test_prepare_adapt_and_export_preserve_the_rig(fake_factory, settings):
    base = fake_factory.prepare_base("dog", PATHS, 42)
    assert load_puppet(settings.catalog_dir / "dog").manifest["provenance"]["status"] == "generated"
    adapted = fake_factory.adapt(base, ["#4EAD72", "#FFE2A8", "#F39AA8"], PATHS,
                                 CharacterDescription(creature="dog", species="dog", species_uncertain=False), 123,
                                 lambda *_: None)
    assert adapted.manifest["layers"] == base.manifest["layers"]
    assert adapted.manifest["provenance"]["parameters"]["strength"] == .30
    for key in base.textures:
        assert np.array_equal(np.array(base.textures[key])[:, :, 3], np.array(adapted.textures[key])[:, :, 3])
    package = export_package(adapted, settings.output_dir / "character")
    with zipfile.ZipFile(package) as bundle:
        assert {"character.json", "character-player.js", "index.html", "textures/eye_left.png"} <= set(bundle.namelist())
        assert b"data:image/png;base64," in bundle.read("index.html")
    assert all(layer["texture"].startswith("textures/") for layer in adapted.manifest["layers"])


def test_catalog_preparation_reuses_completed_parts(fake_factory, settings, monkeypatch):
    fake_factory.prepare_base("cat", PATHS, 42)
    monkeypatch.setattr(fake_factory.generator, "generate", lambda *_args, **_kwargs: pytest.fail("should use checkpoint"))
    result = fake_factory.prepare_base("cat", PATHS, 42, force=True)
    assert all(part["reused_checkpoint"] for part in result.manifest["provenance"]["parts"])
    assert list(settings.catalog_dir.glob("cat.backup-*"))


def test_failed_generation_does_not_publish_a_base(fake_factory, settings, monkeypatch):
    monkeypatch.setattr(fake_factory.generator, "generate", lambda *_args, **_kwargs: (_ for _ in ()).throw(RuntimeError("model failed")))
    with pytest.raises(RuntimeError):
        fake_factory.prepare_base("pig", PATHS)
    assert not (settings.catalog_dir / "pig").exists()


def test_corrupt_checkpoint_regenerates_only_that_piece(fake_factory, settings, monkeypatch):
    fake_factory.prepare_base("bear", PATHS, 42)
    checkpoints = settings.catalog_dir / ".work" / "bear" / "checkpoints"
    next(checkpoints.glob("*.json")).write_text("{interrupted", encoding="utf-8")
    original = fake_factory.generator.generate
    calls = []
    def regenerate(*args, **kwargs):
        calls.append(args)
        return original(*args, **kwargs)
    monkeypatch.setattr(fake_factory.generator, "generate", regenerate)
    result = fake_factory.prepare_base("bear", PATHS, 42, force=True)
    assert len(calls) == 1
    assert sum(part["reused_checkpoint"] for part in result.manifest["provenance"]["parts"]) == 1


def test_invalid_cycles_texture_paths_and_dimensions(tmp_path):
    puppet = make_guide("cat")
    cycle = deepcopy(puppet.manifest)
    cycle["layers"][1]["parent"] = "head"
    with pytest.raises(RigError, match="ciclo"):
        validate_manifest(cycle)
    escaped = deepcopy(puppet.manifest)
    escaped["layers"][0]["texture"] = "../private.png"
    with pytest.raises(RigError, match="Ruta"):
        validate_manifest(escaped)
    save_puppet(puppet, tmp_path)
    Image.new("RGBA", (100, 100)).save(tmp_path / puppet.manifest["layers"][0]["texture"])
    with pytest.raises(RigError, match="lienzo"):
        validate_manifest(puppet.manifest, tmp_path)


def test_free_character_has_a_separate_face_and_no_animal_base():
    drawing = preprocess(load_image(Path(__file__).resolve().parents[1] / "test1.png"))
    puppet = free_guide(drawing.silhouette, 512, ["#91CDB5", "#FFE2A8", "#F39AA8"], "puppy")
    validate_manifest(puppet.manifest)
    assert puppet.manifest["id"] == "custom"
    assert "base_id" not in puppet.manifest
    head = np.array(puppet.textures["head"])[:, :, 3]
    for eye in ("eye_left", "eye_right"):
        alpha = np.array(puppet.textures[eye])[:, :, 3]
        assert np.count_nonzero((alpha > 50) & (head == 0)) == 0


@pytest.mark.parametrize("species,uncertain,requested,expected", [
    ("dog", False, "auto", "template"), ("dog", True, "auto", "free"),
    ("other", False, "auto", "free"), ("dog", False, "free", "free"),
])
def test_pipeline_routes_ambiguity_and_explicit_free(settings, fake_factory, monkeypatch,
                                                     species, uncertain, requested, expected):
    fake_factory.prepare_base("dog", PATHS)
    pipeline = Pipeline(settings)
    pipeline.characters = fake_factory
    monkeypatch.setattr(pipeline.generator, "unload", lambda: None)
    monkeypatch.setattr("draw_to_life.pipeline.local_models", lambda _: PATHS)
    monkeypatch.setattr("draw_to_life.pipeline.describe", lambda *_: (
        CharacterDescription(creature="puppy", species=species, species_uncertain=uncertain), []))
    run = pipeline.prepare(Path(__file__).resolve().parents[1] / "test1.png", "Cartoon infantil",
                           "Colores del dibujo", list(settings.palette), mode=requested, seed=7)
    pipeline.finish(run)
    data = json.loads((run.directory / "metadata.json").read_text())
    assert data["generation_mode"] == expected
    assert data["status"] == "completed"
    assert data["parameters"]["strength"] == data["effective_parameters"]["strength"]
    assert data["parameters"]["image_size"] == settings.image_size
    assert (run.directory / "character.zip").is_file()
    assert (run.puppet.manifest.get("base_id") is not None) == (expected == "template")


def test_forced_template_failure_keeps_intermediates(settings, fake_factory, monkeypatch):
    pipeline = Pipeline(settings)
    pipeline.characters = fake_factory
    monkeypatch.setattr(pipeline.generator, "unload", lambda: None)
    monkeypatch.setattr("draw_to_life.pipeline.local_models", lambda _: PATHS)
    monkeypatch.setattr("draw_to_life.pipeline.describe", lambda *_: (CharacterDescription(), []))
    run = pipeline.prepare(Path(__file__).resolve().parents[1] / "test1.png", "Cartoon infantil",
                           "Paleta por defecto", list(settings.palette), mode="template")
    with pytest.raises(RigError):
        pipeline.finish(run)
    assert run.metadata["status"] == "failed"
    assert (run.directory / "isolated.png").is_file()
    assert not (run.directory / "character.zip").exists()


def test_preview_escapes_untrusted_metadata():
    puppet = make_guide("cat")
    puppet.manifest["name"] = "</script><script>alert(1)</script>"
    html = preview_document(puppet)
    assert "</script><script>alert(1)" not in html
    assert "\\u003c/script" in html
    assert "data:image/png;base64," in html
