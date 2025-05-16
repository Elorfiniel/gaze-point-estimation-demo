/**
 * Configure mouse and keyboard inputs.
 */
function configureInputs(ctx) {
  ctx.inputs.addKeys([
    32, // Press SPACE to aim in key mode
    46, // Press DELETE to skip the enemy
  ])
  ctx.inputs.addBtns([
    0,  // Left Button
  ])

  ctx.inputs.spaceAimed = () => {
    const state = ctx.inputs.keyState(32)
    return state == ctx.inputs.PRESSED ||
      state == ctx.inputs.HELD
  }
  ctx.inputs.skipTarget = () => {
    const state = ctx.inputs.keyState(46)
    return state == ctx.inputs.PRESSED
  }
}


/**
 * Primary draw functions at different game state.
 */
function drawGameStates(ctx) {
  let aimStatus = { valid: true, aimX: mouseX, aimY: mouseY }

  let keyStatus = {
    spaceAimed: ctx.inputs.spaceAimed(),
    skipTarget: ctx.inputs.skipTarget(),
  }

  background(221, 230, 237)
  ctx.space.draw()
  ctx.game.draw()

  ctx.space.update()
  ctx.game.update(aimStatus, keyStatus)
}


/**
 * Switch game states.
 */
function updateGameContext(ctx) {
  ctx.inputs.inputsUpdate()
}


/**
 * Game context and the general main loop.
*/
const context = {}  // Global game context

function setup() {
  context.canvas = document.getElementById("canvas")
  createCanvas(windowWidth, windowHeight, P2D, context.canvas)

  context.space = new Space(80)

  const aiming = 'key+pog', emitter = {name: 'demo'}
  context.game = new GameSystem(windowWidth / 2, -2, aiming, emitter)

  context.inputs = new InputsManager()
  configureInputs(context)
}

function draw() {
  drawGameStates(context)
  updateGameContext(context)
}
