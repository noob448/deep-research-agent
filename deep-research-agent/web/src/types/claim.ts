export type ClaimStatus =
  | 'pending'
  | 'SUPPORTED'
  | 'PARTIAL'
  | 'UNSUPPORTED'
  | 'CONTRADICTED'
  | 'NOT_CHECKED'
  | 'needs_more_sources'

export interface ClaimRecord {
  claim_id: string
  run_id: string
  section?: string
  claim_text: string
  raw_text?: string
  source_ids: string[]
  importance: 'high' | 'medium' | 'low'
  verification_status: ClaimStatus
  created_by?: string
  verification?: {
    verdict?: ClaimStatus
    verified_at?: string
    verifier?: string
    notes?: string
  }
}
