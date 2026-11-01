# Verificacion exploratoria de API

Fecha: 2026-11-01. Solo lectura de OpenAPI, llamadas curl indicadas y lectura del frontend. No se modificaron backend ni frontend/src.

## A. Mapa de endpoints por funcionalidad

Rutas GET publicadas en `openapi.json`: `/health`, `/api/metrics`, `/api/metrics/facets`, `/api/metrics/summary`, `/api/metrics/categories/top`, `/api/metrics/comparison`, `/api/metrics/alerts`, `/api/metrics/b2b`, `/api/metrics/b2c`.

| Funcionalidad | Endpoint(s) y uso confirmado |
| --- | --- |
| F1: rango de fechas | `/api/metrics?start_date=&end_date=` filtra movimientos; `/api/metrics/facets` entrega `min_date` y `max_date` globales, sin parámetros. Repetir las fechas en los endpoints que las aceptan para mantener las vistas alineadas. |
| F2: alertas | `/api/metrics/alerts?threshold=&start_date=&end_date=`. También acepta `group_by` y `business_type`. |
| F3: top de ingresos | `/api/metrics/categories/top?operation_type=income&limit=5&business_type=B2B\|B2C&start_date=&end_date=`. `facets.business_types` enumera B2B/B2C y `facets.categories` las categorías globales. |
| F3: total comparativo | OpenAPI de `/api/metrics/summary` admite fechas y `business_type`, y devuelve importes `income` por periodo; una opción es sumar `income` para cada grupo. `/api/metrics/b2b` y `/api/metrics/b2c` devuelven movimientos, no un total agregado. No se hicieron llamadas reales a estas rutas auxiliares. |

Los cuatro endpoints solicitados tienen respuesta 200. OpenAPI declara 422 para `/api/metrics`, `/api/metrics/alerts` y `/api/metrics/categories/top`; `/api/metrics/facets` solo declara 200. No hay otros estados de error documentados para estos cuatro endpoints.

El cuerpo 422 declarado es `HTTPValidationError.detail[]`. Cada `ValidationError` requiere `loc` (array de string/integer), `msg` (string) y `type` (string); `input` y `ctx` aparecen como campos opcionales en el schema.

### `GET /api/metrics`

| Query | Tipo / requerido | Restricciones y valor por defecto |
| --- | --- | --- |
| `start_date`, `end_date` | fecha ISO, opcional, nullable | Sin valor por defecto. |
| `category` | string, opcional, nullable | Enum: `suppliers`, `sales`, `operational`, `administrative`, `others`. |
| `operation_type` | string, opcional, nullable | Enum: `income`, `outcome`. |

200: array de `FinancialMovement`; cada elemento requiere `create_date` (fecha), `amount` (number), `operation_type` (enum), `category` (enum) y `business_type` (`B2B`/`B2C`). Ninguno de esos campos se declara nullable. 422: `HTTPValidationError` con `detail` array de errores de validación.

### `GET /api/metrics/facets`

Sin parámetros. 200: objeto `MetricsFacets`, todos los campos requeridos y no nullable: `operation_types` (array enum `income\|outcome`), `business_types` (array enum `B2B\|B2C`), `categories` (array enum de cinco categorías), `min_date` y `max_date` (fecha). No hay respuesta de error declarada en OpenAPI.

### `GET /api/metrics/alerts`

| Query | Tipo / requerido | Restricciones y valor por defecto |
| --- | --- | --- |
| `threshold` | number, opcional | mínimo 0; defecto 0.3; no se declara máximo. |
| `group_by` | string, opcional | Enum `day\|week\|month`; defecto `month`. |
| `start_date`, `end_date` | fecha ISO, opcional, nullable | Sin valor por defecto. |
| `business_type` | string, opcional, nullable | Enum `B2B\|B2C`. |

200: array de `MetricsAlert`; campos requeridos y no nullable: `period` (string), `outcome_total`, `baseline_average` e `increase_ratio` (number). 422: `HTTPValidationError`. OpenAPI no define que `baseline_average` sea específicamente la media de los tres periodos anteriores.

### `GET /api/metrics/categories/top`

| Query | Tipo / requerido | Restricciones y valor por defecto |
| --- | --- | --- |
| `operation_type` | string, opcional | Enum `income\|outcome`; defecto `outcome`. |
| `limit` | integer, opcional | mínimo 1, máximo 20; defecto 5. |
| `start_date`, `end_date` | fecha ISO, opcional, nullable | Sin valor por defecto. |
| `business_type` | string, opcional, nullable | Enum `B2B\|B2C`. |

200: array de `TopCategoryItem`; campos requeridos y no nullable: `category` (enum de cinco categorías), `operation_type` (enum `income\|outcome`) y `total_amount` (number). No incluye porcentaje ni total del grupo. 422: `HTTPValidationError`.

