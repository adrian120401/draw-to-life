from dataclasses import replace
import json
from pathlib import Path

from PIL import Image
import pytest

from draw_to_life.config import Settings, valid_hex
from draw_to_life.description import CharacterDescription, parse_description
from draw_to_life.generation import Generated, build_prompt
from draw_to_life.models import ModelError, validate_snapshot
from draw_to_life.pipeline import Pipeline
from scripts.make_examples import example


@pytest.fixture
def setup_pipeline(tmp_path):
    settings = replace(Settings.from_env(), output_dir=tmp_path / "outputs")
    source = tmp_path / "rabbit-original.png"
    example("conejo").save(source)
    return Pipeline(settings), source


def test_complete_artifact_contract_with_mocked_models(setup_pipeline, monkeypatch):
    """Verifica orquestación; deliberadamente NO evalúa calidad del generador."""
    pipeline, source = setup_pipeline
    monkeypatch.setattr("draw_to_life.pipeline.local_models", lambda _: {"vision": Path("local-test")})
    monkeypatch.setattr("draw_to_life.pipeline.describe", lambda *_: (CharacterDescription(creature="rabbit"), []))
    monkeypatch.setattr(pipeline.generator, "unload", lambda: None)
    monkeypatch.setattr(pipeline.generator, "generate", lambda *args: Generated(
        Image.new("RGB", (512, 512), "#91CDB5"), "cpu", "test prompt", "test negative", []))
    run = pipeline.prepare(source, "Sticker", "Colores del dibujo", list(pipeline.settings.palette), seed=42)
    final = pipeline.finish(run)
    metadata = json.loads((run.directory / "metadata.json").read_text())
    assert final.is_file()
    assert metadata["status"] == "completed"
    assert metadata["original_filename"] == source.name
    assert metadata["seed"] == 42
    assert metadata["description"]["creature"] == "rabbit"
    assert {"original.png", "cropped.png", "isolated.png", "final_character.png", "metadata.json"} <= {
        path.name for path in run.directory.iterdir()}


def test_failure_preserves_preprocessing_and_marks_metadata(setup_pipeline, monkeypatch):
    pipeline, source = setup_pipeline
    def missing(_):
        raise ModelError("missing model")
    monkeypatch.setattr("draw_to_life.pipeline.local_models", missing)
    monkeypatch.setattr(pipeline.generator, "unload", lambda: None)
    run = pipeline.prepare(source, "Sticker", "Paleta por defecto", list(pipeline.settings.palette))
    with pytest.raises(ModelError):
        pipeline.finish(run)
    metadata = json.loads((run.directory / "metadata.json").read_text())
    assert metadata["status"] == "failed"
    assert (run.directory / "isolated.png").exists()
    assert not (run.directory / "final_character.png").exists()


def test_pencil_fallback_is_explicit(setup_pipeline, tmp_path):
    pipeline, _ = setup_pipeline
    pencil = tmp_path / "pencil.png"
    example("gato_lapiz").save(pencil)
    run = pipeline.prepare(pencil, "Cartoon suave", "Colores del dibujo", list(pipeline.settings.palette))
    assert not run.preserve_colors
    assert run.metadata["warnings"]


def test_invalid_description_and_untrusted_text():
    with pytest.raises(ValueError):
        parse_description('not JSON')
    with pytest.raises(ValueError):
        parse_description('{"creature": ["cat"]}')
    result = parse_description('```json\n{"creature": "cat", "eyes":"large eyes"}\n```')
    assert result.creature == "cat"
    assert result.ears == ""
    assert "large eyes" in build_prompt(result, "Sticker", ["#91CDB5"], False)
    assert "green rabbit" not in build_prompt(CharacterDescription(creature="green rabbit"), "Sticker", ["#F39AA8"], False)


def test_invalid_color_and_incomplete_snapshot(tmp_path):
    with pytest.raises(ValueError):
        valid_hex('red" onclick="bad')
    with pytest.raises(ModelError, match="incompleto"):
        validate_snapshot("control", tmp_path)


def test_color_only_species_is_not_used_as_a_creature():
    description = parse_description('{"creature":"purple","eyes":"large","accessories":"cone hat"}')
    assert description.creature == "cartoon creature"
    assert description.summary
    prompt = build_prompt(description, "Mascota virtual", ["#91CDB5"], False)
    assert "one cartoon creature" in prompt
    assert "large eyes" in prompt
    assert "wearing cone hat" in prompt
