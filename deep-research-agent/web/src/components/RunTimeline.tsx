import { useEffect, useRef } from 'react'
import styles from './RunTimeline.module.css'

interface Props { logs: { time: string; text: string }[] }
function dim(t: string) { return !t || t.startsWith('Loading') || t.startsWith('Fetching') }

export default function RunTimeline({ logs }: Props) {
  const ref = useRef<HTMLDivElement>(null)
  useEffect(() => { ref.current?.scrollTo(0, ref.current.scrollHeight) }, [logs])
  if (!logs.length) return null
  return (
    <div className={styles.section}>
      <div className={styles.header}><span>实时日志</span><span className={styles.count}>{logs.length} 条</span></div>
      <div className={styles.container} ref={ref}>
        {logs.map((l, i) => (
          <div key={i} className={`${styles.line} ${dim(l.text) ? styles.dim : ''}`}>
            <span className={styles.time}>{l.time}</span><span className={styles.text}>{l.text}</span>
          </div>
        ))}
      </div>
    </div>
  )
}
