import { useState, useEffect } from 'react'
import { getRunSources } from '@/api/research'
import type { SourceRecord } from '@/types/source'
import styles from './SourceLedgerPanel.module.css'

const TL: Record<string, string> = { paper:'📄',paper_preprint:'📝',search_result:'🔍',web:'🌐',encyclopedia:'📚',community:'💬',official_doc:'📃',news:'📰',unknown:'❓' }

export default function SourceLedgerPanel({ runId, active }: { runId: string | null; active: boolean }) {
  const [s, setS] = useState<SourceRecord[]>([])
  const [l, setL] = useState(false)
  useEffect(() => { if (!active || !runId) return; setL(true); getRunSources(runId).then(d => setS(d.sources||[])).catch(()=>{}).finally(()=>setL(false)) }, [runId, active])
  if (!runId) return <div className={styles.section}><div className={styles.header}>来源账本</div><div className={styles.empty}>等待研究启动...</div></div>
  return (
    <div className={styles.section}>
      <div className={styles.header}>来源账本 ({s.length})</div>
      {l && <div className={styles.empty}>加载中...</div>}
      {!l && !s.length && <div className={styles.empty}>暂无来源记录</div>}
      {!l && s.map(r => (
        <div key={r.source_id} className={styles.row}>
          <span className={styles.id}>{r.source_id}</span><span className={styles.type}>{TL[r.source_type]||r.source_type}</span>
          <span className={styles.title}>{r.title||r.url||'(未知)'}</span>
          {r.url && <a href={r.url} target="_blank" rel="noopener" className={styles.url}>{r.url.length>60?r.url.slice(0,60)+'...':r.url}</a>}
        </div>
      ))}
    </div>
  )
}
