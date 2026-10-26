import { Calendar, Clock, FileText, Hash, Loader2 } from 'lucide-react';
import { useEffect, useRef, useState } from 'react';
import { useParams, useSearchParams } from 'react-router-dom';
import { getEpisode } from '../api';
import { Header } from '../components/Header';
import type { Episode } from '../types';

function formatDate(dateStr: string | null): string {
  if (!dateStr) return '';
  return new Date(dateStr).toLocaleDateString('en-GB', {
    day: 'numeric',
    month: 'long',
    year: 'numeric',
  });
}

function formatDuration(seconds: number | null): string {
  if (!seconds) return '';
  const h = Math.floor(seconds / 3600);
  const m = Math.floor((seconds % 3600) / 60);
  const s = Math.floor(seconds % 60);
  if (h > 0) return `${h}:${m.toString().padStart(2, '0')}:${s.toString().padStart(2, '0')}`;
  return `${m}:${s.toString().padStart(2, '0')}`;
}

function formatTimestamp(seconds: number): string {
  const h = Math.floor(seconds / 3600);
  const m = Math.floor((seconds % 3600) / 60);
  const s = Math.floor(seconds % 60);
  if (h > 0) return `${h}:${m.toString().padStart(2, '0')}:${s.toString().padStart(2, '0')}`;
  return `${m}:${s.toString().padStart(2, '0')}`;
}

export function EpisodePage() {
  const { id } = useParams<{ id: string }>();
  const [searchParams] = useSearchParams();
  const targetTime = searchParams.get('t') ? parseFloat(searchParams.get('t')!) : null;

  const [episode, setEpisode] = useState<Episode | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const scrolledRef = useRef(false);

  useEffect(() => {
    if (!id) return;
    setLoading(true);
    setError(null);
    getEpisode(id)
      .then(setEpisode)
      .catch((err) => setError(err.message))
      .finally(() => setLoading(false));
  }, [id]);

  useEffect(() => {
    if (!episode || targetTime === null || scrolledRef.current) return;
    const seg = episode.transcript.find(
      (s) => targetTime >= s.start_time && targetTime < s.end_time,
    ) ?? episode.transcript.find((s) => s.start_time >= targetTime);
    if (seg) {
      scrolledRef.current = true;
      setTimeout(() => {
        document.getElementById(`seg-${seg.sequence}`)?.scrollIntoView({
          behavior: 'smooth',
          block: 'center',
        });
      }, 100);
    }
  }, [episode, targetTime]);

  if (loading) {
    return (
      <div className="min-h-screen bg-stone-50">
        <Header />
        <div className="text-center py-20">
          <Loader2 className="w-6 h-6 text-gray-400 mx-auto animate-spin" />
        </div>
      </div>
    );
  }

  if (error || !episode) {
    return (
      <div className="min-h-screen bg-stone-50">
        <Header />
        <main className="max-w-4xl mx-auto px-4 py-20 text-center">
          <p className="text-gray-500">{error === 'Not found' ? 'Episode not found.' : 'Failed to load episode.'}</p>
        </main>
      </div>
    );
  }

  const highlightSeq = targetTime !== null
    ? (episode.transcript.find((s) => targetTime >= s.start_time && targetTime < s.end_time)
      ?? episode.transcript.find((s) => s.start_time >= targetTime))?.sequence
    : null;

  return (
    <div className="min-h-screen bg-stone-50">
      <Header />

      <main className="max-w-4xl mx-auto px-4 py-8">
        {/* Episode header */}
        <div className="mb-8">
          <div className="flex items-center gap-3 text-sm text-gray-400 mb-3">
            {episode.episode_number != null && (
              <span className="inline-flex items-center gap-1">
                <Hash className="w-3.5 h-3.5" />
                Episode {episode.episode_number}
              </span>
            )}
            {episode.published_at && (
              <span className="inline-flex items-center gap-1">
                <Calendar className="w-3.5 h-3.5" />
                {formatDate(episode.published_at)}
              </span>
            )}
            {episode.duration_seconds && (
              <span className="inline-flex items-center gap-1">
                <Clock className="w-3.5 h-3.5" />
                {formatDuration(episode.duration_seconds)}
              </span>
            )}
            {episode.transcript.length > 0 && (
              <span className="inline-flex items-center gap-1">
                <FileText className="w-3.5 h-3.5" />
                {episode.transcript.length} segments
              </span>
            )}
          </div>

          <h1 className="text-2xl font-bold text-gray-900 mb-3">
            {episode.title}
          </h1>

          {episode.description && (
            <p className="text-gray-500 text-sm leading-relaxed max-w-2xl">
              {episode.description}
            </p>
          )}
        </div>

        {/* Transcript */}
        {episode.transcript.length > 0 ? (
          <section>
            <div className="flex items-center justify-between mb-4">
              <h2 className="text-sm font-semibold text-gray-900 uppercase tracking-wider">
                Transcript
              </h2>
            </div>

            <div className="bg-white border border-gray-100 rounded-xl divide-y divide-gray-50">
              {episode.transcript.map((segment) => {
                const isHighlighted = segment.sequence === highlightSeq;
                return (
                  <div
                    key={segment.id}
                    id={`seg-${segment.sequence}`}
                    className={`
                      flex gap-4 px-5 py-3 select-text
                      ${isHighlighted ? 'bg-amber-50 border-l-2 border-l-amber-400' : 'hover:bg-stone-50'}
                    `}
                  >
                    <span className="shrink-0 w-14 pt-0.5 text-right tabular-nums text-xs font-mono text-gray-400 select-none">
                      {formatTimestamp(segment.start_time)}
                    </span>
                    <p className="flex-1 min-w-0 text-sm text-gray-700 leading-relaxed">
                      {segment.text}
                    </p>
                  </div>
                );
              })}
            </div>
          </section>
        ) : (
          <div className="text-center py-12">
            <FileText className="w-8 h-8 text-gray-300 mx-auto mb-3" />
            <p className="text-gray-400 text-sm">No transcript available yet.</p>
          </div>
        )}
      </main>
    </div>
  );
}
