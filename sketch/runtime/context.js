class GameContext {
  constructor() {
    this.states = new GameStateManager()
    this.views = new SimpleDict()
    this.assets = new SimpleDict()
    this.socket = new SocketManager()
  }
}
