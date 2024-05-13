class SocketManager {
  constructor() {
    this.socket = undefined
    this.onMessage = (msgObj) => {}
  }

  startSocket(host, port) {
    this.socket = new WebSocket(`ws://${host}:${port}/`)
    this.socket.onmessage = (event) => {
      const msgObj = JSON.parse(event.data)
      this.onMessage(msgObj)
    }
  }

  setOnMessage(onMessage) {
    this.onMessage = onMessage
  }

  sendMessage(msgObj) {
    const msg = JSON.stringify(msgObj)
    this.socket.send(msg)
  }

  closeSocket() {
    this.socket.close()
  }
}
