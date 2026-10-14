from dataclasses import replace

from draw_to_life.config import ROOT, Settings
from draw_to_life.pipeline import Pipeline
from draw_to_life import ui


def test_generation_error_is_visible_in_character_panel(tmp_path, monkeypatch):
    settings = replace(Settings.from_env(), output_dir=tmp_path, device="cpu")
    pipeline = Pipeline(settings)
    monkeypatch.setattr(ui, "Pipeline", lambda _settings: pipeline)
    monkeypatch.setattr(ui, "diagnose", lambda _settings: {
        "cuda_available": False, "character_ready": True, "gpu": None,
    })
    monkeypatch.setattr(ui, "catalog_status", lambda _directory: {"ready": ["dog"]})

    def fail(_run, _progress):
        raise RuntimeError("Error de prueba <detalle>")

    monkeypatch.setattr(pipeline, "finish", fail)
    demo = ui.build_ui(settings)
    process = next(item.fn for item in demo.fns.values()
                   if getattr(item.fn, "__name__", "") == "process")
    updates = list(process(str(ROOT / "test1.png"), "Cartoon infantil", "Paleta por defecto",
                           *settings.palette, "auto", "auto", progress=lambda *_args, **_kwargs: None))
    failed = updates[-1]
    assert failed[0] is not None and failed[1] is not None
    assert failed[2] is None and failed[9] is None
    assert 'role="alert"' in failed[8]
    assert "Error de prueba &lt;detalle&gt;" in failed[8]
    assert "<detalle>" not in failed[8]
