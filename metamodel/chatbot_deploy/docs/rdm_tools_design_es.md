# Diseño de tools con RDM integrado — borrador v0

*Documento de trabajo, rama `rdm-tools`, 2026-09-30. En español, como `plan_trabajo_es.md`:
es un borrador de diseño para iterar, no un entregable. Sustituye la arquitectura de tools
actual (`run_simulation`, `get_scenario_variables`, …) en esta rama; `metamodel` queda intacta.*

---

## Principios

1. **RDM está en las tools, no en el prompt.** Toda evaluación de una política es un ensemble;
   ninguna tool devuelve un único número de un único futuro.
2. **L se decide, X se muestrea.** Las palancas fuera de la política valen 0 (una decisión: no
   activarla). Las 13 X se muestrean siempre, salvo que la pregunta las condicione a un rango.
3. **Foco = lo que se muestra, no lo que se mueve.** Las 13 X se mueven; el mapa de
   vulnerabilidad se proyecta sobre 2 X — por defecto las 2 que más explican el cumplimiento de
   esa política, o las que pida el usuario. La variación del resto aparece como porcentaje de
   cumplimiento dentro de cada celda y se reporta cuánto aporta.
   *(Pendiente de validar con el experto del equipo: qué valor toma una X cuando no se varía.)*
4. **Cada tool tiene una sola fuente de datos, fija.** Preguntas sobre el *sistema* → corridas
   reales de SISEPUEDE (tablas precalculadas). Preguntas sobre *una política concreta* → XGBoost.
   El agente elige la tool, nunca la fuente.
5. **Todo experimento se declara antes de correr** (XLRM + criterio de robustez) y el usuario lo
   confirma. La declaración registra la categoría de la pregunta, que se evalúa.

---

## Tools

| # | Tool | Paso RDM | Inputs | Outputs | Fuente |
|---|---|---|---|---|---|
| 1 | `consultar_mapa` | información | `palancas` (ids) **o** `output` (sector/métrica + año); `modo`: por_palanca / por_output | Por palanca: outputs que mueve, cambio 0→1 (mediana, p10–p90), forma de la curva, variable tangible titular, X que más altera su efecto. Por output: nivel típico y rango, palancas y X que lo explican (con su participación), 2 X sugeridas para el foco | Emisiones/costos: `lever_response_map.json` (hoy desde el XGBoost; recalcular desde corridas reales y usar la diferencia como chequeo de fidelidad). Variables tangibles: hipercubo real |
| 2 | `traducir_meta` | información (inverso) | `variable_tangible` (o palanca), `valor_objetivo`, `año`, `condicion_X` opcional | Nivel de L necesario por región de X (p. ej. por tercil de PIB), si es alcanzable, máximo alcanzable, distribución de la variable a ese nivel | Hipercubo real: tablas L*i* × X*j* → variable tangible (~4.000 corridas por celda) |
| 3 | `definir_experimento` | 1 · plantear (XLRM) | `tipo_de_pregunta` (A1–F4); `politicas` (1+ vectores; cada palanca con valor o rango); `incertidumbres`: `todas` o `condicionado` {X: rango}; `x_a_mostrar` (≤2, opcional); `metricas` (outputs + años); `criterio` (métrica, umbral, dirección, % mínimo de futuros) | `experimento_id`, planteamiento en lenguaje claro para que el usuario lo confirme, advertencias (id desconocido, X usada como palanca, falta criterio, X elegida que explica <1%) | Registro de features + mapa (solo para validar) |
| 4 | `correr_experimento` | 2 · generar casos | `experimento_id`, `n_futuros` (por defecto 1.000) | Por política: distribución por métrica (mediana, p10, p90), cambio pareado vs BAU en los mismos futuros, % de futuros que cumplen el criterio, banderas de extrapolación. Guarda el ensemble (`ensemble_id`) | XGBoost |
| 5 | `descubrir_vulnerabilidades` | 3 · scenario discovery | `ensemble_id`, `politica`, `x_a_mostrar` opcional | Reglas de falla sobre las 13 X (CART: condición, cobertura, densidad), las 2 X más importantes, mapa X₁ × X₂ con % de cumplimiento por celda, cuánto aportan las X no mostradas | XGBoost (el ensemble ya corrido) |
| 6 | `evidencia_mecanismo` | 3b · explicar el porqué | región de X (de la tool 5), palancas de la política, variables intermedias | Variables intermedias dentro vs fuera de la región de falla (p. ej. demanda eléctrica con PIB alto vs resto), con palancas en rango similar | Hipercubo real (todos los outputs de SISEPUEDE) |
| 7 | `comparar_politicas` | 4 · trade-offs | `ensemble_id` con ≥2 políticas en los mismos futuros | Por política: robustez (%), emisiones, costos, beneficios, neto; regret por futuro (máx. y p90); políticas dominadas | XGBoost |
| 8 | `buscar_politica` | 5 · diseñar / iterar | `experimento_id` con la meta como criterio; `palancas_candidatas` (+ rangos; por defecto desde el mapa); `restricciones` (costo, nº de palancas); `robustez_requerida` | Pocas políticas candidatas que cumplen en ≥ p% de futuros (las de menor ambición), o el máximo alcanzable si es inviable | XGBoost (búsqueda sobre L, ensemble común de X) |
| 9 | `get_pathway_results` | referencia | estrategia oficial | Trayectorias de la estrategia | Corridas reales (pathways) |
| 10 | `get_country_context` | contexto | sector / tema | Inventario y contexto del país | Inventario |

