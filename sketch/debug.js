/**
 * Configure keyboard status on user interaction.
 */
function configureKeyboard(ctx) {
  ctx.keyboard.addKeys([
    32, // Press SPACE to aim in key mode
    46, // Press DELETE to skip the enemy
  ])

  ctx.keyboard.spaceAimed = () => {
    const state = ctx.keyboard.keyState(32)
    return state == ctx.keyboard.PRESSED ||
      state == ctx.keyboard.HELD
  }
  ctx.keyboard.skipTarget = () => {
    const state = ctx.keyboard.keyState(46)
    return state == ctx.keyboard.PRESSED
  }
}


/**
 * Primary draw functions at different game state.
 */
function drawGameStates(ctx) {
  let aimStatus = { valid: true, aimX: mouseX, aimY: mouseY }

  let keyStatus = {
    spaceAimed: ctx.keyboard.spaceAimed(),
    skipTarget: ctx.keyboard.skipTarget(),
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
  ctx.keyboard.keyUpdate()
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

  context.keyboard = new KeyboardManager()
  configureKeyboard(context)
}

function draw() {
  drawGameStates(context)
  updateGameContext(context)

  console.log(context.game.getGameScore())
}
