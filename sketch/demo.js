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
  const view = new UiComponent(name, ctx, (c) => {
    push()

    scale(c.values.get('ui-scale'))
    draw_fn(c)

    pop()
  }, update_fn)
  ctx.views.add(name, view)
}



/**
 * Initialize views for different game states.
 */
function createViewsForIntro(ctx) {
  createViewHelper(
    'game-warn',
    ctx,
    (c) => {
      const recordMode = c.values.get('record-mode')
      const uiShift = c.values.get('ui-shift')

      const warnIntro = '[  摄  像  头  调  用  说  明  ]'
      const warnContent = '请注意，本游戏在运行过程中需要调用摄像头拍摄您的面部图像。' +
        '当您点击 “开始游戏” 按钮，即表示您知晓、理解并允许我们捕获您的面部图像。' +
        '我们的算法将试图从捕获的面部图像中分析您的视线方向，以估计您在屏幕上注视的的位置。' +
        '考虑到个体间的差异，请在体验本游戏时适当调整您的位置和姿态，以获得更好的估计。'
      let noteContent = '我们在此郑重承诺，本游戏使用摄像头捕获的面部图像仅用于' +
        '实时计算 “视线信息” 。请您知晓，您的个人数据 “不会被” 保存。'
      if (recordMode == true) {
        noteContent = '欢迎使用 “视点采集模式”，请您知晓，我们  “将会” 保存' +
          '您的面部图像，用来不断改进本游戏的 “视点估计” 性能。'
      }

      noFill()
      textAlign(CENTER, TOP)

      stroke(39, 55, 77)
      strokeWeight(2)
      rectMode(CENTER)
      rect(764, 430 + uiShift, 774, 516)

      stroke(169, 29, 58)
      strokeWeight(1.6)
      textSize(32)
      text(warnIntro, 764, 208 + uiShift)

      stroke(39, 55, 77)
      strokeWeight(1.6)
      textSize(24)
      textWrap(CHAR)
      textLeading(40)
      text(warnContent, 764, 502 + uiShift, 714, 456)
      text(noteContent, 764, 718 + uiShift, 714, 456)
    }
  )

  createViewHelper(
    'start-button',
    ctx,
    (c) => {
      const uiShift = c.values.get('ui-shift')
      const scaling = c.values.get('ui-scale')

      const buttonText = '开  始'

      const checkMouse = (x, y) => {
        x = x / scaling
        y = y / scaling

        const xInRange = 624 <= x && x <= 744
        const yInRange = 590.8 + uiShift <= y && y <= 640.8 + uiShift

        return xInRange && yInRange
      }
      const onHover = checkMouse(mouseX, mouseY)

      noFill()
      onHover ? stroke(169, 29, 58) : stroke(39, 55, 77)
      strokeWeight(2)
      rectMode(CENTER)
      rect(684, 615.8 + uiShift, 120, 50)

      strokeWeight(1.6)
      textAlign(CENTER, CENTER)
      textSize(24)
      text(buttonText, 684, 611.8 + uiShift)

      if (onHover && mouseIsPressed) {
        c.states.setFutureState(c.states.states.ONCAM)
        c.values.add('init-outer-x', screenLeft)
        c.values.add('init-outer-y', screenTop)
        c.display.setViewportOffset(devMouseX - winMouseX, devMouseY - winMouseY)
      }
    }
  )

  createViewHelper(
    'exit-button',
    ctx,
    (c) => {
      const uiShift = c.values.get('ui-shift')
      const scaling = c.values.get('ui-scale')

      const buttonText = '退  出'

      const checkMouse = (x, y) => {
        x = x / scaling
        y = y / scaling

        const xInRange = 784 <= x && x <= 904
        const yInRange = 590.8 + uiShift <= y && y <= 640.8 + uiShift

        return xInRange && yInRange
      }
      const onHover = checkMouse(mouseX, mouseY)

      noFill()
      onHover ? stroke(169, 29, 58) : stroke(39, 55, 77)
      strokeWeight(2)
      rectMode(CENTER)
      rect(844, 615.8 + uiShift, 120, 50)

      strokeWeight(1.6)
      textAlign(CENTER, CENTER)
      textSize(24)
      text(buttonText, 844, 611.8 + uiShift)

      if (onHover && mouseIsPressed) {
        c.socket.sendMessage({ opcode: 'kill-server' })
      }
    }
  )

  return ['game-warn', 'start-button', 'exit-button']
}

function createViewsForOncam(ctx) {
  createViewHelper(
    'open-cam',
    ctx,
    (c) => {
      const messageText = '[  请  等  待  摄  像  头  开  启  ]'

      const uiShift = c.values.get('ui-shift')

      noFill()
      stroke(169, 29, 58)
      strokeWeight(1.6)
      textAlign(CENTER, TOP)
      textSize(32)
      text(messageText, 764, 430 + uiShift)
    }
  )

  return ['open-cam']
}

