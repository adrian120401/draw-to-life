from fnmatch import fnmatch

import numpy as np
import pytest
from safetensors.numpy import save_file

from draw_to_life.config import Settings
from draw_to_life.models import model_specs, validate_snapshot


@pytest.mark.parametrize("kind", ["image", "character"])
def test_generator_snapshot_does_not_require_filter_components(tmp_path, kind):
    for name in ("model_index.json", "scheduler/scheduler_config.json", "tokenizer/vocab.json",
                 "tokenizer/merges.txt", "tokenizer/tokenizer_config.json"):
        path = tmp_path / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("{}")
    for component in ("unet", "vae", "text_encoder"):
        directory = tmp_path / component
        directory.mkdir()
        (directory / "config.json").write_text("{}")
        filename = "model.fp16.safetensors" if component == "text_encoder" else "diffusion_pytorch_model.fp16.safetensors"
        save_file({"weight": np.zeros(1, dtype=np.float16)}, str(directory / filename))
    validate_snapshot(kind, tmp_path)
    patterns = model_specs(Settings.from_env(), include_character=True)[kind][1]
    for name in ("safety_checker/config.json", "safety_checker/model.fp16.safetensors",
                 "feature_extractor/preprocessor_config.json"):
        assert not any(fnmatch(name, pattern) for pattern in patterns)
