const context = {
  websocket: new WebSocket("ws://localhost:4200/"),
  gaze: JSON.stringify([innerWidth / 2, innerHeight / 2]),
}

const commands = {
  requestGaze: JSON.stringify({ type: 'gaze' }),
}

function setup() {
  const canvas = document.getElementById("canvas")
  createCanvas(innerWidth, innerHeight, P2D, canvas)

  context.websocket.onmessage = (event) => {
    const message = JSON.parse(event.data)

    if (message.type == 'gaze') {
      background(color(255, 255, 255))

      gazeX = innerWidth * message.gaze[0] / 1920
      gazeY = innerHeight * message.gaze[1] / 1080

      circle(gazeX, gazeY, 20)
    }
  }
}

function draw() {
  context.websocket.send(commands.requestGaze)
}