function createViewsForGame(ctx) {
  createViewHelper(
    'count-down',
    ctx,
    (c) => {
      const uiShift = c.values.get('ui-shift')
      const maxTime = c.values.get('game-time')
      const start = c.values.get('game-start')

      const timePast = Math.floor(((new Date()).getTime() - start.getTime()) / 1000)

      let timeRemain = maxTime - timePast
      timeRemain = timeRemain < 0 ? 0 : timeRemain

      const timeText = `剩余时间：${timeRemain}s`

      noFill()
      stroke(39, 55, 77)
      strokeWeight(1.6)
      textAlign(LEFT, TOP)
      textSize(20)
      text(timeText, 36, 36 + uiShift)

      if (timeRemain == 0) {
        c.states.setFutureState(c.states.states.CLOSE)
      }
    }
  )

  createViewHelper(
    'score-board',
    ctx,
    (c) => {
      const uiShift = c.values.get('ui-shift')

      const scoreText = `击落敌机：${c.game.getGameScore()}`

      noFill()
      stroke(39, 55, 77)
      strokeWeight(1.6)
      textAlign(RIGHT, TOP)
      textSize(20)
      text(scoreText, 1492, 36 + uiShift)
    }
  )

  return ['count-down', 'score-board']
}

function createViewsForClose(ctx) {
  createViewHelper(
    'kill-cam',
    ctx,
    (c) => {
      const messageText = '[  请  等  待  摄  像  头  关  闭  ]'

      const uiShift = c.values.get('ui-shift')

      noFill()
      stroke(169, 29, 58)
      strokeWeight(1.6)
      textAlign(CENTER, TOP)
      textSize(32)
      text(messageText, 764, 430 + uiShift)
    }
  )

  return ['kill-cam']
}

