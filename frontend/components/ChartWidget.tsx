'use client';

import { useMemo, useState, useEffect, useRef } from 'react';
import {
  Chart as ChartJS,
  CategoryScale,
  LinearScale,
  BarElement,
  LineElement,
  PointElement,
  ArcElement,
  Title,
  Tooltip,
  Legend,
  Filler,
} from 'chart.js';
import { Bar, Line, Pie, Doughnut } from 'react-chartjs-2';
import { QueryResponse, VisualizationType } from '@/types/api';
import { fetchVisualization } from '@/lib/api';
import { 
  X, Copy, Check, ChevronDown, ChevronUp, Download, 
  Table, BarChart3, Database, Lightbulb, Clock, Eye, Loader2, Sparkles, 
  TrendingUp, CheckCircle2, AlertCircle
} from 'lucide-react';
import ReactMarkdown from 'react-markdown';
import MetricCard from './MetricCard';

ChartJS.register(
  CategoryScale,
  LinearScale,
  BarElement,
  LineElement,
  PointElement,
  ArcElement,
  Title,
  Tooltip,
  Legend,
  Filler
);

interface ChartWidgetProps {
  widget: { id: string; query: string; response: QueryResponse };
  onRemove?: (id: string) => void;
  onUpdate?: (id: string, updates: Partial<QueryResponse>) => void;
}

// Helper to detect if result is a single metric
function isSingleMetric(results: Record<string, any>[], columns: string[]): boolean {
  if (results.length !== 1) return false;
  // Single row with 1-3 numeric columns is likely a metric
  const numericColumns = columns.filter(col => typeof results[0][col] === 'number');
  return numericColumns.length >= 1 && numericColumns.length <= 3;
}

// Helper to format values intelligently
function formatValue(value: any, columnName: string): string {
  if (value === null || value === undefined) return '-';
  
  if (typeof value === 'number') {
    // Detect currency columns
    const currencyKeywords = ['revenue', 'sales', 'total', 'amount', 'price', 'cost', 'avg_', 'sum_'];
    const isCurrency = currencyKeywords.some(kw => columnName.toLowerCase().includes(kw));
    
    if (isCurrency) {
      return new Intl.NumberFormat('en-US', {
        style: 'currency',
        currency: 'USD',
        minimumFractionDigits: 2,
      }).format(value);
    }
    
    // Detect percentage columns
    if (columnName.toLowerCase().includes('percent') || columnName.toLowerCase().includes('rate')) {
      return `${value.toFixed(1)}%`;
    }
    
    // Regular number
    return new Intl.NumberFormat('en-US', {
      maximumFractionDigits: 2,
    }).format(value);
  }
  
  return String(value);
}

// Helper to determine metric icon
function getMetricIcon(columnName: string): 'dollar' | 'orders' | 'users' | 'store' | 'time' | 'items' {
  const name = columnName.toLowerCase();
  if (name.includes('revenue') || name.includes('sales') || name.includes('total') || name.includes('amount')) return 'dollar';
  if (name.includes('order') || name.includes('count')) return 'orders';
  if (name.includes('customer') || name.includes('user')) return 'users';
  if (name.includes('location') || name.includes('store')) return 'store';
  if (name.includes('time') || name.includes('hour') || name.includes('avg')) return 'time';
  return 'items';
}

