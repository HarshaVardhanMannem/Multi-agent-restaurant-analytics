'use client';

import { useState, useEffect, useCallback } from 'react';
import QueryInput from '@/components/QueryInput';
import ChartWidget from '@/components/ChartWidget';
import ClarificationDialog from '@/components/ClarificationDialog';
import ErrorAlert from '@/components/ErrorAlert';
import { useAuth } from '@/lib/auth-context';
import {
  QueryResponse,
  ClarificationResponse,
  ErrorResponse,
  ExampleQuery,
  Widget,
  VisualizationType,
  QueryIntent,
} from '@/types/api';
import { submitQuery, submitQueryStream, getExamples, getQueryHistoryWithResults, deleteQueryHistory } from '@/lib/api';
import { UtensilsCrossed, TrendingUp, LayoutDashboard, Trash2, Sparkles, LogOut, User, Lock, Mail, Loader2, AlertCircle, BarChart3, PieChart, LineChart, History } from 'lucide-react';

// Login/Register Page Component
function AuthPage() {
  const [mode, setMode] = useState<'login' | 'register'>('login');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [fullName, setFullName] = useState('');
  const [error, setError] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  
  const { login, register } = useAuth();

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');
    setIsLoading(true);

    try {
      if (mode === 'login') {
        await login({ email, password });
      } else {
        await register({ email, password, full_name: fullName || undefined });
      }
    } catch (err: any) {
      setError(err.response?.data?.detail || err.message || 'An error occurred. Please try again.');
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-gray-50 via-primary-50/30 to-gray-100 flex">
      {/* Left Side - Branding */}
      <div className="hidden lg:flex lg:w-1/2 bg-gradient-to-br from-primary-600 to-primary-800 p-12 flex-col justify-between relative overflow-hidden">
        {/* Background Pattern */}
        <div className="absolute inset-0 opacity-10">
          <div className="absolute top-20 left-20 w-72 h-72 bg-white rounded-full blur-3xl"></div>
          <div className="absolute bottom-20 right-20 w-96 h-96 bg-white rounded-full blur-3xl"></div>
        </div>
        
        <div className="relative z-10">
          <div className="flex items-center gap-3 mb-8">
            <div className="p-3 bg-white/20 backdrop-blur-sm rounded-xl">
              <UtensilsCrossed className="text-white" size={32} />
            </div>
            <div>
              <h1 className="text-2xl font-bold text-white">Restaurant Analytics</h1>
              <p className="text-primary-200 text-sm">AI-Powered Insights</p>
            </div>
          </div>
          
          <h2 className="text-4xl font-bold text-white leading-tight mb-6">
            Transform your restaurant data into actionable insights
          </h2>
          <p className="text-primary-100 text-lg">
            Ask questions in natural language and get instant visualizations, trends, and analysis for your business.
          </p>
        </div>
        
        {/* Feature Cards */}
        <div className="relative z-10 space-y-4">
          <div className="flex items-center gap-4 bg-white/10 backdrop-blur-sm rounded-xl p-4">
            <div className="p-2 bg-white/20 rounded-lg">
              <BarChart3 className="text-white" size={24} />
            </div>
            <div>
              <h3 className="text-white font-medium">Smart Visualizations</h3>
              <p className="text-primary-200 text-sm">Auto-generated charts and graphs</p>
            </div>
          </div>
          <div className="flex items-center gap-4 bg-white/10 backdrop-blur-sm rounded-xl p-4">
            <div className="p-2 bg-white/20 rounded-lg">
              <PieChart className="text-white" size={24} />
            </div>
            <div>
              <h3 className="text-white font-medium">Natural Language Queries</h3>
              <p className="text-primary-200 text-sm">Just ask like you're talking to a person</p>
            </div>
          </div>
          <div className="flex items-center gap-4 bg-white/10 backdrop-blur-sm rounded-xl p-4">
            <div className="p-2 bg-white/20 rounded-lg">
              <LineChart className="text-white" size={24} />
            </div>
            <div>
              <h3 className="text-white font-medium">Query History</h3>
              <p className="text-primary-200 text-sm">Track and revisit your past analyses</p>
            </div>
          </div>
        </div>
      </div>

      {/* Right Side - Auth Form */}
      <div className="w-full lg:w-1/2 flex items-center justify-center p-8">
        <div className="w-full max-w-md">
          {/* Mobile Logo */}
          <div className="lg:hidden flex items-center justify-center gap-3 mb-8">
            <div className="p-3 bg-gradient-to-br from-primary-500 to-primary-600 rounded-xl shadow-lg">
              <UtensilsCrossed className="text-white" size={28} />
            </div>
            <div>
              <h1 className="text-xl font-bold text-gray-900">Restaurant Analytics</h1>
              <p className="text-gray-500 text-sm">AI-Powered Insights</p>
            </div>
          </div>

          <div className="bg-white rounded-2xl shadow-xl border border-gray-100 overflow-hidden">
            {/* Header */}
            <div className="px-8 py-6 bg-gradient-to-r from-primary-500 to-primary-600 text-white">
              <h2 className="text-2xl font-bold">
                {mode === 'login' ? 'Welcome Back' : 'Create Account'}
              </h2>
              <p className="text-primary-100 mt-1">
                {mode === 'login' 
                  ? 'Sign in to access your analytics dashboard' 
                  : 'Get started with your free account'}
              </p>
            </div>

            {/* Form */}
            <form onSubmit={handleSubmit} className="p-8 space-y-5">
              {error && (
                <div className="flex items-center gap-2 p-3 bg-red-50 border border-red-200 rounded-lg text-red-700 text-sm">
                  <AlertCircle size={16} className="flex-shrink-0" />
                  {error}
                </div>
              )}

              {mode === 'register' && (
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1.5">
                    Full Name <span className="text-gray-400">(optional)</span>
                  </label>
                  <div className="relative">
                    <User className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400" size={18} />
                    <input
                      type="text"
                      value={fullName}
                      onChange={(e) => setFullName(e.target.value)}
                      placeholder="John Doe"
                      className="w-full pl-10 pr-4 py-3 border border-gray-300 rounded-xl focus:ring-2 focus:ring-primary-500 focus:border-primary-500 transition-colors"
                    />
                  </div>
                </div>
              )}

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1.5">
                  Email Address
                </label>
                <div className="relative">
                  <Mail className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400" size={18} />
                  <input
                    type="email"
                    value={email}
                    onChange={(e) => setEmail(e.target.value)}
                    placeholder="you@example.com"
                    required
                    className="w-full pl-10 pr-4 py-3 border border-gray-300 rounded-xl focus:ring-2 focus:ring-primary-500 focus:border-primary-500 transition-colors"
                  />
                </div>
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1.5">
                  Password
                </label>
                <div className="relative">
                  <Lock className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400" size={18} />
                  <input
                    type="password"
                    value={password}
                    onChange={(e) => setPassword(e.target.value)}
                    placeholder={mode === 'register' ? 'Min. 8 characters' : '••••••••'}
                    required
                    minLength={mode === 'register' ? 8 : undefined}
                    className="w-full pl-10 pr-4 py-3 border border-gray-300 rounded-xl focus:ring-2 focus:ring-primary-500 focus:border-primary-500 transition-colors"
                  />
                </div>
              </div>

              <button
                type="submit"
                disabled={isLoading}
                className="w-full py-3 bg-gradient-to-r from-primary-500 to-primary-600 text-white font-semibold rounded-xl hover:from-primary-600 hover:to-primary-700 disabled:opacity-50 disabled:cursor-not-allowed transition-all flex items-center justify-center gap-2 shadow-lg shadow-primary-500/25"
              >
                {isLoading ? (
                  <>
                    <Loader2 className="animate-spin" size={20} />
                    {mode === 'login' ? 'Signing in...' : 'Creating account...'}
                  </>
                ) : (
                  mode === 'login' ? 'Sign In' : 'Create Account'
                )}
              </button>

              <div className="text-center text-sm text-gray-600 pt-2">
                {mode === 'login' ? (
                  <>
                    Don't have an account?{' '}
                    <button
                      type="button"
                      onClick={() => { setMode('register'); setError(''); }}
                      className="text-primary-600 hover:text-primary-700 font-semibold"
                    >
                      Sign up for free
                    </button>
                  </>
                ) : (
                  <>
                    Already have an account?{' '}
                    <button
                      type="button"
                      onClick={() => { setMode('login'); setError(''); }}
                      className="text-primary-600 hover:text-primary-700 font-semibold"
                    >
                      Sign in
                    </button>
                  </>
                )}
              </div>
            </form>
          </div>
        </div>
      </div>
    </div>
  );
}

