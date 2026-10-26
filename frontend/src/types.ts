export interface TranscriptSegment {
  id: string;
  sequence: number;
  start_time: number;
  end_time: number;
  text: string;
}

export interface Episode {
  id: string;
  title: string;
  episode_number: number | null;
  description: string | null;
  published_at: string | null;
  duration_seconds: number | null;
  original_url: string | null;
  transcript: TranscriptSegment[];
}

export interface EpisodeSummary {
  id: string;
  title: string;
  episode_number: number | null;
  description: string | null;
  published_at: string | null;
  duration_seconds: number | null;
}

export interface SearchResult {
  segment_id: string;
  episode_id: string;
  episode_title: string;
  episode_number: number | null;
  published_at: string | null;
  sequence: number;
  start_time: number;
  end_time: number;
  text: string;
  rank: number;
}

export interface SearchResponse {
  results: SearchResult[];
  total: number;
  query: string;
}
