import { getDownloadUrl, getRunDownloadUrl } from '@/api/research'
import styles from './DownloadPanel.module.css'

export default function DownloadPanel({ runId }: { runId: string | null }) {
  const dl = (f: string) => runId ? getRunDownloadUrl(runId, f) : getDownloadUrl(f)
  return (
    <div className={styles.section}>
      <h3>研究完成 ✨</h3>
      <div className={styles.btns}>
        <a href={dl('report.md')} className={`${styles.btn} ${styles.md}`} download>📄 下载 Markdown 报告</a>
        <a href={dl('report.docx')} className={`${styles.btn} ${styles.docx}`} download>📝 下载 Word 报告</a>
        <a href={dl('research_summary.txt')} className={`${styles.btn} ${styles.txt}`} download>📋 下载研究摘要</a>
      </div>
    </div>
  )
}