export default function ChartWidget({ widget, onRemove, onUpdate }: ChartWidgetProps) {
  const [copied, setCopied] = useState(false);
  const [expanded, setExpanded] = useState(true);
  const [showSQL, setShowSQL] = useState(false);
  const [loadingViz, setLoadingViz] = useState(false);
  const [vizError, setVizError] = useState<string | null>(null);
  const [vizLoaded, setVizLoaded] = useState(false);
  const { response } = widget;
  const prevChartConfigRef = useRef(response.visualization?.chart_js_config);
  
  // Track when visualization loads for animation
  useEffect(() => {
    const currentChartConfig = response.visualization?.chart_js_config;
    const prevChartConfig = prevChartConfigRef.current;
    
    if (currentChartConfig && !prevChartConfig) {
      // Visualization just loaded
      setTimeout(() => setVizLoaded(true), 100);
      // Clear after animation
      setTimeout(() => setVizLoaded(false), 3000);
    }
    
    prevChartConfigRef.current = currentChartConfig;
  }, [response.visualization?.chart_js_config]);
  
  // Determine if button should be shown
  // Hide button if:
  // - No query_id
  // - Chart already loaded
  // - Status is 'not_applicable' (explicitly not applicable)
  // - Available is explicitly false
  const shouldShowButton = response.query_id && 
    !response.visualization?.chart_js_config && 
    response.visualization?.status !== 'not_applicable' &&
    response.visualization?.status !== 'error' &&
    (response.visualization?.available !== false);
  
  if (response.query_id && !response.visualization?.chart_js_config) {
    console.log('[ChartWidget] Visualization state:', {
      query_id: response.query_id,
      available: response.visualization?.available,
      status: response.visualization?.status,
      has_chart_js_config: !!response.visualization?.chart_js_config,
      type: response.visualization?.type,
      shouldShowButton
    });
  }

  const chartData = useMemo(() => {
    if (!response.visualization?.chart_js_config) {
      return null;
    }

    const config = response.visualization.chart_js_config;
    
    if (response.visualization.type === VisualizationType.TABLE) {
      return null;
    }

    return config;
  }, [response.visualization]);

  const handleCopySQL = async () => {
    await navigator.clipboard.writeText(response.sql);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  const handleExportCSV = () => {
    if (response.results.length === 0) return;
    
    const headers = response.columns.join(',');
    const rows = response.results.map(row => 
      response.columns.map(col => {
        const val = row[col];
        // Escape commas and quotes in CSV
        if (typeof val === 'string' && (val.includes(',') || val.includes('"'))) {
          return `"${val.replace(/"/g, '""')}"`;
        }
        return val ?? '';
      }).join(',')
    );
    
    const csv = [headers, ...rows].join('\n');
    const blob = new Blob([csv], { type: 'text/csv' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `${widget.query.slice(0, 30).replace(/[^a-z0-9]/gi, '_')}.csv`;
    a.click();
    URL.revokeObjectURL(url);
  };

  const handleViewVisualization = async () => {
    console.log('[ChartWidget] handleViewVisualization called', {
      query_id: response.query_id,
      widget_id: widget.id,
      has_onUpdate: !!onUpdate
    });
    
    if (!response.query_id) {
      console.warn('[ChartWidget] No query_id available');
      return;
    }
    
    setLoadingViz(true);
    setVizError(null);
    
    try {
      // Poll for visualization until ready
      let attempts = 0;
      const maxAttempts = 30; // 30 seconds max
      
      while (attempts < maxAttempts) {
        try {
          console.log(`[ChartWidget] Fetching visualization (attempt ${attempts + 1}/${maxAttempts})`);
          const vizData = await fetchVisualization(response.query_id);
          
          console.log('[ChartWidget] Visualization fetched successfully:', {
            type: vizData.type,
            has_config: !!vizData.config,
            has_chart_js_config: !!vizData.chart_js_config
          });
          
          // Update widget with visualization via callback
          if (onUpdate) {
            console.log('[ChartWidget] Calling onUpdate with visualization data');
            onUpdate(widget.id, {
              visualization: {
                type: vizData.type as VisualizationType,
                config: vizData.config || {},
                chart_js_config: vizData.chart_js_config,
                available: true,
                status: 'ready',
              },
            });
          } else {
            console.warn('[ChartWidget] onUpdate callback not available');
          }
          
          setLoadingViz(false);
          return;
        } catch (error: any) {
          console.log('[ChartWidget] Error fetching visualization:', {
            status: error.response?.status,
            error_code: error.response?.data?.error_code,
            message: error.response?.data?.error_message || error.message
          });
          
          if (error.response?.status === 202) {
            // Still pending, wait and retry
            attempts++;
            console.log(`[ChartWidget] Visualization pending, retrying in 1s (${attempts}/${maxAttempts})`);
            await new Promise(resolve => setTimeout(resolve, 1000));
            continue;
          } else if (error.response?.status === 404) {
            const errorCode = error.response?.data?.error_code;
            if (errorCode === 'VISUALIZATION_NOT_APPLICABLE') {
              console.log('[ChartWidget] Visualization not applicable');
              setVizError('A chart isn\'t available for this type of data');
              // Update widget to mark visualization as not applicable
              if (onUpdate) {
                onUpdate(widget.id, {
                  visualization: {
                    ...response.visualization,
                    status: 'not_applicable',
                    available: false,
                  },
                });
              }
              setLoadingViz(false);
              return;
            } else if (errorCode === 'VISUALIZATION_NOT_FOUND') {
              // Visualization not found - might still be generating
              attempts++;
              console.log(`[ChartWidget] Visualization not found, retrying in 1s (${attempts}/${maxAttempts})`);
              await new Promise(resolve => setTimeout(resolve, 1000));
              continue;
            }
          }
          
          // For other errors, throw to outer catch
          throw error;
        }
      }
      
      console.warn('[ChartWidget] Visualization generation timed out');
      setVizError('Visualization generation timed out. Please try again.');
      setLoadingViz(false);
    } catch (error: any) {
      console.error('[ChartWidget] Fatal error fetching visualization:', error);
      setVizError(error.response?.data?.error_message || error.message || 'Failed to load visualization');
      setLoadingViz(false);
    }
  };

  const renderChart = () => {
    if (!chartData) return null;

    const chartType = response.visualization.type;

    switch (chartType) {
      case VisualizationType.BAR_CHART:
      case VisualizationType.STACKED_BAR:
        return <Bar data={chartData.data} options={chartData.options} />;
      
      case VisualizationType.LINE_CHART:
      case VisualizationType.MULTI_SERIES:
        return <Line data={chartData.data} options={chartData.options} />;
      
      case VisualizationType.PIE_CHART:
        return <Pie data={chartData.data} options={chartData.options} />;
      
      default:
        return null;
    }
  };

  const renderMetrics = () => {
    if (!isSingleMetric(response.results, response.columns)) return null;
    
    const row = response.results[0];
    const numericColumns = response.columns.filter(col => typeof row[col] === 'number');
    
    return (
      <div className={`grid gap-4 ${numericColumns.length === 1 ? 'grid-cols-1' : numericColumns.length === 2 ? 'grid-cols-2' : 'grid-cols-3'}`}>
        {numericColumns.map(col => (
          <MetricCard
            key={col}
            title={col.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase())}
            value={row[col]}
            icon={getMetricIcon(col)}
            format={col.toLowerCase().includes('revenue') || col.toLowerCase().includes('sales') || col.toLowerCase().includes('total') ? 'currency' : 'number'}
            size="lg"
          />
        ))}
      </div>
    );
  };

  const renderTable = () => {
    if (response.results.length === 0) {
      return (
        <div className="text-center py-8 text-gray-500">
          <Database className="mx-auto mb-2 text-gray-400" size={32} />
          <p>No results found</p>
        </div>
      );
    }

    return (
      <div className="overflow-x-auto rounded-xl border border-gray-200 shadow-sm">
        <table className="min-w-full divide-y divide-gray-200">
          <thead className="bg-gradient-to-r from-gray-50 to-gray-100 border-b-2 border-gray-200">
            <tr>
              {response.columns.map((col) => (
                <th
                  key={col}
                  className="px-5 py-3.5 text-left text-xs font-bold text-gray-700 uppercase tracking-wider"
                >
                  {col.replace(/_/g, ' ').replace(/\b\w/g, (l) => l.toUpperCase())}
                </th>
              ))}
            </tr>
          </thead>
          <tbody className="bg-white divide-y divide-gray-100">
            {response.results.slice(0, 20).map((row, idx) => (
              <tr key={idx} className="hover:bg-gradient-to-r hover:from-primary-50/50 hover:to-transparent transition-all duration-150">
                {response.columns.map((col) => (
                  <td key={col} className="px-5 py-3.5 whitespace-nowrap text-sm text-gray-800 font-medium">
                    {formatValue(row[col], col)}
                  </td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
        {response.results.length > 20 && (
          <div className="px-5 py-3.5 bg-gradient-to-r from-gray-50 to-gray-100 text-sm text-gray-600 font-medium border-t-2 border-gray-200">
            Showing 20 of {response.result_count} results
          </div>
        )}
      </div>
    );
  };

  const renderKeyInsights = () => {
    const insights = (response as any).key_insights;
    if (!insights || insights.length === 0) return null;

    return (
      <div className="mt-6 p-5 bg-gradient-to-br from-warning-50 via-amber-50 to-warning-50 rounded-xl border border-warning-200 shadow-sm">
        <div className="flex items-center gap-2.5 mb-3">
          <div className="p-1.5 bg-warning-500 rounded-lg">
            <Lightbulb className="text-white" size={16} />
          </div>
          <span className="text-sm font-bold text-warning-800">Key Insights</span>
        </div>
        <ul className="space-y-2">
          {insights.map((insight: string, idx: number) => (
            <li key={idx} className="text-sm text-warning-900 flex items-start gap-2.5 font-medium">
              <span className="text-warning-500 font-bold mt-0.5">•</span>
              {insight}
            </li>
          ))}
        </ul>
      </div>
    );
  };

  return (
    <div className="bg-white rounded-2xl shadow-soft border border-gray-100 overflow-hidden hover:shadow-medium hover-lift transition-all duration-300 group">
      {/* Header */}
      <div className="px-6 py-5 bg-gradient-to-br from-primary-50/60 via-primary-50/40 to-white border-b border-primary-100/50 backdrop-blur-sm">
        <div className="flex items-start justify-between">
          <div className="flex-1 min-w-0">
            <h3 className="text-lg font-bold text-gray-900 mb-2 truncate group-hover:text-primary-700 transition-colors" title={widget.query}>
              {response.visualization?.config?.title || widget.query}
            </h3>
            {response.answer && (
              <div className="text-sm text-gray-700 prose prose-sm max-w-none prose-strong:text-primary-700 prose-strong:font-semibold prose-p:my-1">
                <ReactMarkdown>{response.answer}</ReactMarkdown>
              </div>
            )}
            {/* Analyzing indicator - show when visualization is being generated */}
            {response.query_id && 
             response.visualization?.status === 'pending' && 
             !response.visualization?.chart_js_config && (
              <div className="mt-3 flex items-center gap-3 px-4 py-3 bg-gradient-to-r from-primary-50 via-primary-50/80 to-primary-50 border border-primary-200/60 rounded-xl shadow-sm animate-pulse">
                <div className="relative">
                  <Loader2 size={18} className="animate-spin text-primary-600" />
                  <div className="absolute inset-0 bg-primary-200/30 rounded-full blur-sm animate-ping"></div>
                </div>
                <div className="flex-1">
                  <p className="text-sm font-semibold text-primary-900">Analyzing data</p>
                  <p className="text-xs text-primary-600 mt-0.5">Generating visualization...</p>
                </div>
                <Sparkles size={16} className="text-primary-500 animate-pulse" />
              </div>
            )}
          </div>
          <div className="flex items-center gap-1 ml-4 flex-shrink-0">
            {/* View Visualization Button */}
            {/* Show button if visualization might be available */}
            {shouldShowButton && response.results.length > 0 && (
              <button
                onClick={(e) => {
                  e.preventDefault();
                  e.stopPropagation();
                  console.log('[ChartWidget] View Chart button clicked');
                  handleViewVisualization();
                }}
                disabled={loadingViz}
                className="group relative flex items-center gap-2.5 px-5 py-2.5 rounded-xl transition-all duration-300 font-semibold text-sm bg-gradient-to-r from-primary-500 via-primary-600 to-primary-500 text-white hover:from-primary-600 hover:via-primary-700 hover:to-primary-600 hover:scale-105 shadow-lg hover:shadow-xl disabled:bg-gray-100 disabled:text-gray-400 disabled:cursor-not-allowed disabled:hover:scale-100 disabled:shadow-none overflow-hidden"
                title="View Visualization"
                type="button"
              >
                <div className="absolute inset-0 bg-gradient-to-r from-transparent via-white/20 to-transparent -translate-x-full group-hover:translate-x-full transition-transform duration-1000"></div>
                {loadingViz ? (
                  <>
                    <Loader2 size={18} className="animate-spin relative z-10" />
                    <span className="relative z-10">Loading...</span>
                  </>
                ) : (
                  <>
                    <TrendingUp size={18} className="relative z-10 group-hover:scale-110 transition-transform" />
                    <span className="relative z-10">View Chart</span>
                  </>
                )}
              </button>
            )}
            <button
              onClick={() => setShowSQL(!showSQL)}
              className={`p-2.5 rounded-xl transition-all duration-200 ${
                showSQL 
                  ? 'bg-primary-500 text-white shadow-md scale-105' 
                  : 'text-gray-500 hover:text-primary-600 hover:bg-primary-50 hover:scale-105'
              }`}
              title="Show SQL"
            >
              <Database size={16} />
            </button>
            <button
              onClick={handleCopySQL}
              className="p-2.5 text-gray-500 hover:text-success-600 hover:bg-success-50 rounded-xl transition-all duration-200 hover:scale-105"
              title="Copy SQL"
            >
              {copied ? <Check size={16} className="text-success-600" /> : <Copy size={16} />}
            </button>
            <button
              onClick={handleExportCSV}
              className="p-2.5 text-gray-500 hover:text-primary-600 hover:bg-primary-50 rounded-xl transition-all duration-200 hover:scale-105 disabled:opacity-40 disabled:cursor-not-allowed disabled:hover:scale-100"
              title="Export CSV"
              disabled={response.results.length === 0}
            >
              <Download size={16} />
            </button>
            <button
              onClick={() => setExpanded(!expanded)}
              className="p-2.5 text-gray-500 hover:text-gray-700 hover:bg-gray-100 rounded-xl transition-all duration-200 hover:scale-105"
              title={expanded ? 'Collapse' : 'Expand'}
            >
              {expanded ? <ChevronUp size={16} /> : <ChevronDown size={16} />}
            </button>
            {onRemove && (
              <button
                onClick={() => onRemove(widget.id)}
                className="p-2.5 text-gray-500 hover:text-accent-600 hover:bg-accent-50 rounded-xl transition-all duration-200 hover:scale-105"
                title="Remove widget"
              >
                <X size={16} />
              </button>
            )}
          </div>
        </div>
        
        {/* Meta info badges */}
        <div className="mt-4 flex flex-wrap items-center gap-2.5">
          <span className="inline-flex items-center gap-2 px-3.5 py-1.5 bg-gradient-to-r from-primary-500 to-primary-600 text-white rounded-full text-xs font-semibold shadow-md hover:shadow-lg transition-all hover:scale-105">
            <BarChart3 size={13} />
            <span className="capitalize">{response.intent.replace(/_/g, ' ')}</span>
          </span>
          <span className="inline-flex items-center gap-2 px-3.5 py-1.5 bg-white border border-gray-200 rounded-full text-xs font-medium text-gray-700 shadow-sm hover:bg-gray-50 hover:border-gray-300 transition-all hover:scale-105">
            <Table size={13} />
            <span>{response.result_count} {response.result_count === 1 ? 'result' : 'results'}</span>
          </span>
          <span className="inline-flex items-center gap-2 px-3.5 py-1.5 bg-white border border-gray-200 rounded-full text-xs font-medium text-gray-700 shadow-sm hover:bg-gray-50 hover:border-gray-300 transition-all hover:scale-105">
            <Clock size={13} />
            <span>{(response.execution_time_ms / 1000).toFixed(2)}s</span>
          </span>
          {/* Visualization status badge */}
          {response.visualization?.status && response.visualization.status !== 'ready' && (
            <span className={`inline-flex items-center gap-2 px-3.5 py-1.5 rounded-full text-xs font-medium shadow-sm transition-all ${
              response.visualization.status === 'pending' 
                ? 'bg-amber-50 border border-amber-200 text-amber-700'
                : response.visualization.status === 'not_applicable'
                ? 'bg-gray-50 border border-gray-200 text-gray-600'
                : 'bg-red-50 border border-red-200 text-red-700'
            }`}>
              {response.visualization.status === 'pending' && <Loader2 size={13} className="animate-spin" />}
              {response.visualization.status === 'not_applicable' && <AlertCircle size={13} />}
              {response.visualization.status === 'error' && <AlertCircle size={13} />}
              <span className="capitalize">{response.visualization.status.replace(/_/g, ' ')}</span>
            </span>
          )}
        </div>
      </div>

      {/* SQL Panel (collapsible) */}
      {showSQL && (
        <div className="px-6 py-4 bg-gradient-to-br from-gray-900 via-gray-800 to-gray-900 border-b border-gray-700">
          <pre className="text-xs text-gray-200 overflow-x-auto whitespace-pre-wrap font-mono leading-relaxed">
            <code className="text-primary-300">{response.sql}</code>
          </pre>
        </div>
      )}

      {/* Content */}
      {expanded && (
        <div className="p-6">
          {/* Visualization Status Messages */}
          {vizError && (
            <div className="mb-4 flex items-start gap-3 p-4 bg-gradient-to-r from-red-50 to-red-50/80 border border-red-200/60 rounded-xl shadow-sm animate-in fade-in slide-in-from-top-2">
              <div className="flex-shrink-0 mt-0.5">
                <AlertCircle size={18} className="text-red-600" />
              </div>
              <div className="flex-1">
                <p className="text-sm font-semibold text-red-900">Visualization Unavailable</p>
                <p className="text-xs text-red-700 mt-1">{vizError}</p>
              </div>
            </div>
          )}
          
          {/* Success indicator when visualization loads */}
          {vizLoaded && response.visualization?.chart_js_config && (
            <div className="mb-4 flex items-center gap-3 px-4 py-3 bg-gradient-to-r from-green-50 via-emerald-50 to-green-50 border border-green-200/60 rounded-xl shadow-md animate-in fade-in slide-in-from-top-2">
              <div className="flex-shrink-0">
                <CheckCircle2 size={18} className="text-green-600 animate-in zoom-in duration-300" />
              </div>
              <div className="flex-1">
                <p className="text-sm font-semibold text-green-900">Visualization loaded successfully!</p>
                <p className="text-xs text-green-700 mt-0.5">Your chart is ready to view</p>
              </div>
            </div>
          )}
          
          {/* Check if single metric first */}
          {isSingleMetric(response.results, response.columns) ? (
            renderMetrics()
          ) : response.visualization.type === VisualizationType.TABLE ? (
            renderTable()
          ) : chartData && response.results.length > 0 ? (
            <>
              {/* Show chart when available */}
              <div className={`mb-6 rounded-xl border border-gray-200 bg-white p-4 shadow-sm hover:shadow-md transition-all duration-500 ${
                vizLoaded ? 'animate-in fade-in slide-in-from-bottom-4' : ''
              }`}>
                <div className="h-80">
                  {renderChart()}
                </div>
              </div>
              {/* Always show table below chart when results exist */}
              <div className="mt-6">
                <div className="mb-4 flex items-center gap-2.5 pb-2 border-b border-gray-200">
                  <div className="p-1.5 bg-gray-100 rounded-lg">
                    <Table size={16} className="text-gray-600" />
                  </div>
                  <h4 className="text-sm font-bold text-gray-800">Data Table</h4>
                </div>
                {renderTable()}
              </div>
            </>
          ) : response.results.length > 0 ? (
            renderTable()
          ) : (
            <div className="text-center py-8 text-gray-500">
              <Database className="mx-auto mb-2 text-gray-400" size={32} />
              <p>No results found</p>
            </div>
          )}

          {/* Key Insights */}
          {renderKeyInsights()}
        </div>
      )}
    </div>
  );
}

