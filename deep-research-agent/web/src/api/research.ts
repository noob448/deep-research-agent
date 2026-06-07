import type { RunDetail, RunSummary, VersionInfo } from '@/types/run'
import type { RunEvent } from '@/types/event'
import type { SourceRecord } from '@/types/source'
import type { ClaimRecord } from '@/types/claim'

// ── SSE 流式研究 ──────────────────────────────────────

interface StreamCallbacks {
  onLog: (text: string) => void
  onDone: (exitCode: number) => void
  onError: (msg: string) => void
  onStart?: (data: { task_id: string; run_id: string; resumed?: boolean }) => void
}

export function streamResearch(
  topic: string,
  effort: string,
  { onLog, onDone, onError, onStart }: StreamCallbacks
): void {
  fetch('/api/research', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ topic, effort }),
  })
    .then(async (response) => {
      const reader = response.body?.getReader()
      if (!reader) return
      const decoder = new TextDecoder()
      let buffer = ''

      while (true) {
        const { done, value } = await reader.read()
        if (done) break
        buffer += decoder.decode(value, { stream: true })
        const lines = buffer.split('\n')
        buffer = lines.pop() || ''
        for (const line of lines) {
          if (line.startsWith('data: ')) {
            try {
              const data = JSON.parse(line.slice(6))
              if (data.type === 'log') onLog(data.data)
              else if (data.type === 'done') onDone(data.exit_code)
              else if (data.type === 'start') {
                onLog(`[系统] 研究已启动 | run_id: ${data.run_id || 'N/A'}`)
                onStart?.(data)
              } else if (data.type === 'error') onError(data.data)
            } catch {
              /* ignore parse errors */
            }
          }
        }
      }
    })
    .catch(onError)
}

// ── REST 接口 ─────────────────────────────────────────

export function stopResearch(): Promise<{ stopped: number }> {
  return fetch('/api/stop', { method: 'POST' }).then((r) => r.json())
}

export function getDownloadUrl(filename: string): string {
  return `/api/download/${filename}`
}

export function getRunDownloadUrl(runId: string, filename: string): string {
  return `/api/download/${runId}/${filename}`
}

export async function getVersion(): Promise<VersionInfo> {
  const resp = await fetch('/api/version')
  return resp.json()
}

export async function listRuns(): Promise<{ runs: RunSummary[] }> {
  const resp = await fetch('/api/runs')
  return resp.json()
}

export async function getRunDetail(runId: string): Promise<RunDetail> {
  const resp = await fetch(`/api/runs/${runId}`)
  return resp.json()
}

export async function getRunEvents(runId: string): Promise<{ events: RunEvent[]; count: number }> {
  const resp = await fetch(`/api/runs/${runId}/events`)
  return resp.json()
}

export async function getRunSources(runId: string): Promise<{ sources: SourceRecord[]; count: number }> {
  const resp = await fetch(`/api/runs/${runId}/sources`)
  return resp.json()
}

export async function getRunClaims(runId: string): Promise<{ claims: ClaimRecord[]; count: number }> {
  const resp = await fetch(`/api/runs/${runId}/claims`)
  return resp.json()
}

export async function getRunReport(runId: string): Promise<{ report: string }> {
  const resp = await fetch(`/api/runs/${runId}/report`)
  return resp.json()
}
