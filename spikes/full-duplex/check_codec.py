"""Reconstruye la referencia con el códec; excluye LLM y generación de voz."""

import json
from pathlib import Path

import numpy as np
import soundfile as sf
import torch
from safetensors import safe_open
from transformers.initialization import no_init_weights

from haru.config import HaruConfig
from haru.models.vibevoice_codec import VibeVoiceCodec, open_stream

REPO = Path(__file__).resolve().parents[2]
MODEL = REPO / "data/full-duplex/model"
OUT = Path(__file__).resolve().parent / "out"


@torch.inference_mode()
def main():
    config = HaruConfig.from_file(MODEL / "config.json")
    with no_init_weights():
        codec = VibeVoiceCodec(config.codec)
    with safe_open(MODEL / "model.safetensors", framework="pt", device="cuda:0") as weights:
        state = {key.removeprefix("codec."): weights.get_tensor(key)
                 for key in weights.keys() if key.startswith("codec.")}
    codec.load_state_dict(state, strict=True, assign=True)
    codec.eval().requires_grad_(False)
    audio, rate = sf.read(REPO / "data/full-duplex/reference/kokoro-HEARME.wav", dtype="float32")
    assert rate == config.sample_rate and audio.ndim == 1
    frame_size = config.frame_samples
    padded = np.pad(audio, (0, (-len(audio)) % frame_size))
    stream = open_stream(codec, backend="torch")
    chunks = []
    for start in range(0, len(padded), frame_size):
        latent = stream.encode(torch.from_numpy(padded[start:start + frame_size])[None])
        chunks.append(stream.decode(latent)[0].float().cpu().numpy())
    reconstructed = np.concatenate(chunks)[:len(audio)]
    assert np.isfinite(reconstructed).all()
    OUT.mkdir(exist_ok=True)
    sf.write(OUT / "codec-reference-original.wav", audio, rate)
    sf.write(OUT / "codec-reference-roundtrip.wav", reconstructed, rate)
    print(json.dumps({"gpu": torch.cuda.get_device_name(), "seconds": len(audio)/rate,
                      "latent_sampling": "mean only; no noise", "finite": True,
                      "input_rms": float(np.sqrt(np.mean(audio**2))),
                      "output_rms": float(np.sqrt(np.mean(reconstructed**2)))}))


if __name__ == "__main__":
    main()