function createViewsForOutro(ctx) {
  createViewHelper(
    'congrats',
    ctx,
    (c) => {
      const uiShift = c.values.get('ui-shift')

      const congratsText = 'C  O  N  G  R  A  T  U  L  A  T  I  O  N'
      const scoreText = `您总共击落敌机 ${c.game.getGameScore()} 架`

      noFill()
      stroke(169, 29, 58)
      strokeWeight(2.0)
      textAlign(CENTER, TOP)
      textSize(48)
      text(congratsText, 764, 258 + uiShift)

      stroke(39, 55, 77)
      strokeWeight(1.6)
      textSize(28)
      text(scoreText, 764, 344 + uiShift)
    }
  )

  createViewHelper(
    'restart-button',
    ctx,
    (c) => {
      const uiShift = c.values.get('ui-shift')
      const scaling = c.values.get('ui-scale')

      const buttonText = '重  新  开  始'

      const checkMouse = (x, y) => {
        x = x / scaling
        y = y / scaling

        const xInRange = 664 <= x && x <= 864
        const yInRange = 559.8 + uiShift <= y && y <= 609.8 + uiShift

        return xInRange && yInRange
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
      rect(764, 584.8 + uiShift, 200, 50)

      strokeWeight(1.6)
      textAlign(CENTER, CENTER)
      textSize(24)
      text(buttonText, 764, 580.8 + uiShift)

      if (onHover && mouseIsPressed) {
        c.states.setFutureState(c.states.states.INTRO)
      }
    }
  )

  return ['congrats', 'restart-button']
}


/**
 * Configure socket behaviors on message received.
 * Configure UI settings wrt the screen.
 */
function configureSocket(ctx) {
  ctx.socket.setOnMessage((msgObj) => {
    const allStates = ctx.states.allStates()

    if (msgObj.status == 'server-on') {
      ctx.values.add('topleft-offset', msgObj.topleftOffset)
      ctx.values.add('screen-size-px', msgObj.screenSizePx)
      ctx.values.add('screen-size-cm', msgObj.screenSizeCm)

      ctx.display.setScreenOrigin(msgObj.topleftOffset[0], msgObj.topleftOffset[1])
      ctx.display.setActualSize(msgObj.screenSizeCm[0], msgObj.screenSizeCm[1])
      ctx.display.setScreenSize(screen.height, screen.width)

      ctx.values.add('record-mode', msgObj.recordMode)
      const gameTime = msgObj.recordMode ? 90 : 60
      ctx.values.add('game-time', gameTime)
    }

    if (msgObj.status == 'camera-on') {
      ctx.states.setFutureState(allStates.GAME)
    }

    if (msgObj.status == 'camera-off') {
      ctx.states.setFutureState(allStates.OUTRO)
    }

    if (msgObj.status == 'next-ready') {
      ctx.values.add('gaze', [msgObj.gaze_x, msgObj.gaze_y, msgObj.tid])
      ctx.values.add('next-ready', true)
      ctx.values.add('next-valid', msgObj.valid)
    }
  })
}

function configureScreen(ctx) {
  // Scale properly so that the ui components can adapt to different screen size
  const scaling = windowWidth / 1528
  context.values.add('ui-scale', scaling)

  // Specifically, all components are placed in a 16:9 area centered on screen
  const idealHeight = windowWidth / 16 * 9
  const uiShift = (windowHeight - idealHeight) / 2
  context.values.add('ui-shift', uiShift / scaling)
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
  const introViews = ctx.values.get('intro-views')

  background(221, 230, 237)
  ctx.space.draw()

  drawViewsForState(ctx, introViews)

  ctx.space.update()
}

function drawWhenOncam(ctx) {
  const oncamViews = ctx.values.get('oncam-views')

  background(221, 230, 237)
  ctx.space.draw()

  drawViewsForState(ctx, oncamViews)

  ctx.space.update()
}

function drawWhenGame(ctx) {
  let gazeXY = undefined
  const spacebar = keyIsPressed && keyCode == 32

  const gameViews = ctx.values.get('game-views')
  const recordMode = ctx.values.get('record-mode')
  const gaze = ctx.values.get('gaze')
  const nextReady = ctx.values.pop('next-ready')
  const nextValid = ctx.values.get('next-valid')

  const xUpdate = screenLeft - ctx.values.get('init-outer-x')
  const yUpdate = screenTop - ctx.values.get('init-outer-y')
  if (nextValid == true) {
    const screenXY = ctx.display.actual2screen(gaze[0], gaze[1])
    gazeXY = ctx.display.screen2canvas(screenXY[0], screenXY[1], xUpdate, yUpdate)
  }

  background(221, 230, 237)
  ctx.space.draw()
  ctx.game.draw()

  if (nextReady == true) {
    if (recordMode == true) {
      const enemy = ctx.game.getAimedEnemy()

      if (enemy !== undefined) {
        const screenXY = ctx.display.canvas2screen(enemy.x, enemy.y, xUpdate, yUpdate)
        const actualXY = ctx.display.screen2actual(screenXY[0], screenXY[1])

        ctx.socket.sendMessage({
          opcode: 'save-gaze',
          tid: gaze[2],
          gaze_x: nextValid ? gaze[0] : 0,
          gaze_y: nextValid ? gaze[1] : 0,
          label_x: actualXY[0],
          label_y: actualXY[1],
        })
      }
    }
  }

  drawViewsForState(ctx, gameViews)

  const aimX = nextValid ? gazeXY[0] : undefined
  const aimY = nextValid ? gazeXY[1] : undefined

  ctx.space.update()
  ctx.game.update(aimX, aimY, spacebar, nextValid)
}

function drawWhenClose(ctx) {
  const closeViews = ctx.values.get('close-views')

  background(221, 230, 237)
  ctx.space.draw()

  drawViewsForState(ctx, closeViews)

  ctx.space.update()
}

function drawWhenOutro(ctx) {
  const outroViews = ctx.values.get('outro-views')

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
  ctx.game = new GameSystem(windowWidth / 2, -2)

  const startTime = new Date()
  ctx.values.add('game-start', startTime)
}

function actOnSwitchToClose(ctx) {
  ctx.socket.sendMessage({ opcode: 'kill-cam', hard: false })
}

function actOnSwitchToOutro(ctx) {
  ctx.socket.closeSocket()
}



/**
 * Switch game states.
 */
function switchGameState(ctx) {
  ctx.states.switchState()
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
  context.canvas = document.getElementById("canvas")
  createCanvas(windowWidth, windowHeight, P2D, context.canvas)

  textFont(context.assets.get('font'))

  configureScreen(context)
  configureSocket(context)

  const introViews = createViewsForIntro(context)
  context.values.add('intro-views', introViews)
  const oncamViews = createViewsForOncam(context)
  context.values.add('oncam-views', oncamViews)
  const gameViews = createViewsForGame(context)
  context.values.add('game-views', gameViews)
  const closeViews = createViewsForClose(context)
  context.values.add('close-views', closeViews)
  const outroViews = createViewsForOutro(context)
  context.values.add('outro-views', outroViews)
}

function draw() {
  actOnStateUpdate(context)
  drawGameStates(context)
  switchGameState(context)
}


/**
 * Close socket on page closing or reloading gracefully
 */
window.onbeforeunload = (e) => {
  if (context.socket !== undefined) {
    context.socket.sendMessage({ opcode: 'kill-cam', hard: true })
    context.socket.closeSocket()
  }
}
