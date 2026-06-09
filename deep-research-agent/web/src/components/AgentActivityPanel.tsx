import { useMemo } from 'react'
import styles from './AgentActivityPanel.module.css'

interface Props { logs: { time: string; text: string }[] }
interface TC { time: string; agent: string; tool: string; query: string }

function parse(logs: Props['logs']): TC[] {
  const calls: TC[] = []
  for (const l of logs) {
    const m = l.text.match(/\[(researcher-\d+|critic|verifier)\]/)
    if (!m) continue
    const agent = m[1]
    const tm = l.text.match(/\[(?:搜索|抓取|学术搜索|中文搜索[:\w]*|TOOL_OBSERVATION)\]/)
    if (!tm) continue
    calls.push({ time: l.time, agent, tool: tm[0].replace(/[[\]]/g, ''), query: l.text.slice(0, 100) })
  }
  return calls
}

export default function AgentActivityPanel({ logs }: Props) {
  const calls = useMemo(() => parse(logs), [logs])
  const groups = useMemo(() => {
    const m: Record<string, TC[]> = {}
    for (const c of calls) { if (!m[c.agent]) m[c.agent] = []; m[c.agent].push(c) }
    return m
  }, [calls])

  if (!calls.length) return <div className={styles.section}><div className={styles.header}>Agent 活动面板</div><div className={styles.empty}>暂无工具调用记录</div></div>

  return (
    <div className={styles.section}>
      <div className={styles.header}>Agent 活动面板 ({calls.length} 次调用)</div>
      <div className={styles.container}>
        {Object.entries(groups).map(([agent, acs]) => (
          <div key={agent} className={styles.group}>
            <div className={styles.an}>{agent} <span className={styles.cn}>{acs.length} calls</span></div>
            {acs.map((c, i) => (
              <div key={i} className={styles.call}>
                <span className={styles.ct}>{c.time}</span><span className={styles.ctl}>{c.tool}</span><span className={styles.cq}>{c.query}</span>
              </div>
            ))}
          </div>
        ))}
      </div>
    </div>
  )
}
