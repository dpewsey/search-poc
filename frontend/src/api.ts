import type { Episode, EpisodeSummary, SearchResponse } from './types';

const BASE = '/api';

async function fetchJson<T>(url: string): Promise<T> {
  const res = await fetch(url);
  if (!res.ok) {
    if (res.status === 404) throw new Error('Not found');
    throw new Error(`API error: ${res.status}`);
  }
  return res.json();
}

export async function searchTranscripts(
  query: string,
  limit = 20,
  offset = 0,
): Promise<SearchResponse> {
  const params = new URLSearchParams({ q: query, limit: String(limit), offset: String(offset) });
  return fetchJson<SearchResponse>(`${BASE}/search?${params}`);
}

export async function getEpisodes(): Promise<EpisodeSummary[]> {
  const data = await fetchJson<{ episodes: EpisodeSummary[] }>(`${BASE}/episodes`);
  return data.episodes;
}

export async function getEpisode(id: string): Promise<Episode> {
  return fetchJson<Episode>(`${BASE}/episodes/${id}`);
}
