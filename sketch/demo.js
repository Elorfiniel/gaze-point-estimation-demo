/**
 * Helper functions.
 */
function drawViewsForState(ctx, viewNames) {
  for (let viewName of viewNames) {
    const view = ctx.views.get(viewName)
    view.draw()
    view.update()
  }
}

function createViewHelper(name, ctx, draw_fn = (c) => {}, update_fn = (c) => {}) {
  const view = new UiComponent(name, ctx, draw_fn, update_fn)
  ctx.views.add(name, view)
}



/**
 * Initialize views for different game states.
 */
function createGameViews(ctx) {
  const introViews = createViewsForIntro(ctx)
  ctx.values.add('introViews', introViews)
  const oncamViews = createViewsForOncam(ctx)
  ctx.values.add('oncamViews', oncamViews)
  const gameViews = createViewsForGame(ctx)
  ctx.values.add('gameViews', gameViews)
  const closeViews = createViewsForClose(ctx)
  ctx.values.add('closeViews', closeViews)
  const outroViews = createViewsForOutro(ctx)
  ctx.values.add('outroViews', outroViews)
}

function createViewsForIntro(ctx) {
  createViewHelper(
    'game-title',
    ctx,
    (c) => {
      const titleContent = '深  空  防  御'

      noFill()
      stroke(39, 55, 77)
      strokeWeight(2)
      textAlign(CENTER, TOP)
      textSize(48)
      text(titleContent, 0.5 * windowWidth, 60)
    },
  )

  createViewHelper(
    'game-warn',
    ctx,
    (c) => {
      const warnIntro = '[  摄  像  头  调  用  说  明  ]'
      const warnContent = '请注意，本游戏在运行过程中需要调用摄像头拍摄您的面部图像。' +
        '当您点击 “开始游戏” 按钮，即表示您知晓、理解并允许我们捕获您的面部图像。' +
        '我们的算法将试图从捕获的面部图像中分析您的视线方向，以估计您在屏幕上注视的的位置。' +
        '考虑到个体间的差异，请在体验本游戏时适当调整您的位置和姿态，以获得更好的估计。'
      const noteContent = '我们在此郑重承诺，本游戏使用摄像头捕获的面部图像仅用于' +
        '实时计算 “视线信息” 。请您知晓您的个人数据 “不会被” 我们保存。'

      const boxHeight = 0.6 * windowHeight
      const boxWidth = 1.5 * boxHeight

      noFill()
      textAlign(CENTER, TOP)

      stroke(39, 55, 77)
      strokeWeight(2)
      rectMode(CENTER)
      rect(0.5 * windowWidth, 0.5 * windowHeight, boxWidth, boxHeight)

      stroke(169, 29, 58)
      strokeWeight(1.6)
      textSize(32)
      text(
        warnIntro,
        0.5 * windowWidth, 0.5 * windowHeight - 0.5 * boxHeight + 36,
      )

      stroke(39, 55, 77)
      strokeWeight(1.6)
      textSize(24)
      textWrap(CHAR)
      textLeading(40)
      text(
        warnContent,
        0.5 * windowWidth, 0.5 * windowHeight + 72,
        boxWidth - 2 * 30, boxHeight - 2 * 30,
      )
      text(
        noteContent,
        0.5 * windowWidth, 0.5 * windowHeight + 288,
        boxWidth - 2 * 30, boxHeight - 2 * 30,
      )
    }
  )

  createViewHelper(
    'start-button',
    ctx,
    (c) => {
      const buttonText = '开  始  游  戏'

      const boxHeight = 0.6 * windowHeight

      const checkMouse = (x, y) => {
        const xMin = 0.5 * windowWidth - 100
        const xMax = 0.5 * windowWidth + 100
        const yMin = 0.5 * windowHeight + 0.36 * boxHeight - 25
        const yMax = 0.5 * windowHeight + 0.36 * boxHeight + 25

        return xMin <= x && x <= xMax && yMin <= y && y <= yMax
      }
      const onHover = checkMouse(mouseX, mouseY)

      noFill()
      if (onHover) {
        stroke(169, 29, 58)
      } else {
        stroke(39, 55, 77)
      }
      strokeWeight(2)
      rectMode(CENTER)
      rect(0.5 * windowWidth, 0.5 * windowHeight + 0.36 * boxHeight, 200, 50)

      strokeWeight(1.6)
      textAlign(CENTER, CENTER)
      textSize(24)
      text(
        buttonText,
        0.5 * windowWidth, 0.5 * windowHeight + 0.36 * boxHeight - 4,
      )

      if (onHover && mouseIsPressed) {
        c.states.setFutureState(c.states.states.ONCAM)
      }
    },
  )

  return ['game-title', 'game-warn', 'start-button']
}