## B. Evidencia real

La extracción principal de OpenAPI se ejecutó así:

```sh
curl -fsS http://localhost:8000/openapi.json | jq '{routes: [.paths | to_entries[] as $path | $path.value | to_entries[] | select(.key | IN("get", "post", "put", "patch", "delete")) | "\(.key | ascii_upcase) \($path.key)"], endpoints: [.paths | to_entries[] | select(.key | IN("/api/metrics", "/api/metrics/facets", "/api/metrics/alerts", "/api/metrics/categories/top")) | {path: .key, get: {parameters: .value.get.parameters, responses: .value.get.responses}}], schemas: .components.schemas}'
```

También se extrajeron `/api/metrics/summary`, `/api/metrics/comparison`, `/api/metrics/b2b` y `/api/metrics/b2c` desde OpenAPI con `curl`+`jq`; no se llamaron esas rutas. Para las tablas, cada URL fue una llamada curl independiente. En alerts y categories se usó `curl -sS -w '\n%{http_code}' '<URL>' | jq -s ...` para conservar status y proyectar conteos, campos y errores. `jq` está disponible en `/usr/bin/jq`.

### Métricas y facets

| Comando | Salida truncada |
| --- | --- |
| `curl -fsS http://localhost:8000/api/metrics \| jq '{count:length,first:.[0],last:.[-1]}'` | 360; primera fecha `2025-11-01`; última `2026-10-28`. |
| `curl -sS -w '\n%{http_code}' 'http://localhost:8000/api/metrics?start_date=2026-01-01&end_date=2026-03-31'` | HTTP 200, 90 movimientos; extremos `2026-01-01` y `2026-03-24`. |
| `curl -fsS http://localhost:8000/api/metrics/facets \| jq .` | `min_date=2025-11-01`, `max_date=2026-10-28`; `business_types=[B2B,B2C]`; `operation_types=[income,outcome]`; cinco categorías: `administrative`, `operational`, `others`, `sales`, `suppliers`. |

### Alerts

| URL llamada con curl | HTTP y salida truncada |
| --- | --- |
| `/api/metrics/alerts` | 200; 4 alertas; primera `2025-12`, `outcome_total=103378.98`, `baseline_average=41404.44`, `increase_ratio=1.4968`; última `2026-08`. |
| `/api/metrics/alerts?threshold=0.3` | 200; mismas 4 alertas que el defecto. |
| `/api/metrics/alerts?threshold=0.01` | 200; 5 alertas; última `2026-09`, ratio `0.2223`. |
| `/api/metrics/alerts?threshold=1.0` | 200; 1 alerta, periodo `2025-12`. |
| `/api/metrics/alerts?threshold=0` | 200; 6 alertas; última `2026-09`. |
| `/api/metrics/alerts?threshold=1.5` | 200; array vacío. |
| `/api/metrics/alerts?threshold=abc` | 422; error `float_parsing`, ubicación `query.threshold`. |
| `/api/metrics/alerts?start_date=2026-01-01&end_date=2026-03-31` | 200; 1 alerta, periodo `2026-03`, baseline `38276.88`, ratio `1.301`. |
| `/api/metrics/alerts?start_date=2026-01-01` | 200; 3 alertas, periodos extremos `2026-03` y `2026-08`. |
| `/api/metrics/alerts?end_date=2026-03-31` | 200; 2 alertas, periodos extremos `2025-12` y `2026-03`. |
| `/api/metrics/alerts?start_date=1900-01-01&end_date=1900-01-31` | 200; array vacío. |
| `/api/metrics/alerts?threshold=0&start_date=2025-11-01&end_date=2026-01-31` | 200; una alerta: `2025-12`, `outcome_total=103378.98`, `baseline_average=41404.44`, `increase_ratio=1.4968`. La respuesta de alertas no contiene filas para cada periodo sin alerta; no prueba el valor de la media en periodos iniciales sin historial. |

### Top categories