**Cambios respecto a la versión actual:** `run_simulation` → tools 3 + 4. `get_scenario_variables`
→ absorbida por 1. Nuevas: 2, 5, 6, 7, 8. Se quedan: 9, 10.

**Candidatas a fusionar si resultan poco útiles:**
- 3 + 4: si confirmar el planteamiento no aporta, `correr_experimento` recibe la especificación
  directamente. *Se pierde el paso de deliberación con el usuario.*
- 4 + 7: `correr_experimento` con varias políticas ya da casi todo; 7 solo agrega regret y
  dominancia.

---

## Flujo por categoría de pregunta

Antes de cualquier tool, el agente clasifica la pregunta (A–F). La categoría queda registrada en
`definir_experimento`, y en la respuesta estructurada final para A y F.

```
A · INFORMATIVAS (no corren el XGBoost)
  A1–A3 ──► [1 consultar_mapa] ──► respuesta
  A4    ──► [10 get_country_context] ──► respuesta

B · EVALUAR UNA POLÍTICA DADA
  B1 (palancas explícitas) ────────────────────────────┐
  B2 (lenguaje natural) ──► [1 consultar_mapa] ────────┤
  B3 (variable tangible) ──► [2 traducir_meta] ────────┤
  B4 (variable inexistente) ──► [1] ──► aclarar / proponer aproximación
                                                       ▼
                         [3 definir_experimento] ──► usuario confirma
                                                       ▼
                                             [4 correr_experimento]
                                                       ▼
                                        ¿hay criterio de cumplimiento?
                                          sí ──► [5 descubrir_vulnerabilidades]
                                          no ──► distribuciones + ofrecer criterio

C · LOGRAR UNA META
  [1 consultar_mapa] ──► ¿meta en variable tangible? ── sí ──► [2 traducir_meta]
            │                                                        │
            └──────────────────────────┬─────────────────────────────┘
                                       ▼
                        [3 definir_experimento] (meta = criterio)
                                       ▼
                             [8 buscar_politica]
                                       ▼
                     ¿alguna candidata cumple en ≥ p% de futuros?
                       no ──► reportar máximo alcanzable (C3)
                       sí ──► [7 comparar_politicas] (candidatas, costos: C4)
                                       ▼
                        [5 descubrir_vulnerabilidades] de la elegida

D · ROBUSTEZ Y VULNERABILIDAD
  D1, D2 ──► [3 definir_experimento] (X: todas)
  D3     ──► [3 definir_experimento] (X: condicionado, p. ej. PIB alto)
                                       ▼
                             [4 correr_experimento]
                                       ▼
                        [5 descubrir_vulnerabilidades]
                                       ▼
                   ¿el usuario pregunta por qué? ──► [6 evidencia_mecanismo]
  D4 ──► [3] (varias políticas, X condicionado) ──► [4] ──► [7 comparar_politicas]

E · COMPARAR Y TRADE-OFFS
  E1 ──► [3 definir_experimento] (≥2 políticas) ──► [4] ──► [7 comparar_politicas]
  E2 ──► [3] ──► [4] (costos y beneficios)

F · FUERA DEL SURROGATE
  F1 (estrategia oficial) ──► [9 get_pathway_results]
  F2 (referente inexistente) ──► declinar + alternativa
  F3 (fuera del modelo) ──► declinar
  F4 (ambigua) ──► aclarar antes de cualquier tool
```

**Cobertura:** las 10 tools aparecen en al menos un flujo. Las que dependen de una sola
subcategoría son 6 (`evidencia_mecanismo`, solo D) y 10 (`get_country_context`, solo A4).

---

## Qué registra cada turno (para la evaluación)

- Categoría declarada vs categoría asignada a priori → **clasificación**.
- Secuencia de tools vs secuencia esperada del flujo → **ruta**.
- Coherencia entre la categoría declarada y lo que hizo (p. ej. declaró D3 y fijó el PIB).
- Llamadas a `consultar_mapa` / `traducir_meta`, con argumentos y retorno → **uso de la información**.
- Afirmaciones de "por qué" y si hubo una llamada a `evidencia_mecanismo` detrás → **procedencia**.

## Pendientes

- Valor de las X que no se varían (consultar con el experto del equipo).
- Variables tangibles titulares y de mecanismo por palanca (lista a curar).
- Método de búsqueda de `buscar_politica`.
- Usuario simulado para las corridas automáticas (respuesta fija al paso de confirmación).
- Idea guardada: verificar las afirmaciones de "por qué" antes de mostrarlas (tool o segundo agente).
