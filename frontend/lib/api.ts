import axios from 'axios';
import {
  QueryRequest,
  QueryResponse,
  ClarificationResponse,
  ErrorResponse,
  ExamplesResponse,
  LoginRequest,
  RegisterRequest,
  TokenResponse,
  User,
  QueryHistoryItem,
  QueryHistoryDetail,
} from '@/types/api';

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

// Token storage keys
const TOKEN_KEY = 'auth_token';
const USER_KEY = 'auth_user';

// Create axios instance
const apiClient = axios.create({
  baseURL: API_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Add auth token to requests if available
apiClient.interceptors.request.use((config) => {
  const token = getStoredToken();
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

// Handle 401 responses
apiClient.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      // Clear auth on 401
      clearAuth();
    }
    return Promise.reject(error);
  }
);

// ==================== Token Storage ====================

export function getStoredToken(): string | null {
  if (typeof window === 'undefined') return null;
  return localStorage.getItem(TOKEN_KEY);
}

export function getStoredUser(): User | null {
  if (typeof window === 'undefined') return null;
  const userStr = localStorage.getItem(USER_KEY);
  if (!userStr) return null;
  try {
    return JSON.parse(userStr);
  } catch {
    return null;
  }
}

export function setAuth(token: string, user: User): void {
  if (typeof window === 'undefined') return;
  localStorage.setItem(TOKEN_KEY, token);
  localStorage.setItem(USER_KEY, JSON.stringify(user));
}

export function clearAuth(): void {
  if (typeof window === 'undefined') return;
  localStorage.removeItem(TOKEN_KEY);
  localStorage.removeItem(USER_KEY);
}

// ==================== Auth API ====================

export async function login(credentials: LoginRequest): Promise<TokenResponse> {
  const response = await apiClient.post('/api/auth/login', credentials);
  const data = response.data as TokenResponse;
  setAuth(data.access_token, data.user);
  return data;
}

export async function register(data: RegisterRequest): Promise<TokenResponse> {
  const response = await apiClient.post('/api/auth/register', data);
  const tokenData = response.data as TokenResponse;
  setAuth(tokenData.access_token, tokenData.user);
  return tokenData;
}

export async function getCurrentUser(): Promise<User | null> {
  try {
    const response = await apiClient.get('/api/auth/me');
    return response.data as User;
  } catch (error) {
    return null;
  }
}

export async function getQueryHistory(limit: number = 50, offset: number = 0): Promise<QueryHistoryItem[]> {
  const response = await apiClient.get('/api/auth/history', {
    params: { limit, offset }
  });
  return response.data as QueryHistoryItem[];
}

// Get full query history with results for restoring widgets
export async function getQueryHistoryWithResults(limit: number = 20): Promise<QueryHistoryDetail[]> {
  const response = await apiClient.get('/api/auth/history/widgets', {
    params: { limit }
  });
  return response.data as QueryHistoryDetail[];
}

// Delete a query from history
export async function deleteQueryHistory(queryId: string): Promise<void> {
  await apiClient.delete(`/api/auth/history/${queryId}`);
}

export function logout(): void {
  clearAuth();
}

// ==================== Query API ====================

export async function submitQuery(request: QueryRequest): Promise<QueryResponse | ClarificationResponse | ErrorResponse> {
  const response = await apiClient.post('/api/query', {
    query: request.query,
    include_chart: request.include_chart ?? true,
    max_results: request.max_results ?? 100,
    context: request.context,
    stream_answer: request.stream_answer ?? false,
  });
  return response.data;
}

export interface StreamCallbacks {
  onResults?: (data: {
    query_id: string;
    intent: string;
    sql: string;
    explanation: string;
    results: Record<string, any>[];
    result_count: number;
    columns: string[];
    execution_time_ms: number;
  }) => void;
  onAnswerChunk?: (chunk: string) => void;
  onVisualizationAvailable?: (data: {
    query_id: string;
    status: string;
  }) => void;
  onVisualization?: (data: {
    type: string;
    config: Record<string, any>;
    chart_js_config?: Record<string, any>;
  }) => void;
}

export async function submitQueryStream(
  request: QueryRequest,
  callbacks: StreamCallbacks
): Promise<QueryResponse | ClarificationResponse | ErrorResponse> {
  const token = getStoredToken();
  const headers: Record<string, string> = {
    'Content-Type': 'application/json',
  };
  if (token) {
    headers['Authorization'] = `Bearer ${token}`;
  }

  const response = await fetch(`${API_URL}/api/query`, {
    method: 'POST',
    headers,
    body: JSON.stringify({
      query: request.query,
      include_chart: request.include_chart ?? true,
      max_results: request.max_results ?? 100,
      context: request.context,
      stream_answer: true,
    }),
  });

  if (!response.ok) {
    const error = await response.json();
    throw new Error(error.error_message || 'Failed to submit query');
  }

  // Check if it's a streaming response
  if (response.headers.get('content-type')?.includes('text/event-stream')) {
    const reader = response.body?.getReader();
    const decoder = new TextDecoder();
    let buffer = '';
    let fullResponse: QueryResponse | null = null;

    if (!reader) {
      throw new Error('Response body is not readable');
    }

    while (true) {
      const { done, value } = await reader.read();
      if (done) break;

      buffer += decoder.decode(value, { stream: true });
      const lines = buffer.split('\n');
      buffer = lines.pop() || '';

      for (const line of lines) {
        if (line.startsWith('data: ')) {
          try {
            const data = JSON.parse(line.slice(6));
            console.log('[Stream] Received event:', data.type, data);
            
            // Call callbacks immediately as events arrive
            if (data.type === 'results' && callbacks.onResults) {
              console.log('[Stream] Calling onResults callback');
              callbacks.onResults(data.data);
            } else if (data.type === 'answer_chunk' && callbacks.onAnswerChunk) {
              console.log('[Stream] Calling onAnswerChunk callback, chunk:', data.chunk);
              callbacks.onAnswerChunk(data.chunk);
            } else if (data.type === 'visualization_available' && callbacks.onVisualizationAvailable) {
              console.log('[Stream] Visualization available event received, query_id:', data.data?.query_id, 'status:', data.data?.status);
              callbacks.onVisualizationAvailable(data.data);
            } else if (data.type === 'visualization_available') {
              console.warn('[Stream] Visualization available event received but no callback registered');
            } else if (data.type === 'visualization' && callbacks.onVisualization) {
              console.log('[Stream] Calling onVisualization callback');
              callbacks.onVisualization(data.data);
            } else if (data.type === 'complete') {
              console.log('[Stream] Received complete event');
              fullResponse = data.response as QueryResponse;
            }
          } catch (e) {
            // Ignore parse errors
            console.error('Error parsing stream data:', e);
          }
        }
      }
    }

    if (fullResponse) {
      return fullResponse;
    }
    throw new Error('Streaming response incomplete');
  } else {
    // Non-streaming response
    return await response.json();
  }
}

export async function getExamples(): Promise<ExamplesResponse> {
  const response = await apiClient.get('/api/examples');
  return response.data;
}

export async function healthCheck(): Promise<{ status: string; database_connected: boolean }> {
  const response = await apiClient.get('/api/health');
  return response.data;
}

export async function fetchVisualization(queryId: string): Promise<{
  type: string;
  config: Record<string, any>;
  chart_js_config?: Record<string, any>;
}> {
  try {
    const response = await apiClient.get(`/api/visualization/${queryId}`);
    return response.data;
  } catch (error: any) {
    // Re-throw with more context for better error handling
    if (error.response) {
      // Include the response data in the error for the handler to use
      error.response.data = error.response.data || {};
      error.response.data.error_code = error.response.data.error_code || 'UNKNOWN_ERROR';
      error.response.data.error_message = error.response.data.error_message || error.message;
    }
    throw error;
  }
}



