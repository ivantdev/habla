# ¡Habla!

Proyecto de Sistemas Inteligentes para practicar conversación en inglés con un tutor de voz y recibir, al finalizar, observaciones de pronunciación, gramática y vocabulario sustentadas en la sesión.

## Estado

La plataforma local de la iteración 1 implementa el flujo C-09 con datos sintéticos. Permite recorrer la práctica, enviar turnos y muestras simuladas, consultar informes y comparar sesiones por sonido. La integración con voz y evaluación reales se valida con Nicolás e Ivan en G1/G2.

La fuente de alcance y criterios de aceptación es [docs/REQUIREMENTS.md](docs/REQUIREMENTS.md). Las tecnologías y parámetros pendientes se decidirán mediante los experimentos descritos allí.

## Funcionamiento previsto

El estudiante elige un nivel, un tema y una duración para conversar en inglés. Al terminar, lee cinco frases ancla y recibe un informe en español con observaciones respaldadas por su sesión. El historial permite consultar informes y comparar la pronunciación entre sesiones.

El alcance completo, las restricciones y los criterios de aceptación están en el documento de requisitos.

## Arranque local

Requiere Python 3.12, [uv](https://docs.astral.sh/uv/), Node.js 22.12 o posterior de la serie 22, o Node.js 24 o posterior, y un navegador de escritorio.

```sh
uv sync --locked --python 3.12
npm ci
```

En una terminal, inicia la API y deja que escuche en loopback.

```sh
uv run --locked python -m uvicorn habla.app:app --host 127.0.0.1 --port 8000 --ws-max-size 8192
```

En otra terminal, inicia la web.

```sh
npm run dev
```

Abre [la práctica local](http://127.0.0.1:3000/practica). La banda superior indica el modo de simulación. Los turnos y las muestras se generan desde los botones. El reloj utiliza los 5 o 10 minutos configurados. La sonda [`/api/v1/health`](http://127.0.0.1:3000/api/v1/health) también comprueba el proxy de Vite.

Para comprobar el recorrido de fallos, inicia la API con `HABLA_MODE=demo` y un `HABLA_DEMO_SCENARIO` de [ADR-003](docs/architecture/ADR-003-fixture-operation.md). Este ejemplo configura un validador que rechaza las tres muestras.

```powershell
$env:HABLA_MODE = "demo"
$env:HABLA_DEMO_SCENARIO = "anchor_invalid"
uv run --locked python -m uvicorn habla.app:app --host 127.0.0.1 --port 8000 --ws-max-size 8192
```

En PowerShell, `npm.cmd` permite usar los comandos de npm cuando la política de ejecución local bloquea `npm.ps1`.

## Comprobaciones

```sh
uv run --locked pytest
npm test
npm run build
```

Los [fixtures v1](contracts/fixtures/platform-v1.json) y el [esquema compartido](contracts/v1.json) permiten probar productores y consumidores sin GPU. Consulta [las decisiones de arranque](docs/architecture/ADR-001-local-development.md) y [la evidencia de verificación](docs/verification/PLATFORM-ITERATION-1.md).

## Documentación

- [Requisitos del MVP](docs/REQUIREMENTS.md): alcance, decisiones pendientes y criterios de aceptación.
- [Plan por iteraciones](docs/ROADMAP.md): recorte del MVP, reparto por persona y demo del *Shark Tank*.
- [Especificaciones y plan de construcción](docs/specs/README.md): módulos, contratos, etapas y reparto del trabajo entre tres personas.
- [Métricas de evaluación](docs/experiments/METRICS.md): qué se mide, cómo y quién lo ejecuta.
