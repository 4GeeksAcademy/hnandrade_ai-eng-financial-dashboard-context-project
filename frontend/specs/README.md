# Contrato de datos del frontend

## 1. Propósito y alcance

Este directorio contiene especificaciones y contratos de datos para F1–F3; no es implementación. No contiene componentes React, solicitudes de red ni cambios del backend.

Orden de lectura para una sesión nueva:
1. [verification.md](verification.md): OpenAPI, evidencia real de curl, decisiones D1–D6 y rastro de verificación.
2. [api-types.ts](api-types.ts): tipos de respuesta verificados contra OpenAPI.
3. [param-types.ts](param-types.ts): tipos de query y reglas cliente.
4. [components.md](components.md): props, estados, layout y textos de UI especificados.

## 2. Decisiones D1–D6

- D1: El cliente limita threshold a 0.01–1.0, paso 0.01 y defecto 0.3; si falta o no es válido, no solicita y conserva el último resultado.
- D2: Fechas opcionales `YYYY-MM-DD`; omitir cada fecha vacía y bloquear fechas invertidas o fuera del rango de facets.
- D3: Solicitar top de ingreso con `limit=20` por `business_type`, calcular proporción sobre todos los importes devueltos y comparar sus sumas.
- D4: `facets.categories` es global; `facets.business_types` selecciona los paneles y `business_type` filtra sus tops.
- D5: Sin router en `package.json`; usar `ViewSwitcher` por estado con vistas `dashboard` y `comparison`, sin dependencias nuevas.
- D6: Dashboard y comparación mantienen estados de fechas independientes y comparten `DateRangeFilterBar`.

## 3. Brief frente a API

| Brief | API real | Qué hace la spec |
| --- | --- | --- |
| `threshold` restringido a 0.01–1.0 | OpenAPI define mínimo 0, defecto 0.3 y ningún máximo. | Aplicar D1 en cliente; no enviar valores vacíos o fuera de rango. |
| Facets separa categorías B2B/B2C | `facets.categories` es global; `business_types` también es una lista global. | Crear un panel por `business_types` y pedir categorías mediante `categories/top?business_type=...`. |
| La API devuelve porcentaje por categoría | `TopCategoryItem` solo devuelve `category`, `operation_type`, `total_amount`. | Calcular el porcentaje con la suma de todas las categorías devueltas por grupo. |
| Inicio posterior a fin produce error | La API contestó HTTP 200 con `[]` para fechas invertidas. | D2 bloquea la petición y muestra el mensaje de validación. |
| Baseline independiente del filtro | `2026-03` cambia de `55334.29` a `38276.88` con `start_date=2026-01-01`; desaparece `2025-12`. | Mostrar que el promedio usa períodos del rango; no afirmar la cantidad cuando hay menos de tres. |
| Top-5 por grupo | Con `limit=20`, hoy se devuelven 2 categorías B2B y 2 B2C. | Mostrar solo las filas recibidas, sin relleno; dejar como ❓ una expansión futura por encima del máximo. |

## Funcionalidad 1 — Filtro de fechas

### Endpoints

