import { useState, useEffect } from 'react'
import { getRunReport } from '@/api/research'
import styles from './ReportPreview.module.css'

export default function ReportPreview({ runId, active }: { runId: string | null; active: boolean }) {
  const [r, setR] = useState(''); const [l, setL] = useState(false)
  useEffect(() => { if (!active || !runId) return; setL(true); getRunReport(runId).then(d => setR(d.report||'')).catch(()=>{}).finally(()=>setL(false)) }, [runId, active])
  if (!runId) return <div className={styles.section}><div className={styles.header}>报告预览</div><div className={styles.empty}>等待研究启动...</div></div>
  const h = r.replace(/^### (.+)$/gm,'<h3>$1</h3>').replace(/^## (.+)$/gm,'<h2>$1</h2>').replace(/^# (.+)$/gm,'<h1>$1</h1>').replace(/\*\*(.+?)\*\*/g,'<strong>$1</strong>').replace(/`([^`]+)`/g,'<code>$1</code>').replace(/^- (.+)$/gm,'· $1<br/>').replace(/\n\n/g,'</p><p>').replace(/\n/g,'<br/>')
  return (
    <div className={styles.section}>
      <div className={styles.header}>报告预览</div>
      {l && <div className={styles.empty}>加载中...</div>}
      {!l && !r && <div className={styles.empty}>报告尚未生成</div>}
      {!l && r && <div className={styles.container}><div className={styles.content} dangerouslySetInnerHTML={{ __html: `<p>${h}</p>` }} /></div>}
    </div>
  )
}
