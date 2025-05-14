class KeyboardManager {
  constructor() {
    this.dict = new SimpleDict()

    this.NONE = 'NONE'
    this.PRESSED = 'PRESSED'
    this.HELD = 'HELD'
    this.RELEASED = 'RELEASED'
  }

  addKey(keycode) {
    const state = this.dict.get(keycode, this.NONE)
    this.dict.add(keycode, state)
  }

  delKey(keycode) {
    this.dict.pop(keycode)
  }

  addKeys(keycodes) {
    for (let keycode of keycodes)
      this.addKey(keycode)
  }

  delKeys(keycodes) {
    for (let keycode of keycodes)
      this.delKey(keycode)
  }

  keyUpdate() {
    for (let key of this.dict.keys()) {
      const keycode = parseInt(key, 10)

      const state = this.dict.get(keycode)
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

      this.dict.add(keycode, newState)
    }
  }

  keyState(keycode) {
    return this.dict.get(keycode)
  }
}
