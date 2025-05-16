class GameStates {
  constructor() {
    this.INTRO = 'INTRO'
    this.CHECK = 'CHECK'
    this.ONCAM = 'ONCAM'
    this.GAME = 'GAME'
    this.CLOSE = 'CLOSE'
    this.OUTRO = 'OUTRO'
    this.EXIT = 'EXIT'
  }
}

class GameStateManager {
  constructor() {
    this.states = new GameStates()
    this.resetStates()
  }

  resetStates() {
    this.present = this.states.INTRO
    this.future = undefined
    this.renewed = true
  }

  allStates() {
    return this.states
  }

  presentState() {
    return this.present
  }

  isRenewed() {
    return this.renewed
  }

  setFutureState(state) {
    this.future = state
  }

  switchState() {
    this.renewed = this.future !== undefined
    this.present = this.future || this.present
    this.future = undefined
  }
}
