import { useState, type Dispatch, type SetStateAction } from 'react'
import { streamResearch, stopResearch as apiStop } from '@/api/research'
import type { ResearchState } from '@/App'
import styles from './ResearchForm.module.css'

interface Props { state: ResearchState; setState: Dispatch<SetStateAction<ResearchState>> }

function pad(n: number) { return String(n).padStart(2, '0') }
function ts(): string { const d = new Date(); return `${pad(d.getHours())}:${pad(d.getMinutes())}:${pad(d.getSeconds())}` }

export default function ResearchForm({ state, setState }: Props) {
  const [topic, setTopic] = useState('')
  const [effort, setEffort] = useState('deep')
  const { running, logs } = state

  async function stop() { await apiStop(); setState({ ...state, running: false, logs: [...logs, { time: ts(), text: '[系统] 用户终止了研究' }] }) }

  function start() {
    if (running || !topic.trim()) return
    const newLogs: { time: string; text: string }[] = []
    setState({ running: true, done: false, runId: null, logs: newLogs })
    streamResearch(topic.trim(), effort, {
      onLog(text) { newLogs.push({ time: ts(), text }); setState((p: ResearchState) => ({ ...p, logs: [...newLogs] })) },
      onDone() { setState((p: ResearchState) => ({ ...p, running: false, done: true, logs: [...p.logs, { time: ts(), text: '[系统] 研究报告生成完毕' }] })) },
      onError(e) { setState((p: ResearchState) => ({ ...p, running: false, logs: [...p.logs, { time: ts(), text: `[错误] ${e}` }] })) },
      onStart(d) { setState((p: ResearchState) => ({ ...p, runId: d.run_id })) },
    })
  }

  return (
    <div className={styles.section}>
      <div className={styles.row}>
        <input className={styles.input} value={topic} onChange={e => setTopic(e.target.value)} placeholder="输入你想研究的问题" onKeyDown={e => e.key === 'Enter' && start()} disabled={running} />
        <select className={styles.select} value={effort} onChange={e => setEffort(e.target.value)} disabled={running}>
          <option value="fast">⚡ 快速搜索</option><option value="deep">🔬 深度检索 (推荐)</option><option value="max">🧠 深度研究</option>
        </select>
        <button className={styles.startBtn} onClick={start} disabled={running || !topic.trim()}>
          <span>{running ? '研究中...' : '开始研究'}</span>
        </button>
        {running && <button className={styles.stopBtn} onClick={stop}>⏹ 终止</button>}
      </div>
    </div>
  )
}
