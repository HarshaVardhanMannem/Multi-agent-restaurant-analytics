'use client';

import { useState, KeyboardEvent } from 'react';
import { Search, Send, Loader2, Sparkles } from 'lucide-react';
import { ExampleQuery } from '@/types/api';

interface QueryInputProps {
  onSubmit: (query: string) => void;
  isLoading: boolean;
  examples?: ExampleQuery[];
}

export default function QueryInput({ onSubmit, isLoading, examples = [] }: QueryInputProps) {
  const [query, setQuery] = useState('');
  const [isFocused, setIsFocused] = useState(false);

  const handleSubmit = () => {
    if (query.trim() && !isLoading) {
      onSubmit(query.trim());
      setQuery('');
    }
  };

  const handleKeyDown = (e: KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSubmit();
    }
  };

  const handleExampleClick = (exampleQuery: string) => {
    setQuery(exampleQuery);
  };

  return (
    <div className="w-full space-y-4">
      <div className="relative">
        <div className={`
          flex items-center gap-3 bg-white rounded-2xl border-2 transition-all duration-300
          ${isFocused 
            ? 'border-primary-500 ring-4 ring-primary-100/50 shadow-glow' 
            : 'border-gray-200 hover:border-primary-300 shadow-soft hover:shadow-medium'
          }
        `}>
          <div className="ml-4 flex-shrink-0">
            {isLoading ? (
              <Loader2 className="text-primary-500 animate-spin" size={20} />
            ) : (
              <Search className={`transition-colors ${isFocused ? 'text-primary-500' : 'text-gray-400'}`} size={20} />
            )}
          </div>
          <textarea
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            onKeyDown={handleKeyDown}
            onFocus={() => setIsFocused(true)}
            onBlur={() => setIsFocused(false)}
            placeholder="Ask about your restaurant data... (e.g., 'Show me sales by location' or 'What are my top products?')"
            className="flex-1 py-4 px-2 resize-none border-0 focus:outline-none focus:ring-0 text-gray-900 placeholder-gray-400 min-h-[56px] max-h-[120px] text-base"
            rows={1}
            disabled={isLoading}
          />
          <button
            onClick={handleSubmit}
            disabled={isLoading || !query.trim()}
            className={`
              mr-3 p-3 rounded-xl transition-all duration-300 flex-shrink-0
              ${query.trim() && !isLoading
                ? 'bg-gradient-to-r from-primary-500 via-primary-600 to-primary-500 text-white shadow-md hover:shadow-glow hover:scale-110 active:scale-95 bg-[length:200%_100%] hover:bg-[position:100%_0]'
                : 'bg-gray-100 text-gray-400 cursor-not-allowed'
              }
            `}
            aria-label="Submit query"
          >
            {isLoading ? (
              <Loader2 className="animate-spin" size={20} />
            ) : (
              <Send size={20} />
            )}
          </button>
        </div>
        
        {/* Helper text */}
        <p className="absolute -bottom-6 left-0 text-xs text-gray-400">
          Press Enter to submit, Shift+Enter for new line
        </p>
      </div>

      {examples.length > 0 && (
        <div className="flex items-center gap-2 text-sm text-gray-600 pt-4">
          <Sparkles className="text-amber-500 flex-shrink-0" size={14} />
          <span className="text-gray-500">Try:</span>
          <div className="flex flex-wrap gap-2">
            {examples.slice(0, 3).map((example, idx) => (
              <button
                key={idx}
                onClick={() => handleExampleClick(example.query)}
                className="px-4 py-2 bg-white hover:bg-gradient-to-r hover:from-primary-50 hover:to-primary-100 hover:text-primary-700 border border-gray-200 hover:border-primary-300 rounded-full text-gray-700 transition-all text-xs font-semibold shadow-sm hover:shadow-md hover:scale-105"
              >
                {example.query.length > 40 ? example.query.slice(0, 40) + '...' : example.query}
              </button>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}



