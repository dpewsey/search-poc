import { Hash, Loader2, Mic } from 'lucide-react';
import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { getEpisodes } from '../api';
import { Header } from '../components/Header';
import type { EpisodeSummary } from '../types';

function formatDate(dateStr: string | null): string {
  if (!dateStr) return '';
  return new Date(dateStr).toLocaleDateString('en-GB', {
    day: 'numeric',
    month: 'short',
    year: 'numeric',
  });
}

export function EpisodesPage() {
  const [episodes, setEpisodes] = useState<EpisodeSummary[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    getEpisodes()
      .then(setEpisodes)
      .catch((err) => setError(err.message))
      .finally(() => setLoading(false));
  }, []);

  return (
    <div className="min-h-screen bg-stone-50">
      <Header />

      <main className="max-w-4xl mx-auto px-4 py-8">
        <h1 className="text-xl font-bold text-gray-900 mb-6">Episodes</h1>

        {loading ? (
          <div className="text-center py-20">
            <Loader2 className="w-6 h-6 text-gray-400 mx-auto animate-spin" />
          </div>
        ) : error ? (
          <div className="text-center py-20">
            <p className="text-red-500 text-sm">{error}</p>
          </div>
        ) : episodes.length === 0 ? (
          <div className="text-center py-20">
            <Mic className="w-10 h-10 text-gray-300 mx-auto mb-4" />
            <p className="text-gray-500">No episodes yet.</p>
            <p className="text-sm text-gray-400 mt-1">
              Episodes will appear here once transcribed.
            </p>
          </div>
        ) : (
          <div className="space-y-3">
            {episodes.map((ep) => (
              <Link
                key={ep.id}
                to={`/episode/${ep.id}`}
                className="block bg-white rounded-xl border border-gray-100 px-5 py-4 hover:border-gray-200 hover:shadow-sm transition-all no-underline"
              >
                <div className="flex items-center gap-3 text-xs text-gray-400 mb-1.5">
                  {ep.episode_number != null && (
                    <span className="inline-flex items-center gap-1">
                      <Hash className="w-3 h-3" />
                      {ep.episode_number}
                    </span>
                  )}
                  {ep.published_at && <span>{formatDate(ep.published_at)}</span>}
                </div>
                <h2 className="text-sm font-medium text-gray-900">
                  {ep.title}
                </h2>
                {ep.description && (
                  <p className="text-sm text-gray-500 mt-1 line-clamp-2">
                    {ep.description}
                  </p>
                )}
              </Link>
            ))}
          </div>
        )}
      </main>
    </div>
  );
}
