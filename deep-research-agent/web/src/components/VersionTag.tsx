import { useState, useEffect } from 'react'
import { getVersion } from '@/api/research'

function fmt(s: string) { const d=new Date(s); if(isNaN(d.getTime())) return s.slice(0,16); const p=(n:number)=>String(n).padStart(2,'0'); return `${d.getFullYear()}-${p(d.getMonth()+1)}-${p(d.getDate())} ${p(d.getHours())}:${p(d.getMinutes())}` }

export default function VersionTag() {
  const [t,setT] = useState('')
  useEffect(()=>{getVersion().then(i=>{if(i?.git?.date)setT(`v${i.git.short_hash} · ${fmt(i.git.date)}`)}).catch(()=>{})},[])
  if(!t)return null
  return <span style={{fontSize:'0.72rem',color:'#64748b',background:'rgba(100,116,139,0.12)',border:'1px solid rgba(100,116,139,0.25)',borderRadius:'4px',padding:'0.10rem 0.5rem',fontFamily:"'Cascadia Code','Fira Code',monospace",whiteSpace:'nowrap'}}>{t}</span>
}
