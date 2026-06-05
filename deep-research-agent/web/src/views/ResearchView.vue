<template>
  <div class="research-view">
    <!-- 输入区 -->
    <div class="input-section">
      <div class="input-main">
        <input
          v-model="topic"
          class="topic-input"
          placeholder="输入你想研究的问题，例如：人工智能的发展史"
          @keydown.enter="startResearch"
          :disabled="running"
        />
        <select v-model="effort" class="effort-select" :disabled="running">
          <option value="deep">🔬 深度研究 (推荐)</option>
          <option value="fast">⚡ 快速模式</option>
        </select>
        <button class="start-btn" @click="startResearch" :disabled="running || !topic.trim()">
          <span v-if="running" class="spinner"></span>
          <span>{{ running ? '研究中...' : '开始研究' }}</span>
        </button>
        <button v-if="running" class="stop-btn" @click="stopResearch">⏹ 终止</button>
      </div>
    </div>

    <!-- 实时日志 -->
    <div v-if="logs.length" class="log-section">
      <div class="log-header">
        <span>实时日志</span>
        <span class="log-count">{{ logs.length }} 条</span>
      </div>
      <div class="log-container" ref="logContainer">
        <div v-for="(log, i) in logs" :key="i" class="log-line" :class="{ dim: isDim(log) }">
          <span class="log-time">{{ log.time }}</span>
          <span class="log-text">{{ log.text }}</span>
        </div>
      </div>
    </div>

    <!-- 下载 -->
    <div v-if="done" class="download-section">
      <h3>研究完成 ✨</h3>
      <div class="download-btns">
        <a :href="getDownloadUrl('report.md')" class="download-btn md" download>📄 下载 Markdown 报告</a>
        <a :href="getDownloadUrl('report.docx')" class="download-btn docx" download>📝 下载 Word 报告</a>
        <a :href="getDownloadUrl('research_summary.txt')" class="download-btn txt" download>📋 下载研究摘要</a>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, nextTick, watch } from 'vue'
import { streamResearch, stopResearch as apiStop, getDownloadUrl } from '@/api/research'

const topic = ref('')
const effort = ref('deep')
const running = ref(false)
const done = ref(false)
const logs = ref([])
const logContainer = ref(null)

function pad(n) { return String(n).padStart(2, '0') }
function timeStr() {
  const d = new Date()
  return `${pad(d.getHours())}:${pad(d.getMinutes())}:${pad(d.getSeconds())}`
}
function isDim(log) {
  const txt = log.text
  return !txt || txt.startsWith('Loading weights') || txt.startsWith('Fetching')
}

async function stopResearch() {
  await apiStop()
  running.value = false
  logs.value.push({ time: timeStr(), text: '[系统] 用户终止了研究' })
}

function startResearch() {
  if (running.value || !topic.value.trim()) return
  running.value = true
  done.value = false
  logs.value = []

  streamResearch(topic.value.trim(), effort.value, {
    onLog(text) {
      logs.value.push({ time: timeStr(), text })
      nextTick(() => {
        if (logContainer.value) {
          logContainer.value.scrollTop = logContainer.value.scrollHeight
        }
      })
    },
    onDone() {
      running.value = false
      done.value = true
      logs.value.push({ time: timeStr(), text: '[系统] 研究报告生成完毕' })
    },
    onError(e) {
      running.value = false
      logs.value.push({ time: timeStr(), text: `[错误] ${e}` })
    }
  })
}
</script>

<style scoped>
.research-view { max-width: 800px; margin: 0 auto; }
.input-section { margin-bottom: 1.5rem; }
.input-main { display: flex; gap: 0.75rem; }
.topic-input {
  flex: 1;
  padding: 0.85rem 1.2rem;
  border: 1px solid #334155;
  border-radius: 8px;
  background: #0f172a;
  color: #e2e8f0;
  font-size: 1rem;
  outline: none;
  transition: border .2s;
}
.topic-input:focus { border-color: #00d4ff; }
.topic-input:disabled { opacity: 0.5; }
.start-btn {
  padding: 0.85rem 1.8rem;
  border: none;
  border-radius: 8px;
  background: linear-gradient(135deg, #7b2fff, #00d4ff);
  color: #fff;
  font-size: 1rem;
  font-weight: 600;
  cursor: pointer;
  transition: opacity .2s;
  display: flex; align-items: center; gap: 0.5rem;
  white-space: nowrap;
}
.start-btn:disabled { opacity: 0.5; cursor: not-allowed; }
.stop-btn {
  padding: 0.85rem 1.2rem;
  border: 1px solid #ef4444;
  border-radius: 8px;
  background: transparent;
  color: #ef4444;
  font-size: 1rem;
  font-weight: 600;
  cursor: pointer;
  transition: all .2s;
  white-space: nowrap;
}
.stop-btn:hover { background: #ef4444; color: #fff; }
.effort-select {
  padding: 0.85rem 1rem;
  border: 1px solid #334155;
  border-radius: 8px;
  background: #0f172a;
  color: #e2e8f0;
  font-size: 0.9rem;
  outline: none;
  cursor: pointer;
  white-space: nowrap;
}
.effort-select:disabled { opacity: 0.5; cursor: not-allowed; }
.spinner {
  width: 16px; height: 16px;
  border: 2px solid #fff;
  border-top-color: transparent;
  border-radius: 50%;
  animation: spin .8s linear infinite;
}
@keyframes spin { to { transform: rotate(360deg); } }

.log-section {
  background: rgba(15, 23, 42, 0.8);
  border: 1px solid #334155;
  border-radius: 8px;
  overflow: hidden;
  margin-bottom: 1.5rem;
}
.log-header {
  display: flex; justify-content: space-between;
  padding: 0.6rem 1rem;
  background: #1e293b;
  font-size: 0.85rem;
  color: #94a3b8;
}
.log-count { color: #00d4ff; }
.log-container {
  max-height: 500px;
  overflow-y: auto;
  padding: 0.5rem 0;
  font-family: 'Cascadia Code', 'Fira Code', monospace;
  font-size: 0.82rem;
  line-height: 1.6;
}
.log-line { padding: 0.15rem 1rem; display: flex; gap: 0.6rem; }
.log-line.dim { opacity: 0.35; }
.log-time { color: #64748b; white-space: nowrap; flex-shrink: 0; }
.log-text { color: #94a3b8; word-break: break-all; }

.download-section {
  background: rgba(15, 23, 42, 0.8);
  border: 1px solid #334155;
  border-radius: 8px;
  padding: 1.5rem;
  text-align: center;
}
.download-section h3 { color: #e2e8f0; margin: 0 0 1rem; }
.download-btns { display: flex; gap: 1rem; justify-content: center; flex-wrap: wrap; }
.download-btn {
  padding: 0.7rem 1.4rem;
  border-radius: 6px;
  text-decoration: none;
  font-weight: 500;
  font-size: 0.9rem;
  transition: opacity .2s;
}
.download-btn:hover { opacity: 0.8; }
.download-btn.md  { background: #2563eb; color: #fff; }
.download-btn.docx { background: #7c3aed; color: #fff; }
.download-btn.txt { background: #334155; color: #94a3b8; }
</style>
