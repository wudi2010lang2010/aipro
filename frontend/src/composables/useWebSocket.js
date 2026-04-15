import { ref, onUnmounted } from 'vue'

export function useWebSocket(onMessage) {
  const connected = ref(false)
  let ws = null
  let reconnectTimer = null
  let heartbeatTimer = null

  function connect() {
    const url = `ws://${location.host}/ws`
    ws = new WebSocket(url)

    ws.onopen = () => {
      connected.value = true
      console.log('WebSocket 已连接')
      startHeartbeat()
    }

    ws.onmessage = (e) => {
      try {
        const msg = JSON.parse(e.data)
        if (msg.type === 'ping') ws.send(JSON.stringify({ type: 'pong' }))
        else onMessage && onMessage(msg)
      } catch {}
    }

    ws.onclose = () => {
      connected.value = false
      stopHeartbeat()
      reconnectTimer = setTimeout(connect, 5000)
    }

    ws.onerror = () => {
      ws.close()
    }
  }

  function startHeartbeat() {
    heartbeatTimer = setInterval(() => {
      if (ws?.readyState === WebSocket.OPEN) {
        ws.send(JSON.stringify({ type: 'ping' }))
      }
    }, 20000)
  }

  function stopHeartbeat() {
    clearInterval(heartbeatTimer)
  }

  function disconnect() {
    clearTimeout(reconnectTimer)
    stopHeartbeat()
    ws?.close()
  }

  onUnmounted(disconnect)

  return { connected, connect, disconnect }
}
