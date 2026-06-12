# Osmar Technical Document Voice

## Purpose

Use this reference when Osmar asks for technical documents, memorias descriptivas, memorias de cálculo, criteria, engineering reports, procedures, or technical explanations that should keep his document style.

This is a private style guide. It stores patterns extracted from technical document examples, not copied source content.

## Core style

- Write in clear, formal Spanish.
- Start with objective, scope, or purpose before details.
- Prefer impersonal technical wording when it improves formality: `se considera`, `se presenta`, `se recomienda`, `se requiere`.
- Keep statements tied to criteria, standards, input data, calculations, observations, or results.
- Use direct paragraphs; avoid decorative introductions.
- Use tables, numbered sections, and bullets when they make review easier.
- Keep units, voltage levels, document names, equipment names, and calculation labels exact when provided by the user.
- Do not invent norms, values, results, measurements, dates, signatures, or project facts.

## Common document structure

### Memoria descriptiva

1. Descripción general
2. Objetivo
3. Alcance
4. Normativas y criterios considerados
5. Descripción técnica del sistema o instalación
6. Equipos, áreas o componentes principales
7. Observaciones
8. Conclusiones o próximos pasos

### Memoria de cálculo

1. Objetivo del cálculo
2. Alcance
3. Criterios, normas y referencias
4. Datos de entrada
5. Hipótesis o consideraciones
6. Procedimiento de cálculo
7. Resultados
8. Verificación o cumplimiento
9. Observaciones y conclusiones

### Reporte técnico

1. Resumen u objetivo
2. Situación observada
3. Criterios de revisión
4. Acciones realizadas o análisis
5. Resultado
6. Pendientes, recomendaciones o próximos pasos

## Preferred phrases

Use these as safe patterns, adapting only with facts provided by the user:

- `El objetivo de este documento es presentar...`
- `La presente memoria tiene como finalidad...`
- `El presente documento describe...`
- `Se consideran los siguientes criterios...`
- `Para el desarrollo del cálculo se consideran...`
- `Los datos de entrada utilizados corresponden a...`
- `Se presenta el procedimiento de cálculo empleado para...`
- `Los resultados obtenidos se resumen a continuación...`
- `Durante la revisión se observó...`
- `En base a los criterios indicados...`
- `Se recomienda verificar...`
- `Para continuar, se requiere...`
- `Queda pendiente la validación de...` only when a real pending item exists.

## Calculation writing rules

When writing or improving calculation memories:

- Separate inputs, assumptions, formulas/procedure, and results.
- If a value is missing, use a placeholder like `[VALOR]`, `[UNIDAD]`, `[NORMA]`, or `[RESULTADO]`.
- If the user provides a result, preserve it and explain its role.
- If the user provides only partial data, state the limitation clearly.
- Never fabricate formulas, safety factors, acceptance criteria, or compliance conclusions.
- Present conclusions as conditional when the source data is incomplete.

## Tone by section

| Section | Voice |
| --- | --- |
| Objective | Direct purpose: what document presents or verifies. |
| Scope | Boundaries: what is included and excluded. |
| Criteria | Norms, references, assumptions, and design basis. |
| Description | Clear technical explanation of system/equipment. |
| Calculations | Step-by-step, traceable, with inputs and units. |
| Observations | Practical notes without exaggeration. |
| Conclusions | Short, tied to results and criteria. |

## Privacy rules

- Do not copy names, phone numbers, emails, signatures, company details, or project identifiers from source documents.
- Use placeholders: `[CLIENTE]`, `[PROYECTO]`, `[DOCUMENTO]`, `[NORMA]`, `[FECHA]`, `[VALOR]`, `[UNIDAD]`, `[RESPONSABLE]`.
- Do not mention source files or private folders in final user-facing documents unless the user asks.
- Extract style patterns only; do not reproduce private source paragraphs as examples.

## Avoid

- Commercial or sales-heavy tone in technical memories.
- Long ornamental openings.
- Unsupported certainty: avoid `cumple` unless criteria and result are provided.
- Mixing observations, assumptions, and conclusions in one paragraph.
- Inventing missing project data.
- Overusing first person.
- Adding recommendations not grounded in provided facts.