| URL llamada con curl | HTTP y salida truncada |
| --- | --- |
| `/api/metrics/categories/top?operation_type=income&limit=5` | 200; 2 elementos: `sales=1132097.38`, `others=126049.49`. |
| `/api/metrics/categories/top?operation_type=income&limit=5&start_date=2026-01-01&end_date=2026-03-31` | 200; 2 elementos: `sales=284641.29`, `others=44819.98`. |
| `/api/metrics/categories/top?operation_type=income&limit=5&start_date=1900-01-01&end_date=1900-01-31` | 200; `[]`. |
| `/api/metrics/categories/top?operation_type=income&limit=5&start_date=2025-13-45` | 422; `date_from_datetime_parsing`, ubicación `query.start_date`. |
| `/api/metrics/categories/top?operation_type=income&limit=5&start_date=2026-03-31&end_date=2026-01-01` | 200; `[]`, no 422 por fechas invertidas. |
| `/api/metrics/categories/top?operation_type=income&limit=0` | 422; `greater_than_equal`, mínimo 1. |
| `/api/metrics/categories/top?operation_type=income&limit=100` | 422; `less_than_equal`, máximo 20. |
| `/api/metrics/categories/top?operation_type=outcome&limit=5` | 200; 4 elementos: `others=224428.44`, `operational=196093.22`, `administrative=188143.37`, `suppliers=153467.23`. |
| `/api/metrics/categories/top?operation_type=income&limit=5&business_type=B2B` | 200; 2 elementos: `sales=557903.97`, `others=57636.75`. |
| `/api/metrics/categories/top?operation_type=income&limit=5&business_type=B2C` | 200; 2 elementos: `sales=574193.41`, `others=68412.74`. |

## C. Desajustes brief del PM vs API real

| Brief | API real | Decisión propuesta para la spec |
| --- | --- | --- |
| Dos fechas opcionales para filtrar los datos del dashboard | Los nombres reales son `start_date` y `end_date`. Metrics, alerts, top categories y summary aceptan ambos; facets no recibe filtros y entrega el rango global. | Usar esos nombres en todos los requests aplicables; mantener facets como rango global disponible. No presentar el rango global como rango ya filtrado. |
| Umbral configurable 0.01–1.0, defecto 0.3 | El defecto 0.3 coincide; API declara mínimo 0 y ningún máximo. `0` y `1.5` respondieron 200; `abc` respondió 422. | Si la UI debe limitar 0.01–1.0, validar ese rango en el control; no atribuirlo a la API. |
| Media móvil de los tres periodos previos | La respuesta expone `baseline_average`; ni OpenAPI ni las respuestas examinadas definen la ventana. La consulta inicial solo devolvió una alerta de diciembre. | No fijar todavía “tres periodos” ni asignar valor a periodos iniciales. Confirmar contrato/semántica antes de etiquetar la columna como media de tres periodos. |
| Estado vacío explícito de alertas | Sin registros o sin resultados se devuelve `[]` con HTTP 200. | Mostrar estado vacío en UI cuando la lista sea vacía; no tratarlo como error HTTP. |
| Categorías B2B/B2C salen de facets | Facets da listas globales de `business_types` y `categories`; el filtro de grupo está en `business_type` de `categories/top`. | Pedir el top por separado con `business_type=B2B` y `business_type=B2C`; facets aporta valores disponibles, no tops por grupo. |
| Top-5 de ingresos con nombre, total y porcentaje del grupo | Para ingreso la llamada real devolvió `category` y `total_amount`, sin porcentaje ni total de grupo. `limit=5` acepta máximo 20; las respuestas observadas contenían dos categorías de ingreso por grupo. | Calcular el porcentaje en frontend solo después de acordar el denominador. Sumar los elementos devueltos puede servir si el top cubre todas las categorías del grupo; la API no declara expresamente ese total como denominador. |
| Gráfico del total B2B vs B2C | `summary` filtra por `business_type` y fechas, devuelve `income` por periodo; `/b2b` y `/b2c` devuelven movimientos. No existe en los contratos inspeccionados un único escalar agregado B2B/B2C. | Candidato: dos requests a `summary`, uno por grupo, y sumar `income` por periodos si “total” significa ingresos. Acordar si el gráfico compara ingresos u otra métrica. No se probó en vivo este candidato. |
| Top de ingreso | `categories/top` tiene defecto `operation_type=outcome`; el brief sí especifica `income`. | Enviar siempre `operation_type=income`; no depender del defecto. |

## D. Patrones del frontend

