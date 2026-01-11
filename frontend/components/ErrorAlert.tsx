'use client';

import { ErrorResponse } from '@/types/api';
import { AlertCircle, X } from 'lucide-react';

interface ErrorAlertProps {
  error: ErrorResponse;
  onClose: () => void;
}

export default function ErrorAlert({ error, onClose }: ErrorAlertProps) {
  return (
    <div className="bg-gradient-to-r from-red-50 via-red-50/80 to-red-50 border border-red-200/60 rounded-xl p-5 mb-4 shadow-md animate-in fade-in slide-in-from-top-2">
      <div className="flex items-start justify-between gap-4">
        <div className="flex items-start gap-3 flex-1">
          <div className="flex-shrink-0 mt-0.5">
            <div className="p-2 bg-red-100 rounded-lg">
              <AlertCircle className="text-red-600" size={20} />
            </div>
          </div>
          <div className="flex-1 min-w-0">
            <h4 className="text-base font-bold text-red-900 mb-2">
              {error.error_message}
            </h4>
            {/* Hide technical error details from restaurant managers */}
            {process.env.NODE_ENV === 'development' && error.details?.original_error && (
              <p className="text-xs text-red-600 mb-3 font-mono bg-red-50 px-2 py-1 rounded border border-red-200">
                {error.details.original_error}
              </p>
            )}
            {error.suggestions && error.suggestions.length > 0 && (
              <div className="mt-3">
                <p className="text-sm font-semibold text-red-800 mb-2">Suggestions:</p>
                <ul className="space-y-2">
                  {error.suggestions.map((suggestion, idx) => (
                    <li key={idx} className="flex items-start gap-2 text-sm text-red-700">
                      <span className="text-red-500 font-bold mt-1">•</span>
                      <span>{suggestion}</span>
                    </li>
                  ))}
                </ul>
              </div>
            )}
          </div>
        </div>
        <button
          onClick={onClose}
          className="flex-shrink-0 p-1.5 text-red-400 hover:text-red-600 hover:bg-red-100 rounded-lg transition-all duration-200"
          aria-label="Close error"
        >
          <X size={18} />
        </button>
      </div>
    </div>
  );
}




