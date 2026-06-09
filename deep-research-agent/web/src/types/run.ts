// CSP-compatible date formatting — no Date.now()/new Date()
export type RunStatus = 'running' | 'completed' | 'failed' | 'aborted'

export interface RunSummary {
  run_id: string
  status: RunStatus
  phase: string
  topic: string
  has_report: boolean
}

export interface RunDetail {
  run_id: string
  progress: Record<string, unknown>
  files: { name: string; size: number }[]
}

export interface VersionInfo {
  status: string
  git?: {
    full_hash: string
    short_hash: string
    date: string
    message: string
  }
  file_mtimes?: Record<string, number>
}
