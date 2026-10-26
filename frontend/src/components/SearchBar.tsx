import { Search } from 'lucide-react';
import { useState, type FormEvent } from 'react';

interface SearchBarProps {
  initialQuery?: string;
  onSearch: (query: string) => void;
  size?: 'default' | 'large';
  autoFocus?: boolean;
}

export function SearchBar({
  initialQuery = '',
  onSearch,
  size = 'default',
  autoFocus = false,
}: SearchBarProps) {
  const [query, setQuery] = useState(initialQuery);

  function handleSubmit(e: FormEvent) {
    e.preventDefault();
    if (query.trim()) {
      onSearch(query.trim());
    }
  }

  const isLarge = size === 'large';

  return (
    <form onSubmit={handleSubmit} className="w-full">
      <div
        className={`
          flex items-center w-full bg-white border border-gray-200
          transition-shadow focus-within:shadow-md focus-within:border-gray-300
          ${isLarge ? 'rounded-2xl px-5 py-4' : 'rounded-xl px-4 py-2.5'}
        `}
      >
        <Search
          className={`text-gray-400 shrink-0 ${isLarge ? 'w-5 h-5' : 'w-4 h-4'}`}
        />
        <input
          type="text"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          placeholder="Search episodes, quotes, moments..."
          autoFocus={autoFocus}
          className={`
            flex-1 bg-transparent outline-none placeholder-gray-400 text-gray-900
            ${isLarge ? 'ml-4 text-lg' : 'ml-3 text-sm'}
          `}
        />
        <button
          type="submit"
          className={`
            shrink-0 bg-gray-900 text-white font-medium
            hover:bg-gray-800 transition-colors cursor-pointer
            ${isLarge ? 'rounded-xl px-6 py-2.5 text-sm' : 'rounded-lg px-4 py-1.5 text-sm'}
          `}
        >
          Search
        </button>
      </div>
    </form>
  );
}
