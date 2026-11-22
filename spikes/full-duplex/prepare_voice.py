"""Instala una muestra sintética fija como voz de la demo; no usa voces del usuario."""

import hashlib
import json
from pathlib import Path
from urllib.request import urlopen

import soundfile as sf

REPO = Path(__file__).resolve().parents[2]
REVISION = "f3ff3571791e39611d31c381e3a41a3af07b4987"
URL = f"https://huggingface.co/hexgrad/Kokoro-82M/resolve/{REVISION}/samples/HEARME.wav"
SHA256 = "aad38e96fa60c91c995ac820ce6e86c28b0df7300177c0d3ca0766b9dc78feec"


def main():
    root = REPO / "data/full-duplex/reference"
    root.mkdir(parents=True, exist_ok=True)
    source = root / "kokoro-HEARME.wav"
    if not source.exists():
        with urlopen(URL, timeout=120) as response:
            source.write_bytes(response.read())
    if hashlib.sha256(source.read_bytes()).hexdigest() != SHA256:
        raise SystemExit(f"La referencia no coincide con el hash fijado: {source}")
    audio, rate = sf.read(source, dtype="float32")
    assert rate == 24000 and audio.ndim == 1
    voices = REPO / "data/full-duplex/Haru/haru/haru/assets/voices"
    voices.mkdir(exist_ok=True)
    for language in ["en", "es"]:
        destination = voices / f"{language}.flac"
        if not destination.exists():
            sf.write(destination, audio, rate, subtype="PCM_16")
    metadata = {
        "source_url": URL,
        "source_sha256": SHA256,
        "model_license": "Apache-2.0",
        "source_language": "en",
        "seconds": len(audio) / rate,
        "note": "Same synthetic English reference for both languages; no user voice.",
    }
    (root / "metadata.json").write_text(json.dumps(metadata, indent=2) + "\n")
    print(json.dumps(metadata), flush=True)


if __name__ == "__main__":
    main()
