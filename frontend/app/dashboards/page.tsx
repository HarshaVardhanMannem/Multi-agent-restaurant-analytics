'use client';

import { useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';
import { useAuth } from '@/lib/auth-context';
import {
    fetchDashboards,
    createDashboard,
    deleteDashboard,
    Dashboard,
} from '@/lib/api';
import { LayoutDashboard, Plus, Eye, Trash2, ArrowLeft } from 'lucide-react';

export default function DashboardsPage() {
    const router = useRouter();
    const { user, isLoading: authLoading } = useAuth();

    const [dashboards, setDashboards] = useState<Dashboard[]>([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);
    const [showCreateModal, setShowCreateModal] = useState(false);
    const [newDashboard, setNewDashboard] = useState({ name: '', description: '' });
    const [creating, setCreating] = useState(false);

    useEffect(() => {
        if (!authLoading && !user) {
            router.push('/');
        }
    }, [user, authLoading, router]);

    useEffect(() => {
        if (user) {
            loadDashboards();
        }
    }, [user]);

    const loadDashboards = async () => {
        try {
            setLoading(true);
            setError(null);
            const data = await fetchDashboards();
            setDashboards(data);
        } catch (err: any) {
            console.error('Error loading dashboards:', err);
            setError(err.response?.data?.detail || err.message || 'Failed to load dashboards');
        } finally {
            setLoading(false);
        }
    };

    const handleCreateDashboard = async () => {
        if (!newDashboard.name.trim()) {
            return;
        }

        try {
            setCreating(true);
            setError(null);
            const created = await createDashboard({
                name: newDashboard.name.trim(),
                description: newDashboard.description.trim() || undefined,
            });

            // Navigate to the new dashboard detail page
            router.push(`/dashboards/${created.id}`);
        } catch (err: any) {
            console.error('Error creating dashboard:', err);
            setError(err.response?.data?.detail || err.message || 'Failed to create dashboard');
        } finally {
            setCreating(false);
        }
    };

    const handleDeleteDashboard = async (id: string, name: string) => {
        if (!confirm(`Are you sure you want to delete "${name}"?`)) {
            return;
        }

        try {
            await deleteDashboard(id);
            // Reload dashboards
            await loadDashboards();
        } catch (err: any) {
            console.error('Error deleting dashboard:', err);
            setError(err.response?.data?.detail || err.message || 'Failed to delete dashboard');
        }
    };

    if (authLoading || loading) {
        return (
            <div className="min-h-screen bg-gradient-to-br from-gray-50 via-primary-50/20 to-gray-100 flex items-center justify-center">
                <div className="text-gray-700 text-lg font-medium">Loading dashboards...</div>
            </div>
        );
    }

    return (
        <div className="min-h-screen bg-gray-50">
            {/* Header */}
            <header className="bg-white border-b border-gray-200 shadow-sm sticky top-0 z-50" style={{ willChange: 'transform' }}>
                <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-4">
                    <div className="flex items-center justify-between">
                        <div className="flex items-center gap-4">
                            <button
                                onClick={() => router.push('/')}
                                className="flex items-center gap-2 text-gray-600 hover:text-gray-900 transition-colors font-medium"
                            >
                                <ArrowLeft size={20} />
                                Back to Home
                            </button>
                        </div>

                        <button
                            onClick={() => setShowCreateModal(true)}
                            className="flex items-center gap-2 px-5 py-2.5 bg-gradient-to-r from-primary-500 to-primary-600 text-white rounded-xl hover:from-primary-600 hover:to-primary-700 transition-all shadow-lg hover:shadow-xl font-semibold"
                        >
                            <Plus size={18} />
                            Create Dashboard
                        </button>
                    </div>
                </div>
            </header>

            <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
                {/* Page Title */}
                <div className="mb-8">
                    <div className="flex items-center gap-3 mb-2">
                        <div className="p-2.5 bg-gradient-to-br from-primary-500 via-primary-600 to-primary-700 rounded-xl shadow-lg">
                            <LayoutDashboard className="text-white" size={24} />
                        </div>
                        <h1 className="text-3xl font-bold gradient-text">My Dashboards</h1>
                    </div>
                    <p className="text-gray-600 ml-11">Create and manage your custom analytics dashboards</p>
                </div>

                {/* Error Message */}
                {error && (
                    <div className="mb-6 bg-red-50 border border-red-200 text-red-700 px-5 py-4 rounded-xl shadow-sm">
                        {error}
                    </div>
                )}

                {/* Dashboards Grid */}
                {dashboards.length === 0 ? (
                    <div className="text-center py-20 animate-fade-in">
                        <div className="inline-flex items-center justify-center w-20 h-20 bg-gradient-to-br from-primary-100 to-primary-200 rounded-2xl mb-6 animate-float">
                            <LayoutDashboard size={40} className="text-primary-600" />
                        </div>
                        <h3 className="text-xl font-semibold text-gray-900 mb-2">No dashboards yet</h3>
                        <p className="text-gray-500 mb-6 max-w-md mx-auto">
                            Create your first dashboard to organize and visualize your analytics
                        </p>
                        <button
                            onClick={() => setShowCreateModal(true)}
                            className="px-6 py-3 bg-gradient-to-r from-primary-500 to-primary-600 text-white rounded-xl hover:from-primary-600 hover:to-primary-700 transition-all shadow-lg font-semibold"
                        >
                            Create Dashboard
                        </button>
                    </div>
                ) : (
                    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
                        {dashboards.map((dashboard, idx) => (
                            <div
                                key={dashboard.id}
                                className={`bg-white rounded-2xl shadow-md border border-gray-100 p-6 hover-lift-glow group animate-stagger-${Math.min(idx + 1, 6)}`}
                            >
                                <div className="flex items-start justify-between mb-4">
                                    <div className="p-2.5 bg-gradient-to-br from-primary-500 to-primary-600 rounded-xl shadow-md group-hover:shadow-lg transition-shadow">
                                        <LayoutDashboard size={22} className="text-white" />
                                    </div>
                                    <span className="text-sm px-3 py-1 bg-primary-100 text-primary-700 rounded-full font-semibold shadow-sm animate-pulse-glow">
                                        {dashboard.widget_count} widgets
                                    </span>
                                </div>

                                <h3 className="text-lg font-bold text-gray-900 mb-2 group-hover:text-primary-700 transition-colors">
                                    {dashboard.name}
                                </h3>

                                {dashboard.description && (
                                    <p className="text-gray-600 text-sm mb-4 line-clamp-2">
                                        {dashboard.description}
                                    </p>
                                )}

                                <div className="text-xs text-gray-500 mb-4">
                                    Updated {new Date(dashboard.updated_at).toLocaleDateString()}
                                </div>

                                <div className="flex gap-2">
                                    <button
                                        onClick={() => router.push(`/dashboards/${dashboard.id}`)}
                                        className="flex-1 flex items-center justify-center gap-2 px-4 py-2.5 bg-gradient-to-r from-primary-500 to-primary-600 text-white rounded-xl hover:from-primary-600 hover:to-primary-700 transition-all shadow-md hover:shadow-lg font-medium"
                                    >
                                        <Eye size={16} />
                                        View
                                    </button>
                                    <button
                                        onClick={() => handleDeleteDashboard(dashboard.id, dashboard.name)}
                                        className="px-4 py-2.5 bg-red-50 text-red-600 rounded-xl hover:bg-red-100 transition-colors border border-red-200 font-medium"                  >
                                        <Trash2 size={16} />
                                    </button>
                                </div>
                            </div>
                        ))}
                    </div>
                )}
            </div>

            {/* Create Dashboard Modal */}
            {showCreateModal && (
                <div className="fixed inset-0 bg-black/40 flex items-center justify-center p-4 z-50 animate-backdrop-fade">
                    <div className="bg-white rounded-2xl p-8 max-w-md w-full shadow-2xl border border-gray-100 animate-slide-up-bottom">
                        <h2 className="text-2xl font-bold text-gray-900 mb-6">Create Dashboard</h2>

                        <div className="space-y-5">
                            <div>
                                <label className="block text-sm font-medium text-gray-700 mb-2">
                                    Dashboard Name *
                                </label>
                                <input
                                    type="text"
                                    value={newDashboard.name}
                                    onChange={(e) => setNewDashboard({ ...newDashboard, name: e.target.value })}
                                    placeholder="e.g., Sales Overview"
                                    className="w-full px-4 py-3 border border-gray-300 rounded-xl focus:ring-2 focus:ring-primary-500 focus:border-primary-500 transition-colors"
                                    autoFocus
                                />
                            </div>

                            <div>
                                <label className="block text-sm font-medium text-gray-700 mb-2">
                                    Description
                                </label>
                                <textarea
                                    value={newDashboard.description}
                                    onChange={(e) => setNewDashboard({ ...newDashboard, description: e.target.value })}
                                    placeholder="Optional description"
                                    rows={3}
                                    className="w-full px-4 py-3 border border-gray-300 rounded-xl focus:ring-2 focus:ring-primary-500 focus:border-primary-500 transition-colors resize-none"
                                />
                            </div>
                        </div>

                        <div className="flex gap-3 mt-8">
                            <button
                                onClick={() => {
                                    setShowCreateModal(false);
                                    setNewDashboard({ name: '', description: '' });
                                }}
                                disabled={creating}
                                className="flex-1 px-4 py-3 bg-gray-100 text-gray-700 rounded-xl hover:bg-gray-200 transition-colors font-semibold disabled:opacity-50"
                            >
                                Cancel
                            </button>
                            <button
                                onClick={handleCreateDashboard}
                                disabled={!newDashboard.name.trim() || creating}
                                className="flex-1 px-4 py-3 bg-gradient-to-r from-primary-500 to-primary-600 text-white rounded-xl hover:from-primary-600 hover:to-primary-700 disabled:opacity-50 disabled:cursor-not-allowed transition-all shadow-lg font-semibold"
                            >
                                {creating ? 'Creating...' : 'Create'}
                            </button>
                        </div>
                    </div>
                </div>
            )}
        </div>
    );
}
