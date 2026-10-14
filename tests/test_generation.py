from dataclasses import replace
from types import SimpleNamespace
from unittest.mock import Mock

import numpy as np
from PIL import Image
import pytest

from draw_to_life.config import Settings
from draw_to_life.description import CharacterDescription
from draw_to_life.generation import LocalGenerator, white_exterior
from draw_to_life.models import ModelError, validate_snapshot


@pytest.mark.parametrize("source", ["dreamshaper", "sd15"])
def test_load_converts_model_scheduler_to_working_dpm(monkeypatch, source):
    import diffusers
    import torch

    config = dict(beta_start=0.00085, beta_end=0.012,
                  beta_schedule="scaled_linear", steps_offset=1)
    if source == "dreamshaper":
        scheduler = diffusers.DEISMultistepScheduler(
            **config, algorithm_type="deis", solver_type="logrho",
            timestep_spacing="leading",
        )
    else:
        scheduler = diffusers.PNDMScheduler(**config, skip_prk_steps=True)
    pipeline = Mock(scheduler=scheduler)
    monkeypatch.setattr(diffusers.ControlNetModel, "from_pretrained", Mock())
    load_pipeline = Mock(return_value=pipeline)
    monkeypatch.setattr(diffusers.StableDiffusionControlNetImg2ImgPipeline,
                        "from_pretrained", load_pipeline)

    generator = LocalGenerator(Settings.from_env())
    generator._load({"image": "unused-image", "control": "unused-control"}, "cpu")
    assert load_pipeline.call_args.kwargs["safety_checker"] is None
    assert load_pipeline.call_args.kwargs["feature_extractor"] is None
    assert load_pipeline.call_args.kwargs["requires_safety_checker"] is False

    converted = generator.pipeline.scheduler
    assert isinstance(converted, diffusers.DPMSolverMultistepScheduler)
    assert converted.config.algorithm_type == "dpmsolver++"
    assert converted.config.solver_type == "midpoint"
    assert converted.config.final_sigmas_type == "zero"
    assert converted.config.beta_schedule == scheduler.config.beta_schedule
    assert torch.equal(converted.betas, scheduler.betas)
    converted.set_timesteps(4)
    sample = torch.ones(1, 4, 8, 8)
    for timestep in converted.timesteps:
        sample = converted.step(torch.zeros_like(sample), timestep, sample).prev_sample
    assert torch.isfinite(sample).all()


def test_white_exterior_does_not_remove_interior_highlights():
    rgb = np.full((40, 40, 3), 235, np.uint8)
    rgb[8:32, 8:32] = [70, 150, 110]
    rgb[15:20, 15:20] = 235
    cleaned = np.array(white_exterior(Image.fromarray(rgb)))
    assert cleaned[0, 0].tolist() == [255, 255, 255]
    assert cleaned[16, 16].tolist() == [235, 235, 235]


def test_damaged_weights_rejected_before_generation(tmp_path):
    (tmp_path / "config.json").write_text("{}")
    (tmp_path / "diffusion_pytorch_model.fp16.safetensors").write_bytes(b"truncated weights")
    with pytest.raises(ModelError, match="dañados"):
        validate_snapshot("control", tmp_path)


def test_cuda_failure_retries_in_cpu_without_changing_size(monkeypatch):
    import torch
    settings = replace(Settings.from_env(), device="auto")
    generator = LocalGenerator(settings)
    monkeypatch.setattr(torch.cuda, "is_available", lambda: True)
    devices = []
    def failing_load(_paths, device):
        devices.append(device)
        raise RuntimeError("CUDA out of memory" if device == "cuda" else "CPU test stop")
    monkeypatch.setattr(generator, "_load", failing_load)
    monkeypatch.setattr(generator, "unload", lambda: None)
    with pytest.raises(RuntimeError, match="CPU test stop"):
        generator.generate({}, Image.new("RGB", (512, 512)), Image.new("RGB", (512, 512)),
                           CharacterDescription(), ["#91CDB5"], "Sticker", False, 42, lambda *_: None)
    assert devices == ["cuda", "cpu"]
    assert generator.settings.image_size == 512


@pytest.mark.parametrize("blank", [False, True])
def test_unfiltered_generation_preserves_texture_and_rejects_blank_output(monkeypatch, blank):
    generator = LocalGenerator(replace(Settings.from_env(), device="cpu"))
    tokenizer = Mock(model_max_length=77)
    tokenizer.return_value = {"input_ids": [1]}
    tokenizer.decode.return_value = "cartoon texture"
    pipeline = Mock(tokenizer=tokenizer)
    image = Image.new("RGB", (32, 32), "white")
    image.paste("green", (8, 8, 24, 24))

    pipeline.return_value = SimpleNamespace(images=[Image.new("RGB", image.size) if blank else image])
    generator.pipeline = pipeline
    monkeypatch.setattr(generator, "_load", lambda *_: None)
    args = ({}, image, image, CharacterDescription(), ["#91CDB5"],
            "Sticker", True, 42, lambda *_: None)
    if blank:
        with pytest.raises(FloatingPointError, match="imagen vacía"):
            generator.generate(*args)
    else:
        assert generator.generate(*args).image.getpixel((16, 16)) == (0, 128, 0)
