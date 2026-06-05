/**
 * 启动研究并返回 SSE 流
 * @param {string} topic
 * @param {function} onLog - 每条日志回调
 * @param {function} onDone - 完成回调
 * @param {function} onError - 错误回调
 */
export function streamResearch(topic, effort, { onLog, onDone, onError }) {
  fetch('/api/research', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ topic, effort })
  }).then(async response => {
    const reader = response.body.getReader()
    const decoder = new TextDecoder()
    let buffer = ''

    while (true) {
      const { done, value } = await reader.read()
      if (done) break
      buffer += decoder.decode(value, { stream: true })
      const lines = buffer.split('\n')
      buffer = lines.pop() || ''
      for (const line of lines) {
        if (line.startsWith('data: ')) {
          try {
            const data = JSON.parse(line.slice(6))
            if (data.type === 'log') onLog(data.data)
            else if (data.type === 'done') onDone(data.exit_code)
            else if (data.type === 'start') onLog('[系统] 研究已启动')
            else if (data.type === 'error') onError(data.data)
          } catch (e) { /* ignore parse errors */ }
        }
      }
    }
  }).catch(onError)
}

export function stopResearch() {
  return fetch('/api/stop', { method: 'POST' }).then(r => r.json())
}

export function getDownloadUrl(filename) {
  return `/api/download/${filename}`
}
