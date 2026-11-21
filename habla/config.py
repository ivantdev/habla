from dataclasses import dataclass
from pathlib import Path
import os
import re


LOCAL_ORIGINS = frozenset(
    f"http://{host}:{port}"
    for host in ("127.0.0.1", "localhost")
    for port in (3000, 8000)
)
DEMO_SCENARIOS = frozenset({
    "normal", "anchor_invalid", "anchor_fail_once", "asr_fail_once",
    "tutor_fail_once", "tts_fail_once", "report_fail_once", "report_unavailable",
    "commit_fail_once", "slow_evaluation",
})


@dataclass(frozen=True)
class Settings:
    data_dir: Path
    mode: str = "fixture"
    scenario: str = "normal"
    corpus_member: str | None = None
    ready_seconds: float = 30
    retry_seconds: float = 30
    model_seconds: float = 10
    upload_seconds: float = 10
    max_anchor_seconds: int = 15

    def __post_init__(self):
        root = Path(__file__).resolve().parent.parent
        if any(self.data_dir.resolve().is_relative_to(root / name) for name in ("web", "contracts", "node_modules")):
            raise RuntimeError("HABLA_DATA_DIR debe indicar una carpeta privada fuera de la entrada web.")

    @classmethod
    def from_env(cls):
        mode = os.getenv("HABLA_MODE", "fixture")
        if mode not in {"fixture", "demo"}:
            raise RuntimeError("HABLA_MODE debe ser fixture o demo.")
        scenario = os.getenv("HABLA_DEMO_SCENARIO", "normal")
        if scenario not in DEMO_SCENARIOS or (scenario != "normal" and mode != "demo"):
            raise RuntimeError("HABLA_DEMO_SCENARIO requiere un escenario del modo demo.")
        corpus = os.getenv("HABLA_CORPUS_ENABLED", "0")
        if corpus not in {"0", "1"}:
            raise RuntimeError("HABLA_CORPUS_ENABLED debe ser 0 o 1.")
        member = os.getenv("HABLA_CORPUS_MEMBER") if corpus == "1" else None
        if corpus == "1" and (not member or not re.fullmatch(r"[A-Za-z0-9_-]{1,40}", member)):
            raise RuntimeError("HABLA_CORPUS_MEMBER es obligatorio para el corpus y debe ser un alias simple.")
        directory = os.getenv("HABLA_DATA_DIR", "data")
        if not directory:
            raise RuntimeError("HABLA_DATA_DIR debe indicar una carpeta.")
        return cls(Path(directory).resolve(), mode, scenario, member)
