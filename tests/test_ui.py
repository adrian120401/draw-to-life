from dataclasses import replace

from draw_to_life.config import ROOT, Settings
from draw_to_life.pipeline import Pipeline
from draw_to_life import ui
from draw_to_life.rig import export_package, make_guide


def configured_ui(tmp_path, monkeypatch):
    settings = replace(Settings.from_env(), output_dir=tmp_path, device="cpu")
    pipeline = Pipeline(settings)
    monkeypatch.setattr(ui, "Pipeline", lambda _settings: pipeline)
    monkeypatch.setattr(ui, "diagnose", lambda _settings: {
        "cuda_available": False, "character_ready": True, "gpu": None,
    })
    demo = ui.build_ui(settings)
    functions = {item.fn.__name__: item.fn for item in demo.fns.values() if item.fn}
    return settings, pipeline, demo, functions


def test_generation_error_returns_to_upload_and_clears_result(tmp_path, monkeypatch):
    _settings, pipeline, _demo, functions = configured_ui(tmp_path, monkeypatch)

    def fail(_run, _progress):
        raise RuntimeError("Error de prueba <detalle>")

    monkeypatch.setattr(pipeline, "finish", fail)
    updates = list(functions["process"](str(ROOT / "test1.png")))
    failed = updates[-1]
    assert failed[0]["visible"] and not failed[1]["visible"] and not failed[2]["visible"]
    assert failed[4] == "" and failed[5]["value"] is None
    assert 'role="alert"' in failed[6] and "Probá otra vez" in failed[6]
    assert "<detalle>" not in failed[6]
    assert failed[7]["visible"] and failed[8] == "upload"


def test_upload_automatically_moves_through_generation_to_play(tmp_path, monkeypatch):
    settings, pipeline, demo, functions = configured_ui(tmp_path, monkeypatch)

    def finish(run, progress):
        assert run.mode == "auto" and run.metadata["style"] == "Cartoon infantil"
        assert run.metadata["color_mode"] == "Colores del dibujo"
        progress(.22, "technical message")
        progress(.35, "technical message")
        run.puppet = make_guide("dog")
        export_package(run.puppet, run.directory / "character")

    monkeypatch.setattr(pipeline, "finish", finish)
    updates = list(functions["process"](str(ROOT / "test1.png")))
    assert all(item[8] == "processing" for item in updates[:-1])
    assert any("Mirando tu dibujo" in item[3] for item in updates)
    assert any("Dándole vida" in item[3] for item in updates)
    assert all("technical message" not in item[3] for item in updates)
    result = updates[-1]
    assert result[8] == "result" and result[2]["visible"]
    assert not result[0]["visible"] and not result[1]["visible"]
    assert "<iframe" in result[4]
    assert result[5]["value"].endswith("character.zip") and result[5]["visible"]
    reset = functions["reset"]()
    assert reset[8] == "upload" and reset[4] == "" and reset[9] is None
    assert reset[10] is None and reset[11] is None
    assert reset[5]["value"] is None
    assert demo.config["enable_queue"]
    assert settings.output_dir.exists()


def test_invalid_upload_never_calls_generation(tmp_path, monkeypatch):
    _settings, pipeline, _demo, functions = configured_ui(tmp_path, monkeypatch)
    monkeypatch.setattr(pipeline, "prepare", lambda *_args, **_kwargs: (_ for _ in ()).throw(AssertionError("must not generate")))
    path = tmp_path / "broken.png"
    path.write_bytes(b"not an image")
    result = list(functions["process"](str(path)))[-1]
    assert result[8] == "upload" and 'role="alert"' in result[6]
    assert not result[7]["visible"]


def test_errors_are_escaped():
    assert "&lt;script&gt;" in ui.error_html("<script>")


def test_camera_and_gallery_replace_the_same_source_and_reset_it(tmp_path, monkeypatch):
    _settings, _pipeline, demo, functions = configured_ui(tmp_path, monkeypatch)
    gallery = functions["select_file"]("gallery.jpg")
    camera = functions["select_file"]("camera.heic")
    assert gallery[-1] == "gallery.jpg" and camera[-1] == "camera.heic"
    assert gallery[-2] == camera[-2] == "processing"
    assert functions["reset"]()[-1] is None
    uploaders = [c for c in demo.config["components"] if c["type"] == "uploadbutton"]
    assert len(uploaders) == 2
    assert all(".heic" in c["props"]["file_types"] for c in uploaders)