// Main Dashboard Component
function Dashboard() {
  const [widgets, setWidgets] = useState<Widget[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [isLoadingHistory, setIsLoadingHistory] = useState(true);
  const [clarification, setClarification] = useState<ClarificationResponse | null>(null);
  const [error, setError] = useState<ErrorResponse | null>(null);
  const [examples, setExamples] = useState<ExampleQuery[]>([]);

  const { user, logout } = useAuth();

  // Load examples on mount
  useEffect(() => {
    getExamples()
      .then((data) => setExamples(data.examples))
      .catch((err) => console.error('Failed to load examples:', err));
  }, []);

  // Load saved widgets from query history when user is authenticated
  useEffect(() => {
    const loadSavedWidgets = async () => {
      if (!user) {
        setIsLoadingHistory(false);
        return;
      }

      try {
        setIsLoadingHistory(true);
        const history = await getQueryHistoryWithResults(20);
        
        // Convert history items to widgets
        const restoredWidgets: Widget[] = history.map((item) => ({
          id: `widget-${item.query_id}`,
          query: item.natural_query,
          response: {
            success: true,
            query_id: item.query_id,
            intent: item.intent as QueryIntent,
            sql: item.generated_sql,
            explanation: '',
            answer: item.answer || undefined,
            results: item.results_sample,
            result_count: item.result_count,
            columns: item.columns,
            visualization: {
              type: item.visualization_type as VisualizationType,
              config: item.visualization_config,
              chart_js_config: item.visualization_config?.chart_js_config,
            },
            execution_time_ms: item.execution_time_ms,
            total_processing_time_ms: item.execution_time_ms,
          },
          createdAt: new Date(item.created_at),
        }));

        setWidgets(restoredWidgets);
      } catch (err) {
        console.error('Failed to load saved widgets:', err);
      } finally {
        setIsLoadingHistory(false);
      }
    };

    loadSavedWidgets();
  }, [user]);

  const handleQuery = useCallback(async (
    query: string, 
    context?: Array<{ role: string; content: string }>
  ) => {
    setIsLoading(true);
    setError(null);
    setClarification(null);

    // Create a temporary widget for streaming
    const tempWidgetId = `widget-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`;
    // Use a ref-like object to track streaming answer across callbacks
    const streamingState = { answer: '' };
    let tempWidget: Widget | null = null;

    try {
      // Use streaming by default
      const response = await submitQueryStream(
        { query, include_chart: true, context, stream_answer: true },
        {
          onResults: (resultsData) => {
            console.log('[Frontend] onResults called with:', resultsData);
            // Create widget with SQL results immediately
            setWidgets((prev) => {
              const existingIndex = prev.findIndex((w) => w.id === tempWidgetId);
              if (existingIndex >= 0) {
                // Update existing widget with results
                const updated = [...prev];
                updated[existingIndex] = {
                  ...updated[existingIndex],
                  response: {
                    ...updated[existingIndex].response,
                    query_id: resultsData.query_id,
                    intent: resultsData.intent as QueryIntent,
                    sql: resultsData.sql,
                    explanation: resultsData.explanation,
                    results: resultsData.results,
                    result_count: resultsData.result_count,
                    columns: resultsData.columns,
                    execution_time_ms: resultsData.execution_time_ms,
                  },
                };
                return updated;
              } else {
                // Create new widget with results
                const newWidget: Widget = {
                  id: tempWidgetId,
                  query,
                  response: {
                    success: true,
                    query_id: resultsData.query_id,
                    intent: resultsData.intent as QueryIntent,
                    sql: resultsData.sql,
                    explanation: resultsData.explanation,
                    answer: '',
                    results: resultsData.results,
                    result_count: resultsData.result_count,
                    columns: resultsData.columns,
                    visualization: {
                      type: VisualizationType.TABLE,
                      config: {},
                    },
                    execution_time_ms: resultsData.execution_time_ms,
                    total_processing_time_ms: resultsData.execution_time_ms,
                  },
                  createdAt: new Date(),
                };
                tempWidget = newWidget;
                return [newWidget, ...prev];
              }
            });
          },
          onAnswerChunk: (chunk: string) => {
            console.log('[Frontend] onAnswerChunk called, chunk:', chunk);
            // Update answer as chunks arrive
            streamingState.answer += chunk;
            
            // Update widget with streaming answer - use functional update to ensure we get latest state
            setWidgets((prev) =>
              prev.map((w) =>
                w.id === tempWidgetId
                  ? { 
                      ...w, 
                      response: { 
                        ...w.response, 
                        answer: streamingState.answer 
                      } 
                    }
                  : w
              )
            );
          },
          onVisualizationAvailable: (vizAvailableData) => {
            console.log('[Frontend] Visualization available for query_id:', vizAvailableData.query_id, 'status:', vizAvailableData.status);
            // Mark widget as having visualization available (or not applicable)
            setWidgets((prev) =>
              prev.map((w) => {
                // Match by query_id (more reliable than tempWidgetId)
                if (w.response.query_id === vizAvailableData.query_id) {
                  console.log('[Frontend] Updating widget visualization availability:', w.id);
                  return {
                    ...w,
                    response: {
                      ...w.response,
                      visualization: {
                        ...w.response.visualization,
                        // Only set available to true if status is not 'not_applicable'
                        available: vizAvailableData.status !== 'not_applicable',
                        status: vizAvailableData.status,
                      },
                    },
                  };
                }
                return w;
              })
            );
          },
          onVisualization: (vizData) => {
            console.log('[Frontend] onVisualization called with:', vizData);
            // Update widget with visualization
            setWidgets((prev) =>
              prev.map((w) =>
                w.id === tempWidgetId
                  ? {
                      ...w,
                      response: {
                        ...w.response,
                        visualization: {
                          type: vizData.type as VisualizationType,
                          config: vizData.config,
                          chart_js_config: vizData.chart_js_config,
                          available: true,
                        },
                      },
                    }
                  : w
              )
            );
          },
        }
      );

      if (response.success === false) {
        setError(response as ErrorResponse);
        setIsLoading(false);
        // Remove temp widget if it exists
        if (tempWidget) {
          setWidgets((prev) => prev.filter((w) => w.id !== tempWidgetId));
        }
        return;
      }

      if ('clarification_needed' in response && response.clarification_needed) {
        setClarification(response as ClarificationResponse);
        setIsLoading(false);
        // Remove temp widget if it exists
        if (tempWidget) {
          setWidgets((prev) => prev.filter((w) => w.id !== tempWidgetId));
        }
        return;
      }

      const queryResponse = response as QueryResponse;
      
      // Update the temporary widget with full response, or create new one
      setWidgets((prev) => {
        const existingIndex = prev.findIndex((w) => w.id === tempWidgetId);
        if (existingIndex >= 0) {
          // Update existing widget
          const updated = [...prev];
          updated[existingIndex] = {
            id: tempWidgetId,
            query,
            response: queryResponse,
            createdAt: new Date(),
          };
          return updated;
        } else {
          // Create new widget
          return [
            {
              id: tempWidgetId,
              query,
              response: queryResponse,
              createdAt: new Date(),
            },
            ...prev,
          ];
        }
      });
      
      setIsLoading(false);
    } catch (err: any) {
      setError({
        success: false,
        error_code: 'NETWORK_ERROR',
        error_message: err.message || 'Failed to submit query',
        suggestions: ['Check your internet connection', 'Make sure the backend API is running'],
      });
      setIsLoading(false);
      // Remove temp widget if it exists
      if (tempWidget) {
        setWidgets((prev) => prev.filter((w) => w.id !== tempWidgetId));
      }
    }
  }, []);

  const handleRemoveWidget = useCallback(async (id: string) => {
    // Find the widget to get its query_id
    const widget = widgets.find((w) => w.id === id);
    
    if (!widget) {
      // Widget not found, just remove from state (shouldn't happen, but handle gracefully)
      setWidgets((prev) => prev.filter((w) => w.id !== id));
      return;
    }
    
    // If widget has a query_id, it's saved in the database - delete it
    if (widget.response.query_id) {
      try {
        await deleteQueryHistory(widget.response.query_id);
        // Remove from state after successful deletion
        setWidgets((prev) => prev.filter((w) => w.id !== id));
      } catch (err) {
        console.error('Failed to delete widget from database:', err);
        // Still remove from UI even if API call fails (optimistic update)
        // The widget will reappear on refresh if deletion failed, which is acceptable
        setWidgets((prev) => prev.filter((w) => w.id !== id));
      }
    } else {
      // Widget doesn't have a query_id, so it's a new unsaved widget - just remove from state
      setWidgets((prev) => prev.filter((w) => w.id !== id));
    }
  }, [widgets]);

  const handleClarificationConfirm = useCallback(
    (clarificationText: string, originalQuery: string) => {
      setClarification(null);
      
      // Create a merged query that combines original question with clarification
      const mergedQuery = `${originalQuery}. Additional context: ${clarificationText}`;
      
      // Build context for the backend to understand this is a follow-up
      const context = [
        { role: 'user', content: originalQuery },
        { role: 'assistant', content: 'I need more information to answer this question.' },
        { role: 'user', content: clarificationText }
      ];
      
      handleQuery(mergedQuery, context);
    },
    [handleQuery]
  );

  return (
    <div className="min-h-screen bg-gradient-to-br from-gray-50 via-primary-50/20 to-gray-100">
      {/* Header */}
      <header className="bg-white/80 backdrop-blur-md border-b border-gray-200/50 shadow-soft sticky top-0 z-50">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              <div className="p-2.5 bg-gradient-to-br from-primary-500 via-primary-600 to-primary-700 rounded-xl shadow-lg hover:shadow-glow transition-shadow">
                <UtensilsCrossed className="text-white" size={24} />
              </div>
              <div>
                <h1 className="text-2xl font-bold gradient-text">Restaurant Analytics</h1>
                <p className="text-sm text-gray-600 font-medium">AI-powered insights dashboard</p>
              </div>
            </div>
            <div className="flex items-center gap-4">
              {widgets.length > 0 && (
                <div className="flex items-center gap-3">
                  <span className="text-sm text-gray-500">
                    {widgets.length} widget{widgets.length !== 1 ? 's' : ''}
                  </span>
                  <button
                    onClick={() => setWidgets([])}
                    className="flex items-center gap-2 px-4 py-2 text-sm text-gray-600 hover:text-accent-600 hover:bg-accent-50 rounded-xl transition-all duration-200 hover:scale-105 font-medium shadow-sm hover:shadow-md"
                  >
                    <Trash2 size={16} />
                    Clear all
                  </button>
                </div>
              )}
              
              {/* User Section */}
              <div className="flex items-center gap-2 pl-4 border-l border-gray-200">
                <div className="flex items-center gap-3">
                  <div className="flex items-center gap-2">
                    <div className="w-9 h-9 rounded-full bg-gradient-to-br from-primary-500 via-primary-600 to-primary-700 flex items-center justify-center text-white text-sm font-bold shadow-md">
                      {user?.email?.charAt(0).toUpperCase() || 'U'}
                    </div>
                    <span className="text-sm text-gray-700 hidden sm:inline">{user?.email}</span>
                  </div>
                  <button
                    onClick={logout}
                    className="flex items-center gap-2 px-4 py-2 text-sm text-gray-600 hover:text-gray-900 hover:bg-gray-100 rounded-xl transition-all duration-200 hover:scale-105 font-medium shadow-sm hover:shadow-md"
                  >
                    <LogOut size={16} />
                    <span className="hidden sm:inline">Sign out</span>
                  </button>
                </div>
              </div>
            </div>
          </div>
        </div>
      </header>

      {/* Main Content */}
      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {/* Query Input Section */}
        <div className="mb-8">
          <div className="bg-white/90 backdrop-blur-sm rounded-2xl shadow-soft border border-gray-100 p-8 hover:shadow-medium transition-shadow">
            <div className="flex items-center gap-3 mb-6">
              <div className="p-2 bg-gradient-to-br from-primary-500 to-primary-600 rounded-xl shadow-md">
                <Sparkles className="text-white" size={20} />
              </div>
              <h2 className="text-xl font-bold text-gray-900">Ask a Question</h2>
            </div>
            <QueryInput onSubmit={handleQuery} isLoading={isLoading} examples={examples} />
          </div>

          {error && <ErrorAlert error={error} onClose={() => setError(null)} />}
        </div>

        {/* Loading State */}
        {isLoading && (
          <div className="mb-8 animate-fade-in">
            <div className="bg-white/90 backdrop-blur-sm rounded-2xl shadow-soft border border-gray-100 p-12">
              <div className="flex flex-col items-center justify-center">
                <div className="relative">
                  <div className="w-20 h-20 border-4 border-primary-200 rounded-full animate-spin border-t-primary-600"></div>
                  <div className="absolute inset-0 flex items-center justify-center">
                    <TrendingUp className="text-primary-600 animate-pulse" size={28} />
                  </div>
                </div>
                <p className="mt-6 text-gray-700 font-semibold text-lg">Analyzing your question...</p>
                <p className="text-sm text-gray-500 mt-1">Generating insights and visualizations</p>
              </div>
            </div>
          </div>
        )}

        {/* Widgets Grid */}
        {widgets.length > 0 && (
          <div className="space-y-6 animate-fade-in">
            <div className="flex items-center gap-3 mb-2">
              <div className="p-2 bg-gradient-to-br from-primary-500 to-primary-600 rounded-xl shadow-md">
                <LayoutDashboard className="text-white" size={20} />
              </div>
              <h2 className="text-xl font-bold text-gray-900">Your Insights</h2>
              <span className="ml-auto px-3 py-1 bg-primary-100 text-primary-700 rounded-full text-sm font-semibold shadow-sm">
                {widgets.length} {widgets.length === 1 ? 'widget' : 'widgets'}
              </span>
            </div>

            <div className="grid grid-cols-1 gap-6">
              {widgets.map((widget) => (
                <ChartWidget
                  key={widget.id}
                  widget={widget}
                  onRemove={handleRemoveWidget}
                  onUpdate={(id, updates) => {
                    console.log('[Page] onUpdate called:', { id, updates });
                    setWidgets((prev) =>
                      prev.map((w) => {
                        if (w.id === id) {
                          const updated = {
                            ...w,
                            response: {
                              ...w.response,
                              ...updates,
                              // Properly merge visualization if it's being updated
                              visualization: updates.visualization
                                ? { ...w.response.visualization, ...updates.visualization }
                                : w.response.visualization,
                            },
                          };
                          console.log('[Page] Widget updated:', updated);
                          return updated;
                        }
                        return w;
                      })
                    );
                  }}
                />
              ))}
            </div>
          </div>
        )}

        {/* Loading History State */}
        {isLoadingHistory && widgets.length === 0 && !isLoading && (
          <div className="text-center py-16">
            <div className="inline-flex items-center justify-center w-16 h-16 bg-gradient-to-br from-primary-100 to-primary-200 rounded-2xl mb-4">
              <History className="text-primary-600 animate-pulse" size={32} />
            </div>
            <p className="text-gray-600 font-medium">Loading your saved insights...</p>
          </div>
        )}

        {/* Empty State */}
        {widgets.length === 0 && !isLoading && !isLoadingHistory && (
          <div className="text-center py-16">
            <div className="inline-flex items-center justify-center w-20 h-20 bg-gradient-to-br from-primary-100 to-primary-200 rounded-2xl mb-6">
              <UtensilsCrossed className="text-primary-600" size={40} />
            </div>
            <h3 className="text-xl font-semibold text-gray-900 mb-2">
              Welcome, {user?.full_name || user?.email?.split('@')[0] || 'User'}!
            </h3>
            <p className="text-gray-500 mb-8 max-w-md mx-auto">
              Ask questions about your restaurant data in natural language and get instant visualizations and insights.
            </p>
            {examples.length > 0 && (
              <div className="max-w-3xl mx-auto">
                <p className="text-sm font-medium text-gray-700 mb-4">Try one of these example queries:</p>
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  {examples.slice(0, 4).map((example, idx) => (
                    <button
                      key={idx}
                      onClick={() => handleQuery(example.query)}
                      className="text-left p-4 bg-white border border-gray-200 rounded-xl hover:border-primary-300 hover:shadow-lg hover:scale-[1.02] transition-all group"
                    >
                      <p className="text-sm text-gray-900 font-medium group-hover:text-primary-700 transition-colors">
                        {example.query}
                      </p>
                      <p className="text-xs text-gray-500 mt-2">{example.description}</p>
                    </button>
                  ))}
                </div>
              </div>
            )}
          </div>
        )}
      </main>

      {/* Clarification Dialog */}
      {clarification && (
        <ClarificationDialog
          clarification={clarification}
          onClose={() => setClarification(null)}
          onConfirm={handleClarificationConfirm}
        />
      )}
    </div>
  );
}

// Loading Screen Component
function LoadingScreen() {
  return (
    <div className="min-h-screen bg-gradient-to-br from-gray-50 to-gray-100 flex items-center justify-center">
      <div className="text-center">
        <div className="inline-flex items-center justify-center w-16 h-16 bg-gradient-to-br from-primary-500 to-primary-600 rounded-2xl mb-4 shadow-lg">
          <UtensilsCrossed className="text-white animate-pulse" size={32} />
        </div>
        <div className="flex items-center gap-2 justify-center">
          <Loader2 className="animate-spin text-primary-600" size={20} />
          <span className="text-gray-600 font-medium">Loading...</span>
        </div>
      </div>
    </div>
  );
}

// Main Page Component
export default function Home() {
  const { isAuthenticated, isLoading } = useAuth();

  // Show loading screen while checking auth
  if (isLoading) {
    return <LoadingScreen />;
  }

  // Show login/register page if not authenticated
  if (!isAuthenticated) {
    return <AuthPage />;
  }

  // Show dashboard if authenticated
  return <Dashboard />;
}

