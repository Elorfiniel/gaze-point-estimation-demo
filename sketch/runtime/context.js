class GameContext {
  constructor() {
    this.states = new GameStateManager()
    this.views = new SimpleDict()
    this.assets = new SimpleDict()
    this.values = new SimpleDict()
    this.socket = new SocketManager()
    this.display = new DisplayConvert()
    this.inputs = new InputsManager()

    this.space = undefined
    this.game = undefined
    this.canvas = undefined
  }
}
