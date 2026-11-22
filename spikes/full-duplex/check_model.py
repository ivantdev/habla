"""Comprueba carga e inferencia con silencio; no evalúa comprensión de voz."""

import json
import time
from datetime import datetime, timezone
from importlib.metadata import version
from pathlib import Path

import numpy as np
import torch

from haru import DuplexConfig, DuplexSession
from haru.audio import save_audio
from haru.models import load_model
from haru.prompt import card_templates, render_card

REPO = Path(__file__).resolve().parents[2]
OUT = Path(__file__).resolve().parent / "out"


def main():
    if not torch.cuda.is_available():
        raise SystemExit("CUDA no está disponible; comprueba nvidia-smi y el entorno.")
    OUT.mkdir(exist_ok=True)
    started = time.perf_counter()
    model = load_model(str(REPO / "data/full-duplex/model"), device="cuda")
    torch.cuda.synchronize()
    result = {
        "check": "silence_and_speak_first_without_voice_reference",
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "gpu": torch.cuda.get_device_name(),
        "torch": torch.__version__,
        "cuda": torch.version.cuda,
        "transformers": version("transformers"),
        "codec_backend": "torch",
        "seed": 20261120,
        "load_seconds": time.perf_counter() - started,
        "runs": [],
    }
    for language, persona, situation in [
        ("en", "Sofia is a friendly, curious conversation partner. She speaks English.",
         "A relaxed conversation about food. Sofia introduces herself briefly."),
        ("es", "Sofía es una compañera de conversación amable y curiosa. Habla español.",
         "Una conversación tranquila sobre comida. Sofía se presenta brevemente."),
    ]:
        card = render_card(
            {"persona": persona, "name": "Sofia", "situation": situation},
            card_templates()["templates"][language],
        )
        torch.cuda.reset_peak_memory_stats()
        config = DuplexConfig(seed=20261120, speak_first=True, max_frames=91)
        session = DuplexSession(model, card, config=config)
        frames = [session.start()]
        silence = np.zeros(model.config.frame_samples, dtype=np.float32)
        for _ in range(89):
            frames.append(session.step(silence))
        audio = np.concatenate([frame.audio for frame in frames])
        if not np.isfinite(audio).all():
            raise RuntimeError(f"Salida no finita en {language}")
        save_audio(OUT / f"silence-{language}.wav", audio)
        run = {
            "card_language": language,
            "system_prompt": card,
            "input": "89 frames of synthetic silence; no human speech",
            "input_seconds": 89 * model.config.frame_samples / model.config.sample_rate,
            "output_seconds": len(audio) / model.config.sample_rate,
            "voice_reference": None,
            "text": "".join(frame.text for frame in frames),
            "startup_ms": frames[0].seconds * 1000,
            "frame_ms_p50_p95_max": np.percentile(
                [frame.seconds * 1000 for frame in frames[1:]], [50, 95, 100]
            ).tolist(),
            "audio_rms": float(np.sqrt(np.mean(audio ** 2))),
            "peak_allocated_mib": torch.cuda.max_memory_allocated() / 2**20,
        }
        result["runs"].append(run)
        print(json.dumps(run, ensure_ascii=False), flush=True)
        del session, frames
    (OUT / "check-model.json").write_text(
        json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )


if __name__ == "__main__":
    main()
