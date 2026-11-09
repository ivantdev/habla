"""Pruebas del análisis de exportaciones del spike (tarjeta T3)."""
import json

import pytest

import analizar

CHROME = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/141.0.0.0 Safari/537.36"
EDGE = CHROME + " Edg/141.0.0.0"
FIREFOX = "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:144.0) Gecko/20100101 Firefox/144.0"


def export(ua=CHROME, salida="parlantes", prueba="interrumpir", aec_pedido=True, aec_real=True,
           paradas=(), acks=(), primeros=(), rtt=(), underruns=0, descartados=0, server=None):
    """Exportación mínima con la forma de summary() en static/app.js tras la tarjeta T2."""
    track = {} if aec_real is None else {"echoCancellation": aec_real}
    return {
        "env": {"user_agent": ua, "requested_constraints": {"echoCancellation": aec_pedido},
                "track_settings": track},
        "trial": {"salida": salida, "prueba": prueba},
        "rtt_ms": {"n": len(rtt), "samples": list(rtt)},
        "interruptions": [{"estimated_stop_ms": p, "server_ack_ms": a} for p, a in zip(paradas, acks)],
        "tutor": [{"first_frame_after_request_ms": f} for f in primeros],
        "underruns": underruns,
        "late_frames_discarded": descartados,
        "server": server,
    }


def write(tmp_path, *exports):
    for i, e in enumerate(exports):
        (tmp_path / f"spike-audio-{i}.json").write_text(json.dumps(e), encoding="utf-8")
    (tmp_path / "notas.txt").write_text("no es una exportación", encoding="utf-8")
    return tmp_path


@pytest.mark.parametrize("ua, esperado", [(CHROME, "chrome"), (EDGE, "edge"), (FIREFOX, "firefox"),
                                          ("curl/8.0", "otro")])
def test_navegador(ua, esperado):
    assert analizar.browser(ua) == esperado


def test_percentil_por_rango_mas_cercano_como_app_js():
    assert analizar.percentile([], 0.5) is None
    assert analizar.percentile([30, 10, 20, 40], 0.5) == 20
    assert analizar.percentile([30, 10, 20, 40], 0.95) == 40
    assert analizar.percentile([1.26], 0.5) == 1.3  # redondeo a un decimal, como pct() en app.js


def test_load_lee_solo_json_del_directorio(tmp_path):
    write(tmp_path, export(), export(prueba="silencio"))
    assert len(analizar.load(tmp_path)) == 2


def test_agrupa_y_calcula_una_fila_de_interrupcion():
    a = export(paradas=[100, 300], acks=[20, 40], primeros=[500], rtt=[2, 4], underruns=1, descartados=10,
               server={"gaps": 0, "bad_frames": 1, "dominant_hz": None})
    b = export(paradas=[200], acks=[None], primeros=[700], rtt=[6], descartados=5,
               server={"gaps": 2, "bad_frames": 0, "dominant_hz": None})
    [row] = analizar.rows([a, b])
    assert row == {
        "navegador": "chrome", "salida": "parlantes", "aec": True, "prueba": "interrumpir",
        "exportaciones": 2, "generaciones": 2, "interrupciones": 3,
        "falsas_por_generacion": None,
        "parada_p50_ms": 200, "parada_p95_ms": 300,
        "ack_p50_ms": 20,  # los ack nulos se ignoran
        "primer_audio_p50_ms": 500,
        "rtt_p50_ms": 4, "rtt_p95_ms": 6,
        "underruns": 1, "frames_tardios_descartados": 15,
        "huecos": 2, "frames_invalidos": 1,
        "dominant_hz": [],
    }


def test_en_silencio_toda_interrupcion_es_falsa_y_no_cuenta_como_parada():
    e = export(prueba="silencio", paradas=[150], acks=[30], primeros=[400, 410, 420, 430])
    [row] = analizar.rows([e])
    assert row["interrupciones"] == 1 and row["generaciones"] == 4
    assert row["falsas_por_generacion"] == 0.25
    assert row["parada_p50_ms"] is None and row["parada_p95_ms"] is None


def test_aec_usa_el_ajuste_real_de_la_pista_y_si_falta_el_pedido():
    ignorado = export(aec_pedido=True, aec_real=False)
    sin_ajuste = export(aec_pedido=False, aec_real=None)
    assert [r["aec"] for r in analizar.rows([ignorado])] == [False]
    assert [r["aec"] for r in analizar.rows([sin_ajuste])] == [False]
    assert len(analizar.rows([ignorado, export()])) == 2  # aec distinto: grupos distintos


def test_sin_estadisticas_del_servidor_los_contadores_quedan_desconocidos():
    [row] = analizar.rows([export(server=None)])
    assert row["huecos"] is None and row["frames_invalidos"] is None


def test_tono_reporta_la_frecuencia_dominante():
    e = export(prueba="tono", server={"gaps": 0, "bad_frames": 0, "dominant_hz": 1000.2})
    [row] = analizar.rows([e])
    assert row["dominant_hz"] == [1000.2]


def test_filas_ordenadas_por_grupo():
    filas = analizar.rows([export(ua=FIREFOX), export(salida="auriculares"), export(prueba="silencio")])
    claves = [(r["navegador"], r["salida"], r["aec"], r["prueba"]) for r in filas]
    assert claves == sorted(claves)


def test_markdown():
    filas = analizar.rows([export(paradas=[100], acks=[None]), export(prueba="tono",
                           server={"gaps": 0, "bad_frames": 0, "dominant_hz": 999.5})])
    md = analizar.to_markdown(filas).strip().splitlines()
    assert len(md) == 2 + len(filas)
    assert md[0].startswith("| navegador | salida | aec | prueba |")
    assert md[1].startswith("| --- |")
    assert "| sí |" in md[2] and "–" in md[2]  # booleano en español y nulos como raya
    assert "999.5" in md[3]


def test_cli_imprime_la_tabla(tmp_path, capsys):
    write(tmp_path, export(paradas=[100], acks=[10]))
    analizar.main([str(tmp_path)])
    out = capsys.readouterr().out
    assert "| chrome | parlantes | sí | interrumpir |" in out
