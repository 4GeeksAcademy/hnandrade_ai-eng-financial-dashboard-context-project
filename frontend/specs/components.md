# Especificacion de componentes

Los componentes de esta fase son especificaciones, no implementaciones. Los contratos importados corresponden a `api-types.ts` y `param-types.ts`.

## F1. Filtro de fechas del dashboard

El dashboard principal conserva su propio `DateRangeFilter`. Su petición de datos es `GET /api/metrics`; la respuesta alimenta las métricas y series mensuales que consumen `KPIRow`, `IncomeOutcomeChart` y `ProfitPercentChart` ([App.tsx:15](frontend/src/App.tsx#L15), [App.tsx:16](frontend/src/App.tsx#L16), [App.tsx:30](frontend/src/App.tsx#L30), [App.tsx:57](frontend/src/App.tsx#L57), [App.tsx:65](frontend/src/App.tsx#L65), [App.tsx:66](frontend/src/App.tsx#L66)). F2 recibe el mismo rango por props y lo combina con su umbral para `AlertsParams`.

### DateRangeFilterBar

**Propósito:** Editar inicio y fin opcionales; compartir el mismo control entre dashboard y comparación B2B/B2C.

**Layout:** Barra con dos inputs `type="date"` etiquetados Inicio y Fin, junto a `AvailableRangeHint`. Cuando hay facets, ambos inputs usan `min={min_date}` y `max={max_date}`.

**Props:**

```ts
import type { FacetsResponse } from "./api-types";
import type { DateRangeFilter } from "./param-types";

interface DateRangeFilterBarProps {
  value: DateRangeFilter;
  facets: FacetsResponse | null;
  facetsLoading: boolean;
  facetsError: string | null;
  onChange: (value: DateRangeFilter) => void;
}
```

**Renderizado condicional:** Solo una fecha rellena: enviar únicamente `start_date` o `end_date`, omitiendo el parámetro vacío. Ambos vacíos: no enviar parámetros de fecha y mostrar datos completos. Inicio posterior a fin: no pedir datos y mostrar `La fecha de inicio no puede ser posterior a la fecha de fin.` Una fecha fuera de facets: no pedir datos y mostrar `Las fechas deben estar entre {min_date} y {max_date}.` Con facets cargando o en error, mostrar el estado de `AvailableRangeHint` y mantener bloqueada la selección de fechas hasta poder validar el rango; el dashboard puede seguir mostrando la carga completa sin filtro.

### AvailableRangeHint

**Propósito:** Mostrar el rango global que informa `GET /api/metrics/facets`; no separa categorías por grupo.

**Layout:** Texto cercano a la barra: `Datos disponibles: {min_date} a {max_date}`. Los dos valores también son los límites de los inputs.

**Props:**

```ts
import type { FacetsResponse } from "./api-types";

interface AvailableRangeHintProps {
  facets: FacetsResponse | null;
  loading: boolean;
  error: string | null;
}
```

**Renderizado condicional:** Mientras carga: `Cargando rango disponible…`. Si facets falla: `No se pudo cargar el rango disponible.` Sin datos ni error: no afirmar fechas; mantener el texto de carga/indisponibilidad, nunca inventar min/max. Con datos: mostrar literalmente el texto de rango indicado arriba.

## F2. Alertas de anomalías

El estado de fechas procede del dashboard por props; la página principal no envía `group_by` ni `business_type`, aunque la API los acepte.

### AnomalyAlertsSection

**Propósito:** Coordinar el umbral, el rango activo y la lista de anomalías de `GET /api/metrics/alerts`.

**Layout:** Umbral encima de una tabla persistente de cuatro columnas. La validación del umbral queda junto al control.

**Props:**

```ts
import type { AlertsResponse } from "./api-types";
import type { AlertsParams, DateRangeFilter } from "./param-types";

interface AnomalyAlertsSectionProps {
  dateRange: DateRangeFilter;
  rows: AlertsResponse | null;
  thresholdInput: string;
  validationMessage: string | null;
  loading: boolean;
  error: string | null;
  onThresholdInput: (value: string) => void;
  onRequest: (params: AlertsParams) => void;
}
```

**Renderizado condicional:** Carga: skeleton dentro de la sección y conservar la estructura de tabla. Error de API: aviso de error y estructura visible. Umbral vacío, no numérico o fuera de 0.01–1.0: D1, no llamar `onRequest` y conservar las últimas filas válidas. Umbral válido: formar `AlertsParams` con el umbral y las fechas no vacías; omitir fechas vacías, `group_by` y `business_type`. Respuesta `[]`: mostrar el estado vacío definido en `AnomalyAlertsTable`, no eliminar la tabla. Los periodos sin anomalía no son errores y no aparecen en la respuesta.

Con `start_date` o `end_date` activo, mostrar bajo la tabla esta nota literal: «El promedio móvil se calcula solo con los períodos del rango seleccionado.» Un período sin períodos previos dentro del rango no puede aparecer.

### ThresholdInput

**Propósito:** Capturar y validar el umbral de anomalía según D1.

**Layout:** Input numérico con `min=0.01`, `max=1.0`, `step=0.01`, valor inicial `0.3` y mensaje de validación asociado.

**Props:**

```ts
interface ThresholdInputProps {
  value: string;
  validationMessage: string | null;
  onChange: (value: string) => void;
}
```

**Renderizado condicional:** Valor válido: habilitar la solicitud con el número correspondiente. Vacío, no numérico o fuera del rango: mostrar `El umbral debe estar entre 0.01 y 1.0.` junto al input, no enviar petición y conservar el último resultado válido. No convertir silenciosamente valores inválidos en 0.3.

### AnomalyAlertsTable

**Propósito:** Presentar cada elemento de `AlertsResponse` y un estado vacío explícito.

**Layout:** Tabla con encabezados siempre visibles y filas de datos debajo. Las cuatro columnas son:

| Nombre en UI | Campo `AlertEntry` | Tipo | Formato |
| --- | --- | --- | --- |
| Periodo | `period` | `string` | Texto recibido, por ejemplo `2025-12`; OpenAPI no fija formato. |
| Outcome registrado | `outcome_total` | `number` | Moneda, dos decimales. |
| Media base | `baseline_average` | `number` | Moneda, dos decimales. |
| Incremento | `increase_ratio` | `number` | Porcentaje con un decimal: multiplicar el ratio por 100. |

**Comprobación de ratio:** La fila documentada en [verification.md](verification.md) tiene `outcome_total=103378.98`, `baseline_average=41404.44` e `increase_ratio=1.4968`. `(103378.98 / 41404.44) - 1 = 1.4968`, es decir, `149.68%`, que se muestra como `149.7%`. Por tanto, `0.3` representa `30%`, no `0.3%`.

**Props:**

```ts
import type { AlertsResponse } from "./api-types";
import type { DateRangeFilter } from "./param-types";

interface AnomalyAlertsTableProps {
  rows: AlertsResponse | null;
  threshold: number;
  dateRange: DateRangeFilter;
  loading: boolean;
  error: string | null;
}
```

**Renderizado condicional:** Carga: mantener tabla y encabezados, con filas skeleton. Error: mantener la tabla y mostrar el error. `rows=[]`: mantener la tabla y mostrar literalmente `No hay anomalías para el umbral {threshold} en el rango {range}.` Para fechas vacías, `{range}` es `todos los datos`; si hay una sola fecha, mostrar solo ese límite. Con filas, renderizar todas las anomalías recibidas; no crear filas para periodos ausentes.

**Estado vacío:** La tabla y sus cuatro encabezados permanecen visibles; el mensaje incluye el umbral y el rango activos.

## F3. Comparación B2B vs B2C

D4: `facets.business_types` decide qué paneles aparecen; `facets.categories` es una lista global de nombres conocidos. Cada grupo pide sus propias categorías mediante `business_type`.

### ViewSwitcher

**Propósito:** Cambiar entre dashboard principal y comparación sin rutas ni dependencias nuevas: `package.json` declara React y Recharts, pero ningún router ([package.json:15](frontend/package.json#L15), [package.json:21](frontend/package.json#L21)). D5 establece navegación por estado local.

**Layout:** Selector de dos opciones visible en la cabecera: Dashboard y Comparación B2B/B2C.

**Props:**

```ts
type ViewName = "dashboard" | "comparison";

interface ViewSwitcherProps {
  activeView: ViewName;
  onChange: (view: ViewName) => void;
}
```

**Renderizado condicional:** Siempre mostrar ambas opciones; marcar la activa. La selección `dashboard` muestra la página principal y `comparison` muestra `BusinessComparisonPage`.

### BusinessComparisonPage

**Propósito:** Mantener el estado de fechas independiente del dashboard, pedir facets y coordinar un panel por cada valor de `business_types`.

**Layout:** `DateRangeFilterBar` compartida arriba; debajo, dos paneles en paralelo que se apilan en pantalla estrecha; `RevenueComparisonChart` a todo el ancho debajo. En el rango observado, cada grupo devolvió dos categorías ([verification.md](verification.md)).

**Props:**

```ts
import type {
  BusinessType,
  FacetsResponse,
  TopCategoriesResponse,
} from "./api-types";
import type {
  DateRangeFilter,
  TopCategoriesParams,
} from "./param-types";

interface BusinessGroupState {
  categories: TopCategoriesResponse | null;
  loading: boolean;
  error: string | null;
}

interface BusinessComparisonPageProps {
  facets: FacetsResponse | null;
  facetsLoading: boolean;
  facetsError: string | null;
  dateRange: DateRangeFilter;
  groups: Partial<Record<BusinessType, BusinessGroupState>>;
  onDateRangeChange: (value: DateRangeFilter) => void;
  onRequestCategories: (params: TopCategoriesParams) => void;
}
```

**Renderizado condicional:** Facets cargando: mantener el layout y mostrar placeholders de paneles/gráfico. Error de facets: mostrar el error y no inventar grupos. Con facets: crear un panel por `business_types`; enviar una solicitud por grupo con `operation_type="income"`, `limit=20`, `business_type` correspondiente y fechas no vacías. Si el filtro de fechas no pasa D2, no solicitar categorías. Un error de un grupo no oculta el panel ni los datos del otro.

### BusinessGroupPanel

**Propósito:** Enmarcar el top y el total de ingreso de un único grupo, sin mezclar B2B y B2C.

**Layout:** Título del grupo y `TopCategoriesTable` dentro de cada panel; los dos paneles se muestran en paralelo en escritorio y apilados en móvil.

**Props:**

```ts
import type { BusinessType } from "./api-types";
import type { TopCategoriesResponse } from "./api-types";

interface BusinessGroupState {
  categories: TopCategoriesResponse | null;
  loading: boolean;
  error: string | null;
}

interface BusinessGroupPanelProps {
  businessType: BusinessType;
  state: BusinessGroupState;
}
```

**Renderizado condicional:** Carga: skeleton local. Error: mensaje local al grupo. `categories=[]`: pasar la lista vacía a la tabla para que muestre su propio estado vacío. Con datos: mostrar grupo y tabla sin afectar el otro panel.

**Estado vacío:** El panel conserva su título de grupo y la tabla muestra su propio mensaje para ese grupo cuando la respuesta es `[]`.

### TopCategoriesTable

**Propósito:** Mostrar categorías de ingreso de un grupo y calcular el porcentaje según D3.

**Layout:** Tabla con columnas Categoría, Total y `% del grupo` a un decimal. Mostrar solo las filas devueltas, hasta cinco; no rellenar huecos. El denominador es la suma de `total_amount` de todas las categorías devueltas por ese grupo, antes de limitar la presentación a cinco.

**Props:**

```ts
import type {
  BusinessType,
  TopCategoriesResponse,
} from "./api-types";

interface TopCategoriesTableProps {
  businessType: BusinessType;
  categories: TopCategoriesResponse | null;
  loading: boolean;
  error: string | null;
}
```

**Renderizado condicional:** Carga: mantener encabezados y mostrar skeleton. Error: mensaje en ese panel. `categories=[]`: mostrar literalmente `No hay categorías de ingreso para {businessType} en el rango seleccionado.` Con datos: mostrar nombre, total monetario y `total_amount / suma_grupo * 100`, con un decimal. Si la suma es 0, mostrar `0.0%` sin dividir por cero. No hay relleno artificial si llegan menos de cinco filas. Si un grupo superase el máximo de 20 categorías, dejarlo como ❓ según D3.

**Estado vacío:** Mostrar el mensaje propio de ese grupo; el otro panel conserva su resultado o su estado independiente.

### RevenueComparisonChart

**Propósito:** Comparar en el rango activo el total de ingresos B2B y B2C, cada uno sumado sobre todas las categorías devueltas por su request `limit=20`.

**Layout:** Gráfico de barras horizontal de Recharts debajo de los dos paneles. Eje categórico vertical: `B2B`, `B2C`; eje numérico horizontal: total monetario con ticks compactos y tooltip en moneda con dos decimales. Cada grupo es un punto/barra. Recharts ya se importa y usa `ResponsiveContainer` en el dashboard ([income-outcome-chart.tsx:14](../src/components/dashboard/income-outcome-chart.tsx#L14), [income-outcome-chart.tsx:78](../src/components/dashboard/income-outcome-chart.tsx#L78)); `LineChart` y formateo monetario son patrones existentes ([income-outcome-chart.tsx:79](../src/components/dashboard/income-outcome-chart.tsx#L79), [income-outcome-chart.tsx:91](../src/components/dashboard/income-outcome-chart.tsx#L91)).

**Props:**

```ts
import type { BusinessType } from "./api-types";

interface RevenuePoint {
  businessType: BusinessType;
  totalAmount: number;
}

interface RevenueComparisonChartProps {
  points: [RevenuePoint, RevenuePoint];
  loading: boolean;
  error: string | null;
}
```

**Renderizado condicional:** Carga: skeleton en el espacio del gráfico. Si falla cualquiera de las dos solicitudes: mensaje `No se pudo comparar B2B y B2C en este rango.` y no dibujar una comparación parcial; los paneles conservan sus estados independientes. Si ambos totales son `0`: mostrar `No hay ingresos B2B ni B2C en el rango seleccionado.` en el espacio del gráfico. En los demás casos, dibujar exactamente dos barras, incluso si una suma es cero; cada suma incluye todas las categorías devueltas y no solo las cinco filas visibles.
