const context = {}  // global context

function setup() {
  const aiming = 'key+pog', emitter = {name: 'demo'}

  context.canvas = document.getElementById("canvas")
  createCanvas(windowWidth, windowHeight, P2D, context.canvas)

  context.space = new Space(80)
  context.game = new GameSystem(windowWidth / 2, -2, aiming, emitter)
}

function draw() {
  const spacebar = keyIsPressed && keyCode == 32

  background(221, 230, 237)
  context.space.draw()
  context.game.draw()

  context.space.update()
  context.game.update(mouseX, mouseY, spacebar, true)
}
