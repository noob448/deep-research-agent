import { useState, useEffect } from 'react'
import ParticleBg from './components/ParticleBg'
import ResearchForm from './components/ResearchForm'
import RunTimeline from './components/RunTimeline'
import AgentActivityPanel from './components/AgentActivityPanel'
import SourceLedgerPanel from './components/SourceLedgerPanel'
import ClaimVerificationPanel from './components/ClaimVerificationPanel'
import ReportPreview from './components/ReportPreview'
import DownloadPanel from './components/DownloadPanel'
import VersionTag from './components/VersionTag'
import styles from './App.module.css'

export interface ResearchState {
  running: boolean
  done: boolean
  runId: string | null
  logs: { time: string; text: string }[]
}

export default function App() {
  const [state, setState] = useState<ResearchState>({
    running: false,
    done: false,
    runId: null,
    logs: [],
  })
  const [activeTab, setActiveTab] = useState<'log' | 'agents' | 'sources' | 'claims' | 'report'>('log')

  // Reset tabs when new research starts
  useEffect(() => {
    if (state.running) {
      setActiveTab('log')
    }
  }, [state.running])

  return (
    <div className={styles.container}>
      <ParticleBg />
      <VersionTag />
      <header className={styles.header}>
        <h1 className={styles.title}>Deep Research Agent</h1>
        <p className={styles.subtitle}>多智能体深度研究系统</p>
      </header>
      <main className={styles.main}>
        <ResearchForm state={state} setState={setState} />

        {state.logs.length > 0 && (
          <div className={styles.tabs}>
            <button
              className={`${styles.tab} ${activeTab === 'log' ? styles.active : ''}`}
              onClick={() => setActiveTab('log')}
            >
              实时日志 ({state.logs.length})
            </button>
            <button
              className={`${styles.tab} ${activeTab === 'agents' ? styles.active : ''}`}
              onClick={() => setActiveTab('agents')}
            >
              Agent 活动
            </button>
            <button
              className={`${styles.tab} ${activeTab === 'sources' ? styles.active : ''}`}
              onClick={() => setActiveTab('sources')}
            >
              来源账本
            </button>
            <button
              className={`${styles.tab} ${activeTab === 'claims' ? styles.active : ''}`}
              onClick={() => setActiveTab('claims')}
            >
              论断验证
            </button>
            <button
              className={`${styles.tab} ${activeTab === 'report' ? styles.active : ''}`}
              onClick={() => setActiveTab('report')}
            >
              报告预览
            </button>
          </div>
        )}

        {activeTab === 'log' && <RunTimeline logs={state.logs} />}
        {activeTab === 'agents' && <AgentActivityPanel logs={state.logs} />}
        {activeTab === 'sources' && <SourceLedgerPanel runId={state.runId} active={activeTab === 'sources'} />}
        {activeTab === 'claims' && <ClaimVerificationPanel runId={state.runId} active={activeTab === 'claims'} />}
        {activeTab === 'report' && <ReportPreview runId={state.runId} active={activeTab === 'report'} />}

        {state.done && <DownloadPanel runId={state.runId} />}
      </main>
    </div>
  )
}
