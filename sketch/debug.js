const context = {}  // global context

function setup() {
  context.canvas = document.getElementById("canvas")
  createCanvas(windowWidth, windowHeight, P2D, context.canvas)

  context.space = new Space(80)
  context.game = new GameSystem(windowWidth / 2, -2, 'key+pog')
}

function draw() {
  const spacebar = keyIsPressed && keyCode == 32

  background(221, 230, 237)
  context.space.draw()
  context.game.draw()

  context.space.update()
  context.game.update(mouseX, mouseY, spacebar, true)
}
