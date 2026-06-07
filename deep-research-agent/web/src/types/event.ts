export type EventType =
  | 'run_started'
  | 'plan_created'
  | 'task_dispatched'
  | 'tool_action'
  | 'tool_observation'
  | 'source_registered'
  | 'claim_registered'
  | 'claim_verified'
  | 'note_written'
  | 'report_written'
  | 'critic_started'
  | 'critic_finished'
  | 'verifier_started'
  | 'verifier_finished'
  | 'run_completed'
  | 'run_failed'

export interface RunEvent {
  event_id: string
  run_id: string
  timestamp: string
  agent?: string
  phase?: string
  event_type: EventType
  tool?: string
  input?: Record<string, unknown>
  output?: Record<string, unknown>
  budget?: { used: number; limit: number }
}