function createViewsForOncam(ctx) {
  createViewHelper(
    'open-cam',
    ctx,
    (c) => {
      const messageText = '[  请  等  待  摄  像  头  开  启  ]'

      textAlign(CENTER, TOP); textSize(32)
      noFill()
      stroke(169, 29, 58); strokeWeight(1.6)
      text(
        messageText,
        0.5 * windowWidth, 0.5 * windowHeight,
      )
    },
  )

  return ['open-cam']
}

function createViewsForGame(ctx) {
  createViewHelper(
    'count-down',
    ctx,
    (c) => {
      const maxTime = c.values.get('game-time')

      const start = c.values.get('game-start')
      const now = new Date()

      const timePast = Math.floor((now.getTime() - start.getTime()) / 1000)

      let timeRemain = maxTime - timePast
      timeRemain = timeRemain < 0 ? 0 : timeRemain

      const timeText = `剩余时间：${timeRemain}s`

      noFill()
      stroke(39, 55, 77)
      strokeWeight(1.6)
      textAlign(LEFT, TOP)
      textSize(20)
      text(timeText, 36, 36)

      if (timeRemain == 0) {
        c.states.setFutureState(c.states.states.CLOSE)
      }
    },
  )

  createViewHelper(
    'score-board',
    ctx,
    (c) => {
      const scoreText = `击落敌机：${c.game.getEnemyKilled()}`

      noFill()
      stroke(39, 55, 77)
      strokeWeight(1.6)
      textAlign(RIGHT, TOP)
      textSize(20)
      text(scoreText, windowWidth - 36, 36)
    },
  )

  return ['count-down', 'score-board']
}

function createViewsForClose(ctx) {
  createViewHelper(
    'kill-cam',
    ctx,
    (c) => {
      const messageText = '[  请  等  待  摄  像  头  关  闭  ]'

      textAlign(CENTER, TOP); textSize(32)
      noFill()
      stroke(169, 29, 58); strokeWeight(1.6)
      text(
        messageText,
        0.5 * windowWidth, 0.5 * windowHeight,
      )
    },
  )

  return ['kill-cam']
}

function createViewsForOutro(ctx) {
  createViewHelper(
    'congrats',
    ctx,
    (c) => {
      const congratsText = 'C  O  N  G  R  A  T  U  L  A  T  I  O  N'
      const scoreText = `您总共击落敌机 ${c.game.getEnemyKilled()} 架`

      noFill()
      stroke(169, 29, 58)
      strokeWeight(2.0)
      textAlign(CENTER, TOP)
      textSize(48)
      text(congratsText, 0.5 * windowWidth, 0.3 * windowHeight)

      stroke(39, 55, 77)
      strokeWeight(1.6)
      textSize(28)
      text(scoreText, 0.5 * windowWidth, 0.4 * windowHeight)
    },
  )

  createViewHelper(
    'restart-button',
    ctx,
    (c) => {
      const buttonText = '重  新  开  始'

      const boxHeight = 0.6 * windowHeight

      const checkMouse = (x, y) => {
        const xMin = 0.5 * windowWidth - 100
        const xMax = 0.5 * windowWidth + 100
        const yMin = 0.5 * windowHeight + 0.3 * boxHeight - 25
        const yMax = 0.5 * windowHeight + 0.3 * boxHeight + 25

        return xMin <= x && x <= xMax && yMin <= y && y <= yMax
      }
      const onHover = checkMouse(mouseX, mouseY)

      noFill()
      if (onHover) {
        stroke(169, 29, 58)
      } else {
        stroke(39, 55, 77)
      }
      strokeWeight(2)
      rectMode(CENTER)
      rect(0.5 * windowWidth, 0.5 * windowHeight + 0.3 * boxHeight, 200, 50)

      strokeWeight(1.6)
      textAlign(CENTER, CENTER)
      textSize(24)
      text(
        buttonText,
        0.5 * windowWidth, 0.5 * windowHeight + 0.3 * boxHeight - 4,
      )

      if (onHover && mouseIsPressed) {
        c.states.setFutureState(c.states.states.INTRO)
      }
    },
  )

  return ['congrats', 'restart-button']
}


/**
 * Handle socket messages.
 */
function configureSocket(ctx) {
  ctx.socket.setOnMessage((msgObj) => {
    const allStates = ctx.states.allStates()

    if (msgObj.status == 'server-on') {
      ctx.values.add('topleftOffset', msgObj.topleftOffset)
      ctx.values.add('screenSizePx', msgObj.screenSizePx)
      ctx.values.add('screenSizeCm', msgObj.screenSizeCm)

      ctx.display.setScreenOrigin(msgObj.topleftOffset[0], msgObj.topleftOffset[1])
      ctx.display.setActualSize(msgObj.screenSizeCm[0], msgObj.screenSizeCm[1])
      ctx.display.setWindowSize(windowHeight, windowWidth)
    }

    if (msgObj.status == 'camera-on') {
      ctx.states.setFutureState(allStates.GAME)
    }

    if (msgObj.status == 'camera-off') {
      ctx.states.setFutureState(allStates.OUTRO)
    }

    if (msgObj.status == 'gaze-ready') {
      // TODO: add id for each gaze-ready message
      ctx.values.add('gaze', [msgObj.gaze_x, msgObj.gaze_y])
      ctx.values.add('gaze-new', true)
    }
  })
}



