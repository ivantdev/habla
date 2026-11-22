"""Demo oficial con medidas de señal y cómputo; no guarda audio ni texto."""

import json
import logging
import time
import uuid
from pathlib import Path

import numpy as np

from haru import server

OUT = Path(__file__).resolve().parent / "out"
logger = logging.getLogger("haru.diagnostics")


def level(audio):
    audio = np.asarray(audio, dtype=np.float64)
    rms = float(np.sqrt(np.mean(audio ** 2)))
    return {
        "rms_dbfs": 20 * float(np.log10(max(rms, 1e-12))),
        "peak": float(np.max(np.abs(audio))),
        "finite": bool(np.isfinite(audio).all()),
    }


class ObservedConversation:
    def __init__(self, conversation):
        self.conversation = conversation
        self.frames = []
        self.started = time.perf_counter()
        self.identifier = uuid.uuid4().hex[:8]

    async def step(self, audio):
        arrival = time.perf_counter() - self.started
        incoming = level(audio)
        frame = await self.conversation.step(audio)
        self.frames.append({
            "arrival_seconds": arrival,
            "input": incoming,
            "output": level(frame.audio),
            "compute_ms": frame.seconds * 1000,
        })
        if len(self.frames) % 75 == 0:
            self.report()
        return frame

    def report(self):
        if not self.frames:
            return {}
        summary = {
            "frames": len(self.frames),
            "input_rms_dbfs_p50_p95_max": np.percentile(
                [row["input"]["rms_dbfs"] for row in self.frames], [50, 95, 100]
            ).tolist(),
            "input_peak_max": max(row["input"]["peak"] for row in self.frames),
            "compute_ms_p50_p95_max": np.percentile(
                [row["compute_ms"] for row in self.frames], [50, 95, 100]
            ).tolist(),
            "compute_over_frame_budget": sum(row["compute_ms"] > 1000 / 7.5 for row in self.frames),
        }
        logger.info("probe %s: %s", self.identifier, json.dumps(summary))
        return summary

    def save(self):
        OUT.mkdir(exist_ok=True)
        path = OUT / f"signal-{self.identifier}.json"
        path.write_text(json.dumps({
            "summary": self.report(), "frames": self.frames,
            "note": "Signal energy is not VAD or proof of speech recognition.",
        }, indent=2) + "\n")
        logger.info("probe %s: saved %s", self.identifier, path)


class DiagnosticServer(server.DemoServer):
    async def _converse(self, ws, conversation, first):
        observed = ObservedConversation(conversation)
        logger.info("probe %s: started", observed.identifier)
        try:
            return await super()._converse(ws, observed, first)
        finally:
            observed.save()


if __name__ == "__main__":
    server.DemoServer = DiagnosticServer
    server.main()
