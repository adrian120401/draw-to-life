from types import SimpleNamespace
import sys

import pytest

import app
from draw_to_life import ui
from draw_to_life.config import Settings


@pytest.mark.parametrize("lan,host", [(False, "127.0.0.1"), (True, "0.0.0.0")])
def test_lan_is_explicit_and_keeps_file_limits(tmp_path, monkeypatch, lan, host):
    from dataclasses import replace
    settings = replace(Settings.from_env(), output_dir=tmp_path)
    captured = {}
    monkeypatch.setattr(app.Settings, "from_env", lambda: settings)
    monkeypatch.setattr(sys, "argv", ["app.py", *(["--lan"] if lan else [])])
    monkeypatch.setattr(ui, "build_ui", lambda _: SimpleNamespace(launch=lambda **kwargs: captured.update(kwargs)))
    app.main()
    assert captured["server_name"] == host
    assert captured["share"] is False
    assert captured["max_file_size"] == "30mb"
    assert any(path.endswith("models") for path in captured["blocked_paths"])
