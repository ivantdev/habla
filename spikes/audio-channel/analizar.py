"""Análisis desechable del spike (S05-P-01). Uso: python analizar.py <carpeta-de-exportaciones>"""
import json
import math
import sys
from collections import defaultdict
from pathlib import Path


def browser(ua):
    # Edge también contiene "Chrome/", por eso se comprueba primero.
    for marca, nombre in (("Edg/", "edge"), ("Firefox/", "firefox"), ("Chrome/", "chrome")):
        if marca in ua:
            return nombre
    return "otro"


def percentile(values, q):
    """Rango más cercano y un decimal, como pct() de static/app.js."""
    if not values:
        return None
    ordered = sorted(values)
    value = ordered[math.ceil(q * len(ordered)) - 1]
    return math.floor(value * 10 + 0.5) / 10  # Math.round: .5 hacia arriba


def load(directory):
    return [json.loads(p.read_text(encoding="utf-8")) for p in sorted(Path(directory).glob("*.json"))]


def key(export):
    env = export["env"]
    settings = env.get("track_settings") or {}
    aec = settings.get("echoCancellation", env["requested_constraints"].get("echoCancellation"))
    trial = export["trial"]
    return (browser(env["user_agent"]), trial["salida"], aec, trial["prueba"])


def present(values):
    return [v for v in values if v is not None]


def server_total(group, field):
    values = [e["server"][field] for e in group if e.get("server")]
    return sum(values) if values else None


def row(k, group):
    navegador, salida, aec, prueba = k
    interruptions = [i for e in group for i in e["interruptions"]]
    generations = [t for e in group for t in e["tutor"]]
    rtt = present(s for e in group for s in e["rtt_ms"]["samples"])
    stops = present(i["estimated_stop_ms"] for i in interruptions) if prueba == "interrumpir" else []
    acks = present(i["server_ack_ms"] for i in interruptions)
    firsts = present(t["first_frame_after_request_ms"] for t in generations)
    false_rate = None
    if prueba == "silencio" and generations:
        false_rate = round(len(interruptions) / len(generations), 2)
    return {
        "navegador": navegador, "salida": salida, "aec": aec, "prueba": prueba,
        "exportaciones": len(group), "generaciones": len(generations),
        "interrupciones": len(interruptions),
        "falsas_por_generacion": false_rate,
        "parada_p50_ms": percentile(stops, 0.5), "parada_p95_ms": percentile(stops, 0.95),
        "ack_p50_ms": percentile(acks, 0.5),
        "primer_audio_p50_ms": percentile(firsts, 0.5),
        "rtt_p50_ms": percentile(rtt, 0.5), "rtt_p95_ms": percentile(rtt, 0.95),
        "underruns": sum(e["underruns"] for e in group),
        "frames_tardios_descartados": sum(e["late_frames_discarded"] for e in group),
        "huecos": server_total(group, "gaps"),
        "frames_invalidos": server_total(group, "bad_frames"),
        "dominant_hz": present(e["server"].get("dominant_hz") for e in group if e.get("server")),
    }


def rows(exports):
    groups = defaultdict(list)
    for e in exports:
        groups[key(e)].append(e)
    return [row(k, groups[k]) for k in sorted(groups)]


def cell(value):
    if value is None:
        return "–"
    if isinstance(value, bool):
        return "sí" if value else "no"
    if isinstance(value, list):
        return ", ".join(str(v) for v in value)
    return str(value)


def to_markdown(table):
    if not table:
        return ""
    header = list(table[0])
    lines = ["| " + " | ".join(header) + " |", "| " + " | ".join("---" for _ in header) + " |"]
    lines += ["| " + " | ".join(cell(r[h]) for h in header) + " |" for r in table]
    return "\n".join(lines) + "\n"


def main(argv):
    print(to_markdown(rows(load(argv[0]))))


if __name__ == "__main__":
    main(sys.argv[1:])
