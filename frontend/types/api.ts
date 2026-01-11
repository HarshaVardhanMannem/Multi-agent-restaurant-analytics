// Type definitions matching backend API responses

export enum QueryIntent {
  SALES_ANALYSIS = "sales_analysis",
  PRODUCT_ANALYSIS = "product_analysis",
  LOCATION_COMPARISON = "location_comparison",
  TIME_SERIES = "time_series",
  PAYMENT_ANALYSIS = "payment_analysis",
  ORDER_TYPE_ANALYSIS = "order_type_analysis",
  SOURCE_COMPARISON = "source_comparison",
  PERFORMANCE_METRICS = "performance_metrics",
  CATEGORY_ANALYSIS = "category_analysis",
  CUSTOMER_ANALYSIS = "customer_analysis",
  UNKNOWN = "unknown",
}

export enum VisualizationType {
  TABLE = "table",
  BAR_CHART = "bar_chart",
  LINE_CHART = "line_chart",
  PIE_CHART = "pie_chart",
  STACKED_BAR = "stacked_bar",
  MULTI_SERIES = "multi_series",
  HEATMAP = "heatmap",
  METRIC = "metric",
  NONE = "none",
}

export interface VisualizationConfig {
  title?: string;
  x_axis?: string;
  y_axis?: string;
  series?: string[];
  colors?: string[];
  [key: string]: any;
}

export interface VisualizationResponse {
  type: VisualizationType;
  config?: VisualizationConfig;  // Optional - may not be set when visualization is pending
  chart_js_config?: Record<string, any>;
  available?: boolean;  // Whether visualization is available to fetch
  status?: string;  // Status: pending, ready, not_applicable, error
}

export interface QueryResponse {
  success: boolean;
  query_id: string;
  intent: QueryIntent;
  sql: string;
  explanation: string;
  answer?: string;
  key_insights?: string[];
  results: Record<string, any>[];
  result_count: number;
  columns: string[];
  visualization: VisualizationResponse;
  execution_time_ms: number;
  total_processing_time_ms: number;
}

export interface ClarificationResponse {
  success: boolean;
  clarification_needed: boolean;
  question: string;
  suggestions: string[];
  original_query: string;
  detected_intent?: QueryIntent;
}

export interface ErrorResponse {
  success: false;
  error_code: string;
  error_message: string;
  details?: Record<string, any>;
  suggestions: string[];
}

export interface QueryRequest {
  query: string;
  include_chart?: boolean;
  max_results?: number;
  context?: Array<{ role: string; content: string }>;
  stream_answer?: boolean;
}

export interface ExampleQuery {
  query: string;
  intent: QueryIntent;
  description: string;
}

export interface ExamplesResponse {
  examples: ExampleQuery[];
}

export interface Widget {
  id: string;
  query: string;
  response: QueryResponse;
  createdAt: Date;
}

// Authentication Types
export enum UserRole {
  USER = "user",
  ADMIN = "admin",
}

export interface User {
  id: string;
  email: string;
  full_name: string | null;
  role: UserRole;
  is_active: boolean;
  created_at: string;
}

export interface LoginRequest {
  email: string;
  password: string;
}

export interface RegisterRequest {
  email: string;
  password: string;
  full_name?: string;
}

export interface TokenResponse {
  access_token: string;
  token_type: string;
  expires_in: number;
  user: User;
}

export interface QueryHistoryItem {
  id: string;
  query_id: string;
  user_id: string | null;
  natural_query: string;
  generated_sql: string;
  intent: string;
  execution_time_ms: number;
  result_count: number;
  visualization_type: string;
  answer: string | null;
  success: boolean;
  created_at: string;
}

// Detailed query history with full results for restoring widgets
export interface QueryHistoryDetail extends QueryHistoryItem {
  results_sample: Record<string, any>[];
  columns: string[];
  visualization_config: Record<string, any>;
}

export interface AuthState {
  user: User | null;
  token: string | null;
  isAuthenticated: boolean;
  isLoading: boolean;
}

