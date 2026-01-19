'use client';

import { useEffect, useState } from 'react';
import { useRouter, useParams } from 'next/navigation';
import { useAuth } from '@/lib/auth-context';
import {
    fetchDashboard,
    addWidget,
    deleteWidget,
    updateWidget,
    getQueryHistoryWithResults,
    DashboardDetail,
    Widget,
    QueryHistoryDetail,
} from '@/lib/api';
import { ArrowLeft, Plus, Trash2, LayoutDashboard, Sparkles, TrendingUp, CheckCircle } from 'lucide-react';
import ChartWidget from '@/components/ChartWidget';
import { QueryResponse, VisualizationType, QueryIntent } from '@/types/api';

export default function DashboardDetailPage() {
    const router = useRouter();
    const params = useParams();
    const dashboardId = params?.id as string;
    const { user, isLoading: authLoading } = useAuth();

    const [dashboard, setDashboard] = useState<DashboardDetail | null>(null);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);
    const [showWidgetSelector, setShowWidgetSelector] = useState(false);
    const [queryHistory, setQueryHistory] = useState<QueryHistoryDetail[]>([]);
    const [addingWidget, setAddingWidget] = useState(false);

    useEffect(() => {
        if (!authLoading && !user) {
            router.push('/');
        }
    }, [user, authLoading, router]);

    useEffect(() => {
        if (user && dashboardId) {
            loadDashboard();
        }
    }, [user, dashboardId]);

    const loadDashboard = async () => {
        try {
            setLoading(true);
            setError(null);
            const data = await fetchDashboard(dashboardId);
            setDashboard(data);
        } catch (err: any) {
            console.error('Error loading dashboard:', err);
            setError(err.response?.data?.detail || err.message || 'Failed to load dashboard');
        } finally {
            setLoading(false);
        }
    };

    const loadQueryHistory = async () => {
        try {
            const history = await getQueryHistoryWithResults(50);
            setQueryHistory(history);
        } catch (err) {
            console.error('Error loading query history:', err);
        }
    };

    const handleAddWidget = async (queryId: string) => {
        if (!dashboard) return;

        try {
            setAddingWidget(true);
            setError(null);

            // Calculate next position
            const nextPosition = dashboard.widgets.length;

            await addWidget(dashboardId, {
                query_id: queryId,
                position: nextPosition,
                size: 'medium'
            });

            // Reload dashboard to get updated widgets
            await loadDashboard();
            setShowWidgetSelector(false);
        } catch (err: any) {
            console.error('Error adding widget:', err);
            setError(err.response?.data?.detail || err.message || 'Failed to add widget');
        } finally {
            setAddingWidget(false);
        }
    };

    const handleRemoveWidget = async (widgetId: string) => {
        if (!dashboard) return;

        if (!confirm('Remove this widget from the dashboard?')) {
            return;
        }

        try {
            await deleteWidget(dashboardId, widgetId);
            // Reload dashboard to get updated widgets
            await loadDashboard();
        } catch (err: any) {
            console.error('Error removing widget:', err);
            setError(err.response?.data?.detail || err.message || 'Failed to remove widget');
        }
    };

    const handleSizeChange = async (widgetId: string, newSize: string) => {
        if (!dashboard) return;

        try {
            await updateWidget(dashboardId, widgetId, { size: newSize });
            // Update local state
            setDashboard({
                ...dashboard,
                widgets: dashboard.widgets.map(w =>
                    w.id === widgetId ? { ...w, size: newSize } : w
                )
            });
        } catch (err: any) {
            console.error('Error updating widget size:', err);
            setError(err.response?.data?.detail || err.message || 'Failed to update widget');
        }
    };

    if (authLoading || loading) {
        return (
            <div className="min-h-screen bg-gradient-to-br from-gray-50 via-primary-50/20 to-gray-100 flex items-center justify-center">
                <div className="text-center">
                    <div className="inline-flex items-center justify-center w-16 h-16 bg-gradient-to-br from-primary-500 to-primary-600 rounded-2xl mb-4 shadow-lg">
                        <LayoutDashboard className="text-white animate-pulse" size={32} />
                    </div>
                    <p className="text-gray-700 text-lg font-medium">Loading dashboard...</p>
                </div>
            </div>
        );
    }

    if (error || !dashboard) {
        return (
            <div className="min-h-screen bg-gradient-to-br from-gray-50 via-primary-50/20 to-gray-100">
                <header className="bg-white/80 backdrop-blur-md border-b border-gray-200/50 shadow-soft sticky top-0 z-50">
                    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-4">
                        <button
                            onClick={() => router.push('/dashboards')}
                            className="flex items-center gap-2 text-gray-600 hover:text-gray-900 transition-colors font-medium"
                        >
                            <ArrowLeft size={20} />
                            Back to Dashboards
                        </button>
                    </div>
                </header>
                <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
                    <div className="bg-red-50 border border-red-200 text-red-700 px-6 py-4 rounded-xl shadow-sm">
                        {error || 'Dashboard not found'}
                    </div>
                </div>
            </div>
        );
    }

    // Convert widgets to ChartWidget format
    const convertedWidgets = dashboard.widgets
        .filter(w => w.query_data) // Only show widgets with valid query data
        .map((widget) => {
            const qd = widget.query_data!;
            return {
                id: widget.id,
                query: qd.natural_query,
                response: {
                    success: true,
                    query_id: qd.query_id,
                    intent: qd.intent as QueryIntent,
                    sql: qd.generated_sql,
                    explanation: '',
                    answer: qd.answer,
                    results: qd.results_sample,
                    result_count: qd.result_count,
                    columns: qd.columns,
                    visualization: {
                        type: qd.visualization_type as VisualizationType,
                        config: qd.visualization_config,
                        chart_js_config: qd.visualization_config?.chart_js_config,
                    },
                    execution_time_ms: qd.execution_time_ms,
                    total_processing_time_ms: qd.execution_time_ms,
                } as QueryResponse,
                createdAt: new Date(widget.created_at),
                size: widget.size,
                dashboardWidgetId: widget.id,
            };
        });

    return (
        <div className="min-h-screen bg-gradient-to-br from-gray-50 via-primary-50/20 to-gray-100">
            {/* Header */}
            <header className="bg-white/80 backdrop-blur-md border-b border-gray-200/50 shadow-soft sticky top-0 z-50">
                <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-4">
                    <div className="flex items-center justify-between">
                        <button
                            onClick={() => router.push('/dashboards')}
                            className="flex items-center gap-2 text-gray-600 hover:text-gray-900 transition-colors font-medium"
                        >
                            <ArrowLeft size={20} />
                            Back to Dashboards
                        </button>

                        <button
                            onClick={() => {
                                setShowWidgetSelector(true);
                                loadQueryHistory();
                            }}
                            disabled={dashboard.widgets.length >= 12}
                            className="flex items-center gap-2 px-5 py-2.5 bg-gradient-to-r from-primary-500 to-primary-600 text-white rounded-xl hover:from-primary-600 hover:to-primary-700 transition-all shadow-lg hover:shadow-xl disabled:opacity-50 disabled:cursor-not-allowed font-semibold"
                        >
                            <Plus size={18} />
                            Add Widget {dashboard.widgets.length >= 12 && '(Max 12)'}
                        </button>
                    </div>
                </div>
            </header>

            <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
                {/* Dashboard Header */}
                <div className="mb-8">
                    <div className="bg-white/90 backdrop-blur-sm rounded-2xl shadow-soft border border-gray-100 p-8 hover:shadow-medium transition-shadow">
                        <div className="flex items-center justify-between">
                            <div className="flex items-center gap-4">
                                <div className="p-3 bg-gradient-to-br from-primary-500 via-primary-600 to-primary-700 rounded-xl shadow-lg">
                                    <LayoutDashboard size={28} className="text-white" />
                                </div>
                                <div>
                                    <h1 className="text-3xl font-bold gradient-text mb-1">{dashboard.name}</h1>
                                    {dashboard.description && (
                                        <p className="text-gray-600">{dashboard.description}</p>
                                    )}
                                </div>
                            </div>

                            <div className="flex items-center gap-4">
                                <div className="text-right">
                                    <div className="text-3xl font-bold gradient-text">{dashboard.widgets.length}</div>
                                    <div className="text-sm text-gray-500 font-medium">Widgets</div>
                                </div>
                            </div>
                        </div>
                    </div>
                </div>

                {/* Error Message */}
                {error && (
                    <div className="mb-6 bg-red-50 border border-red-200 text-red-700 px-5 py-4 rounded-xl shadow-sm">
                        {error}
                    </div>
                )}

                {/* Widgets Grid */}
                {convertedWidgets.length === 0 ? (
                    <div className="bg-white/90 backdrop-blur-sm rounded-2xl shadow-soft border border-gray-100 p-16 text-center">
                        <div className="inline-flex items-center justify-center w-20 h-20 bg-gradient-to-br from-primary-100 to-primary-200 rounded-2xl mb-6">
                            <Sparkles size={40} className="text-primary-600" />
                        </div>
                        <h3 className="text-2xl font-bold text-gray-900 mb-3">Ready to build your dashboard</h3>
                        <p className="text-gray-500 mb-8 max-w-md mx-auto">
                            Add your first widget from your query history to start visualizing your data
                        </p>
                        <button
                            onClick={() => {
                                setShowWidgetSelector(true);
                                loadQueryHistory();
                            }}
                            className="inline-flex items-center gap-2 px-6 py-3 bg-gradient-to-r from-primary-500 to-primary-600 text-white rounded-xl hover:from-primary-600 hover:to-primary-700 transition-all shadow-lg hover:shadow-xl font-semibold"
                        >
                            <Plus size={20} />
                            Add Your First Widget
                        </button>
                    </div>
                ) : (
                    <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                        {convertedWidgets.map((widget) => (
                            <div
                                key={widget.dashboardWidgetId}
                                className={`${widget.size === 'full' ? 'lg:col-span-2' : ''
                                    } ${widget.size === 'large' ? 'lg:col-span-2' : ''
                                    }`}
                            >
                                <div className="relative group">
                                    {/* Size Controls - Floating on hover */}
                                    <div className="absolute top-4 right-4 z-10 opacity-0 group-hover:opacity-100 transition-all duration-200">
                                        <div className="flex gap-2 bg-white/95 backdrop-blur-sm rounded-xl p-2 shadow-lg border border-gray-200">
                                            <select
                                                value={widget.size}
                                                onChange={(e) => handleSizeChange(widget.dashboardWidgetId!, e.target.value)}
                                                className="text-xs px-3 py-1.5 bg-gradient-to-r from-primary-50 to-primary-100 text-primary-700 border border-primary-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-primary-500 font-medium cursor-pointer transition-all hover:from-primary-100 hover:to-primary-200"
                                            >
                                                <option value="small">Small</option>
                                                <option value="medium">Medium</option>
                                                <option value="large">Large</option>
                                                <option value="full">Full Width</option>
                                            </select>
                                            {/* Remove Widget Button */}
                                            <button
                                                onClick={() => handleRemoveWidget(widget.dashboardWidgetId!)}
                                                className="p-2 bg-red-50 text-red-600 hover:bg-red-100 rounded-lg transition-all hover:scale-110 border border-red-200"
                                                title="Remove widget"
                                            >
                                                <Trash2 size={14} />
                                            </button>
                                        </div>
                                    </div>

                                    <ChartWidget
                                        widget={widget}
                                        onRemove={() => handleRemoveWidget(widget.dashboardWidgetId!)}
                                        onUpdate={() => { }}
                                    />
                                </div>
                            </div>
                        ))}
                    </div>
                )}
            </div>

            {/* Widget Selector Modal */}
            {showWidgetSelector && (
                <div className="fixed inset-0 bg-black/40 backdrop-blur-sm flex items-center justify-center p-4 z-50 animate-fade-in">
                    <div className="bg-white rounded-2xl p-8 max-w-4xl w-full max-h-[85vh] overflow-hidden flex flex-col shadow-2xl border border-gray-100">
                        {/* Modal Header */}
                        <div className="mb-6">
                            <div className="flex items-center gap-3 mb-2">
                                <div className="p-2 bg-gradient-to-br from-primary-500 to-primary-600 rounded-xl shadow-md">
                                    <TrendingUp className="text-white" size={24} />
                                </div>
                                <h2 className="text-2xl font-bold gradient-text">Add Widget from Query History</h2>
                            </div>
                            <p className="text-gray-500 ml-11">Select a saved query to add as a widget to your dashboard</p>
                        </div>

                        {/* Query History List */}
                        <div className="flex-1 overflow-y-auto mb-6 -mx-2 px-2">
                            {queryHistory.length === 0 ? (
                                <div className="text-center py-12">
                                    <div className="inline-flex items-center justify-center w-16 h-16 bg-gradient-to-br from-primary-100 to-primary-200 rounded-2xl mb-4">
                                        <Sparkles className="text-primary-600" size={32} />
                                    </div>
                                    <p className="text-gray-500 font-medium">No query history available</p>
                                    <p className="text-sm text-gray-400 mt-1">Run some queries first to add them as widgets!</p>
                                </div>
                            ) : (
                                <div className="space-y-3">
                                    {queryHistory.map((query) => {
                                        const isAdded = dashboard.widgets.some(w => w.query_id === query.query_id);
                                        return (
                                            <button
                                                key={query.query_id}
                                                onClick={() => !isAdded && handleAddWidget(query.query_id)}
                                                disabled={addingWidget || isAdded}
                                                className={`w-full text-left p-5 rounded-xl transition-all border ${isAdded
                                                    ? 'bg-green-50 border-green-200 cursor-not-allowed'
                                                    : 'bg-white border-gray-200 hover:border-primary-300 hover:shadow-lg hover:scale-[1.01] cursor-pointer'
                                                    }`}
                                            >
                                                <div className="flex items-start justify-between gap-4">
                                                    <div className="flex-1 min-w-0">
                                                        <p className={`font-semibold mb-2 line-clamp-2 ${isAdded ? 'text-green-700' : 'text-gray-900'
                                                            }`}>
                                                            {query.natural_query}
                                                        </p>
                                                        <div className="flex items-center gap-3 text-xs">
                                                            <span className={`px-2.5 py-1 rounded-full font-medium ${isAdded
                                                                ? 'bg-green-100 text-green-700'
                                                                : 'bg-primary-100 text-primary-700'
                                                                }`}>
                                                                {query.intent}
                                                            </span>
                                                            <span className="text-gray-500">{query.result_count} results</span>
                                                            <span className="text-gray-400">•</span>
                                                            <span className="text-gray-500">{new Date(query.created_at).toLocaleDateString()}</span>
                                                        </div>
                                                    </div>
                                                    {isAdded && (
                                                        <div className="flex items-center gap-2 text-green-600 flex-shrink-0">
                                                            <CheckCircle size={20} />
                                                            <span className="text-sm font-semibold">Added</span>
                                                        </div>
                                                    )}
                                                </div>
                                            </button>
                                        );
                                    })}
                                </div>
                            )}
                        </div>

                        {/* Modal Footer */}
                        <button
                            onClick={() => setShowWidgetSelector(false)}
                            disabled={addingWidget}
                            className="w-full px-5 py-3 bg-gray-100 text-gray-700 rounded-xl hover:bg-gray-200 transition-colors font-semibold disabled:opacity-50"
                        >
                            Close
                        </button>
                    </div>
                </div>
            )}
        </div>
    );
}
