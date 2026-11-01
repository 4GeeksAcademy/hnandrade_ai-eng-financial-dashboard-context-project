import type { BusinessType, OperationType } from "./api-types";

/** Optional shared date filters; apply the client validation specified in D2. */
export interface DateRangeFilter {
  /**
  * Optional start-date filter as a string in YYYY-MM-DD format. Send this
  * parameter alone when end_date is empty; reject dates outside facets (D2).
   */
  start_date?: string;
  /**
  * Optional end-date filter as a string in YYYY-MM-DD format. Send this
  * parameter alone when start_date is empty; reject dates outside facets (D2).
   */
  end_date?: string;
}

/** Query parameters accepted by GET /api/metrics/alerts. */
export interface AlertsParams extends DateRangeFilter {
  /**
  * Optional numeric threshold; OpenAPI minimum is 0 and declares no maximum.
  * Client input uses 0.01-1.0, step 0.01, default 0.3; blank, invalid, or
  * out-of-range values send no request and preserve the last valid result (D1).
   */
  threshold?: number;
  /** Optional aggregation interval; valid values are day, week, or month. */
  group_by?: "day" | "week" | "month";
  /** Optional business filter; valid values are B2B or B2C. */
  business_type?: BusinessType;
}

/** Query parameters accepted by GET /api/metrics/categories/top. */
export interface TopCategoriesParams extends DateRangeFilter {
  /**
   * Optional operation selector; valid values are income and outcome.
   * The API defaults to outcome; the income view sends income (D3).
   */
  operation_type?: OperationType;
  /**
   * Optional result limit; API range is 1-20 and default is 5.
   * The B2B/B2C spec requests the maximum, 20 (D3).
   */
  limit?: number;
  /** Optional business group; valid values are B2B or B2C, one request per group (D3). */
  business_type?: BusinessType;
}