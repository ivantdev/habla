# SPEC-NN — <Título>

> **Estado:** Borrador | **Prioridad:** P1/P2/P3/Futuro | **Dominio:** <dominio>  
> **RF relacionados:** <IDs del catálogo> | **RNF:** <IDs> | **RT:** <IDs>  
> **Módulo:** <módulo lógico> | **Responsable:** <persona y revisores>  
> **Etapa:** <etapa> | **Iteración:** <1, 2 o ambas, según el plan por iteraciones> | **Versión:** 1.0 | **Actualizado:** <fecha>

## 1. Contexto y problema

Necesidad, fuente y distinción entre hechos, decisiones y propuestas. Referenciar catálogo y arquitectura de docs. No inventar citas.

## 2. Estado del sistema y brecha

Qué existe realmente y qué falta. No suponer frontend, backend ni rutas de código inexistentes.

## 3. Historia de usuario

> Como <actor>, quiero <capacidad>, para <beneficio>.

Actores secundarios, permisos y propiedad.

## 4. Alcance

### Dentro del alcance de la spec

- <entregable>

### Fuera del alcance de la spec

- <no objetivo>

### Supuestos acordados

- <confirmado y su origen; propuestas identificadas por separado>

## 5. Requisitos funcionales

- **SNN-RF-01** (<fuente RF/RNF/RT o derivado explícito>) — CUANDO <evento>, EL SISTEMA DEBE <respuesta observable>.

## 6. Criterios de aceptación

- [ ] **SNN-CA-01** (SNN-RF-01) — Dado <precondición>, Cuando <evento>, Entonces <resultado comprobable>.

## 7. Diseño técnico y datos

Ubicación, autoridad de datos y entidades; interfaz HTTP, esquemas, permisos, errores e idempotencia; eventos, orden y duplicados; frontend y accesibilidad; proxy/ruta/puerto compartido; tecnologías propuestas y ADR requerido. Referenciar los contratos únicos en arquitectura; declarar no aplica cuando corresponda.

## 8. Dependencias y contratos de integración

| Dependencia/consumidor | Propósito | Contrato o dato intercambiado | Modo de fallo |
| --- | --- | --- | --- |
| <origen → destino> | <propósito> | <DTO/contrato> | <respuesta> |

Indicar autoridad, autenticación, plazos, reintentos y aislamiento de almacenamiento.

## 9. Decisiones y preguntas abiertas

### Decisiones tomadas

- **SNN-D-01** — <decisión, origen y fecha>.

### Preguntas abiertas

- **SNN-P-01 — bloqueante/no bloqueante:** <pregunta; responsable, gate/fecha e integración que bloquea>.

## 10. Verificación

**Estado:** plan; distinguir pruebas propuestas de ejecutadas.

| RF/RNF/RT | Prueba o inspección | Evidencia esperada |
| --- | --- | --- |
| SNN-RF-01 → SNN-CA-01 | <tipo y escenario> | <artefacto observable> |

Cubrir todos los requisitos locales y RNF/RT aplicables, incluyendo límites, errores, permisos y contratos.

## 11. Esfuerzo, riesgos y consecuencias

- **Esfuerzo:** S/M/L y tareas principales.
- **Riesgos:** técnicos, datos, integración, seguridad y disponibilidad del equipo.
- **Consecuencias:** límites y trabajo aplazado.