- `GET /api/metrics`: movimientos del dashboard; actualmente tipado como `FinancialMovement[]` mediante el tipo existente [financial-types.ts:5](../src/lib/financial-types.ts#L5).
- `GET /api/metrics/facets`: rango global y listas disponibles, tipo `FacetsResponse`.

### Tipos

Petición de fechas: `DateRangeFilter`. Facets: `FacetsResponse`. Respuesta de métricas: `FinancialMovement[]`, tipo existente en `frontend/src/lib/financial-types.ts`.

### Parámetros

| Nombre | Tipo | Requerido | Defecto | Restricción API (OpenAPI) | Restricción cliente (D2) |
| --- | --- | --- | --- | --- | --- |
| `start_date` | string, fecha | No | Omitido | `format: date`; opcional y nullable. | `YYYY-MM-DD`; omitir si está vacío; dentro de `min_date`–`max_date`. |
| `end_date` | string, fecha | No | Omitido | `format: date`; opcional y nullable. | `YYYY-MM-DD`; omitir si está vacío; dentro de `min_date`–`max_date`. |
| `category` | string | No | Omitido | Enum `suppliers`, `sales`, `operational`, `administrative`, `others`; opcional y nullable. | F1 no lo envía. |
| `operation_type` | string | No | Omitido | Enum `income` o `outcome`; opcional y nullable. | F1 no lo envía. |
| Facets | — | — | — | `GET /api/metrics/facets` no tiene parámetros. | Solicitar para mostrar el rango y validar fechas. |

### Ejemplos reales

Tomados de [verification.md, sección B](verification.md):

```text
GET /api/metrics?start_date=2026-01-01
HTTP 200; 300 movimientos.

GET /api/metrics/facets
HTTP 200; min_date=2025-11-01; max_date=2026-10-28.
```

La pista exacta es `Datos disponibles: {min_date} a {max_date}`. Los ejemplos de fecha son ilustrativos (D2).

### Componentes

`DateRangeFilterBar` y `AvailableRangeHint` ([components.md](components.md#f1-filtro-de-fechas-del-dashboard)); el rango del dashboard filtra el request principal `/api/metrics`, y sus movimientos alimentan `KPIRow`, `IncomeOutcomeChart` y `ProfitPercentChart` ([App.tsx:16](../src/App.tsx#L16), [App.tsx:57](../src/App.tsx#L57), [App.tsx:65](../src/App.tsx#L65), [App.tsx:66](../src/App.tsx#L66)).

### Casos límite

| Caso | Respuesta de la API (evidencia) | Qué muestra la UI (texto literal) |
| --- | --- | --- |
| Solo una fecha (`start_date=2026-01-01`) | HTTP 200, 300 movimientos. | Sin validación; conserva `Datos disponibles: {min_date} a {max_date}` y muestra los datos devueltos. |
| Ambas fechas vacías | `GET /api/metrics` sin parámetros: HTTP 200, 360 movimientos. | `Datos disponibles: {min_date} a {max_date}`; muestra los datos completos. |
| Inicio posterior a fin | Llamada directa con `2026-03-31` y `2026-01-01`: HTTP 200, `[]`. | No se envía request; `La fecha de inicio no puede ser posterior a la fecha de fin.` |
| Facets falla | No hay error de facets probado en curl; OpenAPI no declara respuesta de error para esta ruta. | `No se pudo cargar el rango disponible.` |

## Funcionalidad 2 — Alertas de anomalías

### Endpoints

- `GET /api/metrics/alerts`: tipo de petición `AlertsParams`; respuesta `AlertsResponse`, alias de `AlertEntry[]`.

### Tipos

`AlertsParams` extiende `DateRangeFilter`; `AlertEntry` contiene `period`, `outcome_total`, `baseline_average` e `increase_ratio`. La API permite más filtros, pero el dashboard no envía `group_by` ni `business_type`.

### Parámetros

| Nombre | Tipo | Requerido | Defecto | Restricción API (OpenAPI) | Restricción cliente (D1/D2) |
| --- | --- | --- | --- | --- | --- |
| `threshold` | number | No | `0.3` | mínimo 0; sin máximo. | `0.01`–`1.0`, paso `0.01`; vacío/no numérico/fuera de rango: no solicitar y conservar el último resultado. |
| `start_date` | string, fecha | No | Omitido | `format: date`; opcional y nullable. | D2; omitir si está vacío. |
| `end_date` | string, fecha | No | Omitido | `format: date`; opcional y nullable. | D2; omitir si está vacío. |
| `group_by` | string | No | `month` | Enum `day`, `week`, `month`. | No enviar desde el dashboard. |
| `business_type` | string | No | Omitido | Enum `B2B` o `B2C`; opcional y nullable. | No enviar desde el dashboard. |

### Ejemplos reales

Tomados de [verification.md, sección B](verification.md):

```text
GET /api/metrics/alerts?threshold=0
HTTP 200; 6 alertas; 2026-03 baseline_average=55334.29.

GET /api/metrics/alerts?threshold=0&start_date=2026-01-01
2026-03 baseline_average=38276.88; 2025-12 desaparece.
```

`threshold=0` es una prueba directa de API, no un valor que la UI envíe: D1 lo bloquea.

### Componentes

`AnomalyAlertsSection`, `ThresholdInput` y `AnomalyAlertsTable` ([components.md](components.md#f2-alertas-de-anomalías)). El rango llega por `DateRangeFilter`; la sección construye `AlertsParams` solo tras validar D1/D2.

### Casos límite

| Caso | Respuesta de la API (evidencia) | Qué muestra la UI (texto literal) |
| --- | --- | --- |
| Array vacío | La API devolvió `[]` con `threshold=1.5` y con un rango sin datos; son llamadas directas fuera de los límites que el cliente permite. | Para una respuesta vacía, `No hay anomalías para el umbral {threshold} en el rango {range}.` La tabla permanece visible. |
| Threshold fuera de rango (`1.5`) | HTTP 200, `[]`; OpenAPI no declara máximo. | No se envía request; `El umbral debe estar entre 0.01 y 1.0.` |
| Periodos sin anomalía | La respuesta contiene solo alertas; omite periodos sin alerta. | No se muestra error; no se crean filas para periodos ausentes. |

## Funcionalidad 3 — Comparación B2B vs B2C

### Endpoints

- `GET /api/metrics/facets`: tipo de respuesta `FacetsResponse`; aporta `business_types`, `min_date`, `max_date` y categorías globales.
- `GET /api/metrics/categories/top`: petición `TopCategoriesParams`; respuesta `TopCategoriesResponse`, alias de `CategoryEntry[]`.

### Tipos

`FacetsResponse` define la lista de grupos disponibles; `TopCategoriesParams` extiende `DateRangeFilter`; `TopCategoriesResponse` es array de `CategoryEntry`. Cada entrada usa los campos reales `category`, `operation_type` y `total_amount`; no hay porcentaje en la respuesta.

### Parámetros

| Nombre | Tipo | Requerido | Defecto | Restricción API (OpenAPI) | Restricción cliente (D2/D3) |
| --- | --- | --- | --- | --- | --- |
| `operation_type` | string | No | `outcome` | Enum `income` o `outcome`. | Enviar `income`. |
| `limit` | integer | No | `5` | mínimo `1`, máximo `20`. | Enviar el máximo `20`; mostrar hasta las cinco primeras filas. |
| `start_date` | string, fecha | No | Omitido | `format: date`; opcional y nullable. | D2; omitir si está vacío. |
| `end_date` | string, fecha | No | Omitido | `format: date`; opcional y nullable. | D2; omitir si está vacío. |
| `business_type` | string | No | Omitido | Enum `B2B` o `B2C`; opcional y nullable. | Una petición por cada valor de `FacetsResponse.business_types`. |
| Facets | — | — | — | `GET /api/metrics/facets` no tiene parámetros. | Usar los grupos y límites de fecha recibidos. |

### Ejemplos reales

Tomados de [verification.md, sección B](verification.md):

```text
GET /api/metrics/categories/top?operation_type=income&limit=20&business_type=B2B
HTTP 200; 2 categorías (sales, others); suma total_amount=615540.72.

GET /api/metrics/categories/top?operation_type=income&limit=20&business_type=B2C
HTTP 200; 2 categorías (sales, others); suma total_amount=642606.15.
```

La vista muestra solo las filas recibidas, hasta cinco; la proporción se calcula con todas las categorías devueltas. El gráfico usa dos puntos/barra, `B2B` y `B2C`, con esas sumas.

### Componentes

`BusinessComparisonPage`, `BusinessGroupPanel`, `TopCategoriesTable` y `RevenueComparisonChart` ([components.md](components.md#f3-comparación-b2b-vs-b2c)). `BusinessComparisonPage` consume `FacetsResponse` y crea dos `TopCategoriesParams`; cada panel/tabla consume su `TopCategoriesResponse`.

### Casos límite

| Caso | Respuesta de la API (evidencia) | Qué muestra la UI (texto literal) |
| --- | --- | --- |
| Top con menos de cinco filas | Con `limit=20`, B2B devuelve `sales` y `others` (2 filas); B2C también devuelve 2. | Sin texto de estado; mostrar solo las filas devueltas, sin relleno. |
| Top vacío | En el rango sin datos `1900-01-01`–`1900-01-31`, `categories/top` devuelve `[]`; D2 impide enviar ese rango desde la UI. | `No hay categorías de ingreso para {businessType} en el rango seleccionado.` en el panel afectado. |
| Falla una de las dos peticiones | No probado con curl; E26 de [verification.md](verification.md) conserva este caso como ❓. | `No se pudo comparar B2B y B2C en este rango.`; no mostrar gráfico parcial. |

## 5. Orden de implementación y límites

1. F1: rango del dashboard, facets y validación de fechas.
2. F2: umbral, rango recibido por props y tabla de alertas.
3. F3: facets/grupos, tops por grupo, porcentajes y suma comparativa.

No tocar `backend/` ni `frontend/src`; no crear React, `.tsx`, requests ni tests en esta fase; no añadir dependencias; no inventar campos de API. Usar los nombres de query y response de OpenAPI y las uniones literales ya definidas en `api-types.ts`.

## 6. ❓ Abiertos

- Número de períodos usados por `baseline_average` cuando hay menos de tres disponibles, y si la ventana es exactamente tres en los demás casos (E8 y E25 de [verification.md](verification.md)).
- Cómo se presenta el fallo de solo una de las dos peticiones F3 según el error real del runtime; el estado de UI está especificado, pero no se probó (E26 de [verification.md](verification.md)).
- Si un grupo llegara a superar `limit=20`, la presentación requeriría una decisión; el caso condicional está anotado en D3 de [verification.md](verification.md), pero hoy el catálogo global enumera cinco categorías.
