import { useState, useEffect } from 'react'
import { getVersion } from '@/api/research'

function fmt(s: string) {
  const d = new Date(s)
  if (isNaN(d.getTime())) return s.slice(0, 16)
  const p = (n: number) => String(n).padStart(2, '0')
  return `${d.getFullYear()}-${p(d.getMonth() + 1)}-${p(d.getDate())} ${p(d.getHours())}:${p(d.getMinutes())}`
}

export default function VersionTag() {
  const [t, setT] = useState('')

  useEffect(() => {
    getVersion()
      .then((i) => {
        if (i?.git?.date) setT(`v${i.git.short_hash} · ${fmt(i.git.date)}`)
      })
      .catch(() => {})
  }, [])

  if (!t) return null

  return (
    <span
      style={{
        position: 'fixed',
        top: '10px',
        left: '14px',
        zIndex: 10,
        fontSize: '0.65rem',
        color: 'rgba(148, 163, 184, 0.45)',
        fontFamily: "'Cascadia Code', 'Fira Code', monospace",
        whiteSpace: 'nowrap',
        pointerEvents: 'none',
        userSelect: 'none',
      }}
    >
      {t}
    </span>
  )
}
