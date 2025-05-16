class InputsManager {
  constructor() {
    this.NONE = 'NONE'
    this.PRESSED = 'PRESSED'
    this.HELD = 'HELD'
    this.RELEASED = 'RELEASED'

    this.keys = new SimpleDict()
  }

  addKey(keycode) {
    const state = this.keys.get(keycode, this.NONE)
    this.keys.add(keycode, state)
  }

  delKey(keycode) {
    this.keys.pop(keycode)
  }

  addKeys(keycodes) {
    for (let keycode of keycodes)
      this.addKey(keycode)
  }

  delKeys(keycodes) {
    for (let keycode of keycodes)
      this.delKey(keycode)
  }

  inputsUpdate() {
    for (let key of this.keys.keys()) {
      const keycode = parseInt(key, 10)

      const state = this.keys.get(keycode)
      const down = keyIsDown(keycode)

      let newState = this.NONE
      switch (state) {
        case this.NONE:
          newState = down ? this.PRESSED : this.NONE
          break
        case this.PRESSED:
          newState = down ? this.HELD : this.RELEASED
          break
        case this.HELD:
          newState = down ? this.HELD : this.RELEASED
          break
        case  this.RELEASED:
          newState = down ? this.PRESSED : this.NONE
          break
      }

      this.keys.add(keycode, newState)
    }
  }

  keyState(keycode) {
    return this.keys.get(keycode)
  }
}
