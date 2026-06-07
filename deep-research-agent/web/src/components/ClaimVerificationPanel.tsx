import { useState, useEffect } from 'react'
import { getRunClaims } from '@/api/research'
import type { ClaimRecord } from '@/types/claim'
import styles from './ClaimVerificationPanel.module.css'

const IC: Record<string, string> = { SUPPORTED:'✅',PARTIAL:'⚠️',UNSUPPORTED:'❌',CONTRADICTED:'🚫',NOT_CHECKED:'⬜',pending:'⬜' }
const SC: Record<string, string> = { SUPPORTED:styles.ok,PARTIAL:styles.warn,UNSUPPORTED:styles.bad,CONTRADICTED:styles.bad,NOT_CHECKED:styles.pending,pending:styles.pending }

export default function ClaimVerificationPanel({ runId, active }: { runId: string | null; active: boolean }) {
  const [c, setC] = useState<ClaimRecord[]>([])
  const [l, setL] = useState(false)
  useEffect(() => { if (!active || !runId) return; setL(true); getRunClaims(runId).then(d => setC(d.claims||[])).catch(()=>{}).finally(()=>setL(false)) }, [runId, active])
  if (!runId) return <div className={styles.section}><div className={styles.header}>论断验证</div><div className={styles.empty}>等待研究启动...</div></div>
  const counts: Record<string,number> = {}
  for (const x of c) { const s = x.verification_status||'pending'; counts[s]=(counts[s]||0)+1 }
  return (
    <div className={styles.section}>
      <div className={styles.header}>论断验证 ({c.length}) {Object.entries(counts).map(([k,v]) => <span key={k} className={styles.cb}> {IC[k]||''} {k}:{v}</span>)}</div>
      {l && <div className={styles.empty}>加载中...</div>}
      {!l && !c.length && <div className={styles.empty}>暂无论断记录（max 模式 + Verifier 后生成）</div>}
      {!l && c.map(x => { const s = x.verification_status||'pending'; return (
        <div key={x.claim_id} className={`${styles.row} ${SC[s]||''}`}>
          <div className={styles.ch}><span className={styles.ci}>{x.claim_id}</span><span className={styles.st}>{IC[s]} {s}</span><span className={styles.im}>{x.importance}</span></div>
          <div className={styles.ct}>{x.claim_text||x.raw_text||'(空)'}</div>
          {x.source_ids.length>0 && <div className={styles.src}>来源: {x.source_ids.join(', ')}</div>}
        </div>
      )})}
    </div>
  )
}
