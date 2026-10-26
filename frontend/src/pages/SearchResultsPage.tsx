import { Clock, Hash, Loader2, MessageSquareQuote } from 'lucide-react';
import { useEffect, useState } from 'react';
import { Link, useSearchParams } from 'react-router-dom';
import { searchTranscripts } from '../api';
import { Header } from '../components/Header';
import { HighlightedText } from '../components/HighlightedText';
import type { SearchResult } from '../types';

function formatDate(dateStr: string | null): string {
  if (!dateStr) return '';
  return new Date(dateStr).toLocaleDateString('en-GB', {
    day: 'numeric',
    month: 'short',
    year: 'numeric',
  });
}

function formatTimestamp(seconds: number): string {
  const h = Math.floor(seconds / 3600);
  const m = Math.floor((seconds % 3600) / 60);
  const s = Math.floor(seconds % 60);
  if (h > 0) return `${h}:${m.toString().padStart(2, '0')}:${s.toString().padStart(2, '0')}`;
  return `${m}:${s.toString().padStart(2, '0')}`;
}

export function SearchResultsPage() {
  const [searchParams] = useSearchParams();
  const query = searchParams.get('q') || '';
  const [results, setResults] = useState<SearchResult[]>([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!query.trim()) {
      setResults([]);
      setTotal(0);
      return;
    }

    setLoading(true);
    setError(null);
    searchTranscripts(query)
      .then((data) => {
        setResults(data.results);
        setTotal(data.total);
      })
      .catch((err) => setError(err.message))
      .finally(() => setLoading(false));
  }, [query]);

  return (
    <div className="min-h-screen bg-stone-50">
      <Header query={query} />

      <main className="max-w-4xl mx-auto px-4 py-6">
        {loading ? (
          <div className="text-center py-20">
            <Loader2 className="w-6 h-6 text-gray-400 mx-auto mb-3 animate-spin" />
            <p className="text-sm text-gray-400">Searching...</p>
          </div>
        ) : error ? (
          <div className="text-center py-20">
            <p className="text-red-500 text-sm">{error}</p>
            <p className="text-sm text-gray-400 mt-1">Try again later.</p>
          </div>
        ) : (
          <>
            <p className="text-sm text-gray-500 mb-6">
              {total} result{total !== 1 ? 's' : ''} for{' '}
              <span className="font-medium text-gray-700">"{query}"</span>
            </p>

            {results.length === 0 ? (
              <div className="text-center py-20">
                <MessageSquareQuote className="w-10 h-10 text-gray-300 mx-auto mb-4" />
                <p className="text-gray-500">No results found.</p>
                <p className="text-sm text-gray-400 mt-1">
                  Try different keywords or a broader search.
                </p>
              </div>
            ) : (
              <div className="space-y-3">
                {results.map((result) => (
                  <Link
                    key={`${result.episode_id}-${result.segment_id}`}
                    to={`/episode/${result.episode_id}?t=${result.start_time}`}
                    className="block bg-white rounded-xl border border-gray-100 px-5 py-4 hover:border-gray-200 hover:shadow-sm transition-all no-underline"
                  >
                    <div className="flex items-center gap-2 text-xs text-gray-400 mb-2">
                      {result.episode_number != null && (
                        <span className="inline-flex items-center gap-1 font-medium text-gray-500">
                          <Hash className="w-3 h-3" />
                          {result.episode_number}
                        </span>
                      )}
                      <span className="text-gray-300">-</span>
                      <span className="text-gray-500">{result.episode_title}</span>
                      {result.published_at && (
                        <>
                          <span className="text-gray-300">-</span>
                          <span>{formatDate(result.published_at)}</span>
                        </>
                      )}
                    </div>

                    <p className="text-sm text-gray-700 leading-relaxed mb-2">
                      <HighlightedText text={result.text} query={query} />
                    </p>

                    <span className="inline-flex items-center gap-1 text-xs font-mono text-gray-400">
                      <Clock className="w-3 h-3" />
                      {formatTimestamp(result.start_time)}
                    </span>
                  </Link>
                ))}
              </div>
            )}
          </>
        )}
      </main>
    </div>
  );
}
