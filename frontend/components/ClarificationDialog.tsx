'use client';

import { useState } from 'react';
import { ClarificationResponse } from '@/types/api';
import { AlertCircle, X, MessageSquare } from 'lucide-react';

interface ClarificationDialogProps {
  clarification: ClarificationResponse;
  onClose: () => void;
  onConfirm: (clarificationText: string, originalQuery: string) => void;
}

export default function ClarificationDialog({
  clarification,
  onClose,
  onConfirm,
}: ClarificationDialogProps) {
  const [inputValue, setInputValue] = useState('');

  const handleSubmit = () => {
    if (inputValue.trim()) {
      onConfirm(inputValue.trim(), clarification.original_query);
    }
  };

  const handleSuggestionClick = (suggestion: string) => {
    onConfirm(suggestion, clarification.original_query);
  };

  const handleKeyPress = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && (e.ctrlKey || e.metaKey)) {
      handleSubmit();
    }
  };

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4">
      <div className="bg-white rounded-2xl shadow-xl max-w-lg w-full overflow-hidden">
        {/* Header */}
        <div className="px-6 py-4 bg-gradient-to-r from-amber-500 to-orange-500">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              <AlertCircle className="text-white" size={24} />
              <h3 className="text-lg font-semibold text-white">
                Clarification Needed
              </h3>
            </div>
            <button
              onClick={onClose}
              className="text-white/80 hover:text-white transition-colors p-1 hover:bg-white/10 rounded-lg"
            >
              <X size={20} />
            </button>
          </div>
        </div>

        <div className="p-6">
          {/* Original Query Reference */}
          <div className="mb-4 p-3 bg-gray-50 rounded-lg border border-gray-200">
            <div className="flex items-center gap-2 text-xs text-gray-500 mb-1">
              <MessageSquare size={12} />
              <span>Your original question:</span>
            </div>
            <p className="text-sm text-gray-700 italic">"{clarification.original_query}"</p>
          </div>

          {/* Clarification Question */}
          <p className="text-gray-800 mb-4 font-medium">{clarification.question}</p>

          {/* Suggestions */}
          {clarification.suggestions.length > 0 && (
            <div className="mb-4">
              <p className="text-sm font-medium text-gray-600 mb-2">Quick options:</p>
              <div className="space-y-2">
                {clarification.suggestions.map((suggestion, idx) => (
                  <button
                    key={idx}
                    onClick={() => handleSuggestionClick(suggestion)}
                    className="w-full text-left px-4 py-2.5 bg-gray-50 hover:bg-primary-50 hover:border-primary-300 border border-gray-200 rounded-lg transition-all text-sm text-gray-700 hover:text-primary-700"
                  >
                    {suggestion}
                  </button>
                ))}
              </div>
            </div>
          )}

          {/* Custom Input */}
          <div className="mb-4">
            <label className="block text-sm font-medium text-gray-600 mb-2">
              Or provide more details:
            </label>
            <textarea
              value={inputValue}
              onChange={(e) => setInputValue(e.target.value)}
              onKeyDown={handleKeyPress}
              placeholder="E.g., I meant last week's sales, or I want to see data for Manhattan location..."
              className="w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-primary-500 resize-none text-gray-900 bg-white placeholder-gray-400"
              rows={3}
              autoFocus
            />
            <p className="text-xs text-gray-400 mt-1">Press Ctrl+Enter to submit</p>
          </div>

          {/* Action Buttons */}
          <div className="flex gap-3">
            <button
              onClick={onClose}
              className="flex-1 px-4 py-2.5 border border-gray-300 text-gray-700 rounded-lg hover:bg-gray-50 transition-colors font-medium"
            >
              Cancel
            </button>
            <button
              onClick={handleSubmit}
              disabled={!inputValue.trim()}
              className="flex-1 px-4 py-2.5 bg-gradient-to-r from-primary-500 to-primary-600 text-white rounded-lg hover:from-primary-600 hover:to-primary-700 disabled:from-gray-300 disabled:to-gray-300 disabled:cursor-not-allowed transition-all font-medium shadow-sm"
            >
              Submit Clarification
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}