- El único fetch actual está en `fetchFinancialData`, tipado `Promise<FinancialMovement[]>`, y llama `/api/metrics`: [frontend/src/App.tsx:15](frontend/src/App.tsx#L15), [frontend/src/App.tsx:16](frontend/src/App.tsx#L16). Usa `VITE_API_BASE_URL` como base y calcula KPIs/datos mensuales en frontend.
- `FinancialMovement` ya incluye `create_date`, `amount`, `operation_type`, `category` y `business_type`; `BusinessType` es `B2B | B2C`: [frontend/src/lib/financial-types.ts:3](frontend/src/lib/financial-types.ts#L3), [frontend/src/lib/financial-types.ts:5](frontend/src/lib/financial-types.ts#L5). Tipos derivados existentes: `KPIMetrics` y `MonthlyDataPoint`: [frontend/src/lib/financial-types.ts:13](frontend/src/lib/financial-types.ts#L13), [frontend/src/lib/financial-types.ts:20](frontend/src/lib/financial-types.ts#L20).
- La carga conserva estados `loading` y `error`; el catch actual establece un mensaje de error visible: [frontend/src/App.tsx:26](frontend/src/App.tsx#L26), [frontend/src/App.tsx:27](frontend/src/App.tsx#L27), [frontend/src/App.tsx:35](frontend/src/App.tsx#L35). El periodo del encabezado está fijado actualmente en la llamada de App: [frontend/src/App.tsx:49](frontend/src/App.tsx#L49).
- La dependencia de gráficos es Recharts: [frontend/package.json:21](frontend/package.json#L21). Las vistas existentes importan `recharts` y usan `ResponsiveContainer`/`LineChart`: [frontend/src/components/dashboard/income-outcome-chart.tsx:14](frontend/src/components/dashboard/income-outcome-chart.tsx#L14), [frontend/src/components/dashboard/profit-percent-chart.tsx:13](frontend/src/components/dashboard/profit-percent-chart.tsx#L13).
- Convención observada: archivos de componente en kebab-case y funciones exportadas en PascalCase (`IncomeOutcomeChart`, `ProfitPercentChart`): [frontend/src/components/dashboard/income-outcome-chart.tsx:49](frontend/src/components/dashboard/income-outcome-chart.tsx#L49), [frontend/src/components/dashboard/profit-percent-chart.tsx:50](frontend/src/components/dashboard/profit-percent-chart.tsx#L50).

## E. Rastro de verificación

| # | Afirmación | Marca | Evidencia |
| --- | --- | --- | --- |
| 1 | OpenAPI publica nueve rutas GET, incluyendo `/api/metrics/facets`, `/alerts` y `/categories/top`. | ✅ | `curl -fsS http://localhost:8000/openapi.json` filtrado con jq; salida de rutas en A. |
| 2 | `/api/metrics` usa `start_date`/`end_date` opcionales y responde con array de movimientos. | ✅ | OpenAPI filtrado con jq; llamada con fechas devolvió HTTP 200 y 90 elementos. |
| 3 | Facets da el rango disponible `2025-11-01`–`2026-10-28` y business types B2B/B2C. | ✅ | `curl -fsS http://localhost:8000/api/metrics/facets \| jq .`. |
| 4 | El defecto de threshold es 0.3 y el contrato no declara máximo. | ✅ | OpenAPI de `/api/metrics/alerts`. |
| 5 | La API restringe threshold a 0.01–1.0. | ❌ | OpenAPI declara mínimo 0 y sin máximo; curl con `threshold=0` y `threshold=1.5` respondió 200. |
| 6 | `threshold=abc` causa error de validación 422. | ✅ | `curl` a `/api/metrics/alerts?threshold=abc`; `float_parsing` en `query.threshold`. |
| 7 | Alerts devuelve `[]` para el rango sin datos consultado. | ✅ | `curl` a `/api/metrics/alerts?start_date=1900-01-01&end_date=1900-01-31`; HTTP 200. |
| 8 | La media de alerts usa exactamente los tres periodos anteriores y tiene un valor definido antes de contar con esos periodos. | ❓ | OpenAPI solo nombra `baseline_average`; la consulta del tramo inicial no devuelve filas para todos los periodos ni define el cálculo. |
| 9 | `categories/top` separa los grupos con `business_type=B2B\|B2C`; facets enumera ambos. | ✅ | OpenAPI y las dos llamadas reales con `business_type=B2B` y `business_type=B2C`. |
| 10 | El schema de `TopCategoryItem` incluye el porcentaje del grupo. | ❌ | OpenAPI solo define `category`, `operation_type` y `total_amount`; las respuestas reales no incluyen porcentaje. |
| 11 | La fecha inválida `2025-13-45` causa 422 en `categories/top`. | ✅ | Llamada real; `date_from_datetime_parsing` en `query.start_date`. |
| 12 | El intervalo con inicio posterior a fin se rechaza con 422. | ❌ | Llamada real con `2026-03-31` > `2026-01-01`: HTTP 200 y `[]`. |
| 13 | `limit=0` y `limit=100` se rechazan con 422. | ✅ | Llamadas reales; errores `greater_than_equal` y `less_than_equal`. |
| 14 | `/api/metrics/summary` permite fechas y `business_type`, y devuelve `income`/`outcome` por periodo. | ✅ | OpenAPI inspeccionado con curl+jq; la ruta no se llamó en vivo. |
| 15 | Las citas de fetch, tipos y Recharts del frontend coinciden con el código actual. | ✅ | `grep -n` sobre `frontend/src/App.tsx`, `frontend/src/lib/financial-types.ts`, `frontend/package.json` y ambos componentes de gráfico. |
