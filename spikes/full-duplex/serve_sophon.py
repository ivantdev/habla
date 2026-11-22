"""Arranque oficial con adaptación explícita de las preguntas de turno para ES."""

import sophon_realtime


def main():
    sophon_realtime.register()
    from sophon_realtime import duplex

    # El talker ya contempla es, pero la política solo define preguntas en en/zh.
    # Reusar las preguntas inglesas evita KeyError sin fingir entrenamiento ES.
    duplex.TURN_Q["es"] = duplex.TURN_Q["en"]
    duplex.TPL["es"] = duplex.TPL["en"]
    duplex.SYS["es"] = duplex.SYS["en"] + " Reply only in Spanish."
    print("Sophon: ES experimental; preguntas de turno EN, idioma de voz ES.", flush=True)
    from vllm.entrypoints.cli.main import main as vllm_main

    vllm_main()


if __name__ == "__main__":
    main()
