# Fichas de temas

**Estado:** propuesta; esquema y una ficha de ejemplo (restaurante), pendiente de revisión de Ivan (C). Faltan las otras cuatro fichas: `job_interview`, `weekend`, `travel` y `news`. **Fecha:** 2026-11-12. **Responsable:** Nicolás (B).
**Requisitos:** RF-01, S02-RF-01, S02-RF-04, S02-P-01 (parte de fichas). **Relacionado:** [política del tutor](POLITICA-TUTOR.md), [SPEC-02](../specs/SPEC-02-content-and-catalog.md) y C-02 de los [contratos](../architecture/CONTRACTS.md).

Una ficha da al tutor el escenario y los objetivos de vocabulario y estructuras de un tema por nivel (RF-01). Hay cinco temas × tres niveles, es decir, quince combinaciones. La ficha entra al prompt del tutor tal como se describe en la sección 3 de la [política](POLITICA-TUTOR.md).

## 1. Esquema

La ficha es el DTO `Topic` de C-02 (`id,label_es,objectives_by_level`) sin campos nuevos. El contenido por nivel va dentro de `objectives_by_level`:

| Campo | Tipo | Uso |
| --- | --- | --- |
| `id` | Uno de `restaurant,job_interview,weekend,travel,news` | Identificador estable (C-02) |
| `label_es` | Texto | Nombre en la interfaz, en español (RNF-12) |
| `objectives_by_level.<nivel>` | Objeto para `A2`, `B1` y `B2` | Contenido de la combinación tema-nivel |
| `.scenario_en` | Texto en inglés, una o dos frases | `{topic_scenario}` del prompt |
| `.vocabulary` | Lista de 8 a 12 palabras o expresiones en inglés | `{vocabulary}`; objetivo de vocabulario |
| `.structures` | Lista de 3 a 5 estructuras en inglés | `{structures}`; objetivo de estructuras |
| `.starter_questions` | Lista de 2 o 3 preguntas en inglés | `{starter_questions}`; ideas para llevar la charla al tema |

Los objetivos orientan al tutor; no son una lista que el estudiante deba cumplir ni criterios del informe. Las estructuras siguen los descriptores del MCER usados en la sección 2 de la política.

## 2. Ficha `restaurant`

```json
{
  "id": "restaurant",
  "label_es": "Restaurante",
  "objectives_by_level": {
    "A2": {
      "scenario_en": "Talking about favorite food and ordering food and drinks in a casual restaurant.",
      "vocabulary": ["menu", "order", "starter", "main course", "dessert", "drink", "waiter", "the bill", "table for two", "spicy", "delicious"],
      "structures": ["I'd like ...", "Can I have ...?", "How much is ...?", "I like / I don't like ...", "There is / There are ..."],
      "starter_questions": ["What kind of food do you like?", "Do you often eat at restaurants?", "What do you usually order?"]
    },
    "B1": {
      "scenario_en": "Choosing a restaurant, ordering a meal, dealing with a simple problem such as a wrong dish, and describing a past meal.",
      "vocabulary": ["reservation", "recommend", "dish", "ingredients", "vegetarian", "allergic to", "portion", "service", "tip", "takeaway"],
      "structures": ["Could you ...?", "Past simple to tell an experience", "I'd rather ...", "Comparatives (cheaper than, better than)", "Would you recommend ...?"],
      "starter_questions": ["Tell me about a restaurant you enjoyed recently.", "What would you order at a new restaurant?", "Has a restaurant ever got your order wrong?"]
    },
    "B2": {
      "scenario_en": "Discussing dining experiences and food culture, handling a complaint politely, and comparing eating out with cooking at home.",
      "vocabulary": ["overpriced", "atmosphere", "complimentary", "dietary restrictions", "to make a complaint", "local cuisine", "sustainable", "worth it", "to split the bill"],
      "structures": ["Present perfect for experiences (I've never tried ...)", "Second conditional (If I opened a restaurant, ...)", "Polite complaints (I'm afraid ..., I was wondering if ...)", "Passive voice (The food was served cold)"],
      "starter_questions": ["What makes a restaurant worth its price?", "How would you handle a disappointing meal?", "Do you think eating out has changed in your city?"]
    }
  }
}
```

## 3. Pendientes

- Las fichas de `job_interview`, `weekend`, `travel` y `news`, con el mismo esquema. La de `news` debe orientar a hechos de actualidad tratados de forma neutral (POL-09).
- Revisión de Ivan del nivel de cada ficha frente al MCER.
- Al cerrar las quince fichas, publicarlas en el manifiesto versionado del catálogo (SPEC-02) y añadir los casos del tutor por tema y nivel (METRICS §8).
