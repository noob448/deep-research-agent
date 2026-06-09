export interface SourceRecord {
  source_id: string
  run_id: string
  title?: string
  url?: string
  canonical_url?: string
  doi?: string
  authors?: string[]
  published_at?: string
  fetched_at: string
  source_type: string
  quality_score?: number
  raw_text_path?: string
  saved_path?: string
  metadata?: Record<string, unknown>
}
