# Instrucciones para agentes

## Referencias de trabajo

- Consulta [README.md](README.md) para conocer el propósito y el estado del proyecto.
- Antes de implementar una funcionalidad, revisa los requisitos y criterios de aceptación pertinentes en [docs/REQUIREMENTS.md](docs/REQUIREMENTS.md). Conserva sus identificadores al referenciarlos.
- Consulta el [plan de specs](docs/specs/README.md), la spec de la tarea y sus contratos compartidos. Respeta la propiedad de cada módulo y resuelve las preguntas bloqueantes del hito antes de integrar interfaces reales.
- Consulta el [plan por iteraciones](docs/ROADMAP.md) para saber qué entra en la iteración actual y con qué simplificaciones. En la iteración 1 aplica el perfil C-09 de [CONTRACTS.md](docs/architecture/CONTRACTS.md) aunque la spec describa el mecanismo completo. No implementes trabajo de una iteración posterior sin acuerdo del equipo.
- En experimentos, sigue la [especificación de métricas](docs/experiments/METRICS.md).
- Al escribir, revisar o refactorizar código, lee y aplica [Karpathy Guidelines](skills/karpathy-guidelines/SKILL.md).

## Equipo y herramientas de IA

| Rol | Persona | Área | Agente |
| --- | --- | --- | --- |
| A | Sebastián | Plataforma: backend, orquestación, audio, consentimiento, historial y cuentas | Codex |
| B | Nicolás | Experiencia y voz: contenido, conversación, frases ancla, borrado y anotaciones | Claude Code |
| C | Ivan | Evaluación: experimentos, evaluador fonético, informe y métricas | Codex |

- Este archivo es la **única fuente** de instrucciones para agentes. Codex lo lee directamente; Claude Code lo carga mediante [CLAUDE.md](CLAUDE.md), que solo lo importa. No agregues reglas del proyecto en `CLAUDE.md` ni en configuraciones personales de una herramienta.
- Los plugins, skills o comandos propios de una herramienta son opcionales y personales. Ninguna tarea del proyecto debe depender de ellos; las pautas compartidas van en `skills/` como Markdown legible por cualquier agente.
- Trabaja en la rama de tu tarea (`<persona>/<spec>-<tema>`, por ejemplo `nicolas/s05-spike-audio`) e integra a `main` mediante pull request pequeño revisado por otro integrante.
- Cada commit o pull request indica la spec y los criterios que toca (por ejemplo, `S05-CA-02`). No modifiques archivos de otro módulo sin acordarlo con su responsable; propón el cambio en el pull request.
- Todos ejecutan la aplicación en `localhost`. No subas datasets, audios, modelos, entornos virtuales ni secretos al repositorio.

## Forma de trabajo

- Comunica en español.
- Resuelve las decisiones pequeñas y reversibles dentro de la tarea y explica los supuestos relevantes. Consulta al usuario cuando una decisión cambie el alcance o dependa de información indispensable que no esté disponible; continúa con el trabajo independiente de esa decisión.
- Distingue requisitos confirmados de decisiones pendientes. Registra las decisiones técnicas y sus motivos en `docs/` cuando se tomen.
- Respeta los cambios existentes del usuario. No borres ni sobrescribas trabajo ajeno.
- En experimentos, registra en `docs/` los modelos, datos, configuración, particiones por hablante y métricas necesarios para reproducir los resultados.

## Organización

- `README.md`: presentación del proyecto, estado y, cuando existan, instrucciones para instalarlo y ejecutarlo.
- `docs/`: requisitos, diseño, decisiones y resultados de experimentos.
- `AGENTS.md`: instrucciones operativas para trabajar en este repositorio. Actualízalas cuando cambien las herramientas o convenciones.
- `skills/`: pautas reutilizables y sus recursos. Conserva la procedencia del material externo junto a la skill correspondiente.
- Al mover archivos, actualiza sus enlaces. Al incorporar herramientas, documenta sus comandos reales.

## Verificación

Para cambios de documentación, comprueba enlaces locales, rutas y coherencia con los requisitos. Al mover documentos, conserva su contenido salvo que se solicite editarlo.

Para cambios de código, ejecuta las comprobaciones pertinentes a las rutas afectadas. Al introducir herramientas de pruebas, formato o análisis, añade aquí los comandos que deban ejecutar los agentes.

Relaciona los cambios con los criterios de la spec afectada y registra su evidencia; marca como satisfechos únicamente los criterios efectivamente comprobados.

Al entregar un cambio, indica qué verificaste y qué quedó sin comprobar. No presentes una comprobación no ejecutada como aprobada.