/**
 * Primary draw functions at different game state.
 */
function drawGameStates(ctx) {
  const presentState = ctx.states.presentState()
  const allStates = ctx.states.allStates()

  switch (presentState) {
    case allStates.INTRO:
      drawWhenIntro(ctx)
      break
    case allStates.ONCAM:
      drawWhenOncam(ctx)
      break
    case allStates.GAME:
      drawWhenGame(ctx)
      break
    case allStates.CLOSE:
      drawWhenClose(ctx)
      break
    case allStates.OUTRO:
      drawWhenOutro(ctx)
      break
  }
}

function drawWhenIntro(ctx) {
  const introViews = ctx.values.get('introViews')

  background(221, 230, 237)
  ctx.space.draw()

  drawViewsForState(ctx, introViews)

  ctx.space.update()
}

function drawWhenOncam(ctx) {
  const oncamViews = ctx.values.get('oncamViews')

  background(221, 230, 237)
  ctx.space.draw()

  drawViewsForState(ctx, oncamViews)

  ctx.space.update()
}

function drawWhenGame(ctx) {
  let gazeXY = undefined

  const gameViews = ctx.values.get('gameViews')
  const gaze = ctx.values.get('gaze')
  const gazeNew = ctx.values.pop('gaze-new')

  background(221, 230, 237)
  ctx.space.draw()

  if (gaze !== undefined) {
    gazeXY = ctx.display.actual2window(gaze[0], gaze[1])
    ctx.game.draw(gazeXY[0], gazeXY[1])
  }
  if (gazeNew !== undefined && gazeNew == true) {
    ctx.values.add('gaze-new', false)
    // TODO: send frame id and gaze on recording
  }

  drawViewsForState(ctx, gameViews)

  ctx.space.update()
  if (gaze !== undefined) {
    ctx.game.update(gazeXY[0], gazeXY[1])
  }
}

function drawWhenClose(ctx) {
  const closeViews = ctx.values.get('closeViews')

  background(221, 230, 237)
  ctx.space.draw()

  drawViewsForState(ctx, closeViews)

  ctx.space.update()
}

function drawWhenOutro(ctx) {
  const outroViews = ctx.values.get('outroViews')

  background(221, 230, 237)
  ctx.space.draw()

  drawViewsForState(ctx, outroViews)

  ctx.space.update()
}



/**
 * Initialize resources when first entering a specific state.
 */
function actOnStateUpdate(ctx) {
  if (ctx.states.isRenewed()) {
    const presentState = ctx.states.presentState()
    const allStates = ctx.states.allStates()

    switch (presentState) {
      case allStates.INTRO:
        actOnSwitchToIntro(ctx)
        break
      case allStates.ONCAM:
        actOnSwitchToOncam(ctx)
        break
      case allStates.GAME:
        actOnSwitchToGame(ctx)
        break
      case allStates.CLOSE:
        actOnSwitchToClose(ctx)
        break
      case allStates.OUTRO:
        actOnSwitchToOutro(ctx)
        break
    }
  }
}

function actOnSwitchToIntro(ctx) {
  ctx.socket.startSocket('localhost', 4200)
  ctx.space = new Space(80)
}

function actOnSwitchToOncam(ctx) {
  ctx.socket.sendMessage({ opcode: 'open-cam' })
}

function actOnSwitchToGame(ctx) {
  const xy = ctx.display.actual2window(0, 0)
  ctx.game = new GameSystem(xy[0], xy[1])

  const startTime = new Date()
  ctx.values.add('game-start', startTime)
}

function actOnSwitchToClose(ctx) {
  ctx.socket.sendMessage({ opcode: 'kill-cam' })
}

function actOnSwitchToOutro(ctx) {
  ctx.socket.closeSocket()
}



/**
 * Switch game states.
 */
function switchGameState(ctx) {
  ctx.states.switchState()
  // TODO: handle side effects
}


/**
 * Game context and the general main loop
 */
const context = new GameContext()

function preload() {
  const font = loadFont('assets/SourceHanSansSC-VF.ttf')
  context.assets.add('font', font)
}

function setup() {
  const canvas = document.getElementById("canvas")

  createCanvas(windowWidth, windowHeight, P2D, canvas)
  textFont(context.assets.get('font'))

  createGameViews(context)
  configureSocket(context)

  context.values.add('game-time', 60)
}

function draw() {
  actOnStateUpdate(context)
  drawGameStates(context)
  switchGameState(context)
}
