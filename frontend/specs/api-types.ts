/** Operation values published by the metrics API. */
export type OperationType = "income" | "outcome";

/** Business groups published by the metrics API. */
export type BusinessType = "B2B" | "B2C";

/** Category values published by facets and category responses. */
export type MetricCategory =
  | "suppliers"
  | "sales"
  | "operational"
  | "administrative"
  | "others";

/** Response schema for GET /api/metrics/facets. */
export interface FacetsResponse {
  /** Available operation filters; valid values are income and outcome. */
  operation_types: OperationType[];
  /** Available business groups; valid values are B2B and B2C. */
  business_types: BusinessType[];
  /** Available category filters; values use the MetricCategory union. */
  categories: MetricCategory[];
  /** Earliest available movement date, formatted YYYY-MM-DD. */
  min_date: string;
  /** Latest available movement date, formatted YYYY-MM-DD. */
  max_date: string;
}

/** One alert item returned by GET /api/metrics/alerts. */
export interface AlertEntry {
  /** Period label supplied by the API; OpenAPI does not constrain its format. */
  period: string;
  /** Outcome amount for this period; OpenAPI declares a number without bounds. */
  outcome_total: number;
  /** Average outcome of the previous periods inside the requested date range (verified: it changes when start_date changes); how many periods are used when fewer than three exist is unconfirmed. */
  baseline_average: number;
  /** Numeric relative increase ratio; OpenAPI declares no bounds. */
  increase_ratio: number;
}

/** Array response from GET /api/metrics/alerts. */
export type AlertsResponse = AlertEntry[];

/** One category total returned by GET /api/metrics/categories/top. */
export interface CategoryEntry {
  /** Category name, one of the MetricCategory values. */
  category: MetricCategory;
  /** Operation represented by this total: income or outcome. */
  operation_type: OperationType;
  /** Numeric summed amount for this category and operation; OpenAPI declares no bounds. */
  total_amount: number;
}

/** Array response from GET /api/metrics/categories/top. */
export type TopCategoriesResponse = CategoryEntry[];