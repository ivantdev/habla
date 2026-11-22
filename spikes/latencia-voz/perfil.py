"""Micro-banco de configuraciones de llama-server (S05-P-02).

Repite turnos de la conversación base de una corrida de calidad.py contra el
llama-server que esté arrancado, para comparar opciones del servidor
(--swa-full, checkpoints, decodificación especulativa, reparto entre GPU…) sin
lanzar la prueba completa.

Los turnos se recorren en orden y la lista se repite --reps veces. Un turno que
sigue al anterior (6 tras 5) solo añade la última intervención al historial: es
el caso real de una conversación, con la caché aprovechada. Un salto (volver al
5 tras el 27) recalcula el prompt casi entero. La tabla separa los dos tipos.

Uso, desde spikes/latencia-voz/ y con el servidor ya arrancado:
    python perfil.py --from out/calidad-<fecha>.json --label G0 --pid-file ~/modelos-habla/llama-server.pid
"""
import argparse
import json
import statistics as st
from datetime import datetime
from pathlib import Path

import httpx

import bench
import calidad


def history(run, turn):
    """Mensajes enviados en el turno `turn` de la conversación base de `run`."""
    msgs = []
    for row in run["base"]:
        if row["turn"] == turn:
            break
        if row["user"]:
            msgs.append({"role": "user", "content": row["asr_text"] or "[inaudible]"})
        msgs.append({"role": "assistant", "content": row["text"]})
    row = next(r for r in run["base"] if r["turn"] == turn)
    msgs.append({"role": "user", "content": row["asr_text"] or "[inaudible]"})
    return [calidad.system("conversation")] + msgs


def rss_gb(pid_file):
    if not pid_file:
        return None
    pid = Path(pid_file).expanduser().read_text().strip()
    for line in Path(f"/proc/{pid}/status").read_text().splitlines():
        if line.startswith("VmRSS:"):
            return round(int(line.split()[1]) / 1e6, 2)
    return None


def med(values):
    values = [v for v in values if v is not None]
    return round(st.median(values), 1) if values else None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--from", dest="source", type=Path, required=True, help="JSON de una corrida de calidad.py")
    ap.add_argument("--turns", default="5,6,7,26,27")
    ap.add_argument("--reps", type=int, default=5)
    ap.add_argument("--max-tokens", type=int, default=120)
    ap.add_argument("--llm-url", default="http://127.0.0.1:8081")
    ap.add_argument("--pid-file", default="", help="Archivo con el PID de llama-server, para medir su RSS")
    ap.add_argument("--label", default="")
    args = ap.parse_args()

    run = json.loads(args.source.read_text())
    turns = [int(t) for t in args.turns.split(",")]
    rows = []
    with httpx.Client(timeout=300) as client:
        bench.llm(client, args.llm_url, history(run, turns[0]), True, 8)  # calentamiento
        prev = None
        for rep in range(args.reps):
            for turn in turns:
                out = bench.llm(client, args.llm_url, history(run, turn), True, args.max_tokens)
                kind = "incremental" if prev == turn - 1 else "salto"
                rows.append({"rep": rep + 1, "turn": turn, "tipo": kind, "rss_gb": rss_gb(args.pid_file), **out})
                prev = turn
                acc = (f" acept {out['draft_n_accepted']}/{out['draft_n']}" if out.get("draft_n") else "")
                print(f"r{rep + 1} T{turn} {kind:11} n={out['prompt_n']} prefill={out['prompt_ms'] or 0:.0f} "
                      f"ttft={out['ttft_ms'] or -1:.0f} frase={out['first_sentence_ms']:.0f} "
                      f"tok/s={out['predicted_per_second'] or 0:.1f}{acc} | {out['text'][:60]}", flush=True)

    summary = {}
    for kind in ("incremental", "salto"):
        sel = [r for r in rows if r["tipo"] == kind]
        if not sel:
            continue
        drafted = sum(r["draft_n"] or 0 for r in sel)
        summary[kind] = {
            "n": len(sel),
            "prompt_n": med(r["prompt_n"] for r in sel),
            "prefill_ms": med(r["prompt_ms"] for r in sel),
            "ttft_ms": med(r["ttft_ms"] for r in sel),
            "primera_frase_ms": med(r["first_sentence_ms"] for r in sel),
            "tok_s": med(r["predicted_per_second"] for r in sel),
            "aceptacion": round(sum(r["draft_n_accepted"] or 0 for r in sel) / drafted, 2) if drafted else None,
        }
    summary["vacias"] = sum(not r["text"] for r in rows)
    summary["rss_max_gb"] = max((r["rss_gb"] for r in rows if r["rss_gb"] is not None), default=None)

    print(f"\n{args.label}: " + json.dumps(summary, ensure_ascii=False))
    bench.OUT.mkdir(exist_ok=True)
    path = bench.OUT / f"perfil-{args.label or 'sin-etiqueta'}-{datetime.now():%Y%m%d-%H%M%S}.json"
    path.write_text(json.dumps({"label": args.label, "args": {k: str(v) for k, v in vars(args).items()},
                                "resumen": summary, "filas": rows}, indent=2, ensure_ascii=False))
    print(f"Resultados en {path}")


if __name__ == "__main__":
    main()
