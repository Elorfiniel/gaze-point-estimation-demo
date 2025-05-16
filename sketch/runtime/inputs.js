class InputsManager {
  constructor() {
    this.NONE = 'NONE'
    this.PRESSED = 'PRESSED'
    this.HELD = 'HELD'
    this.RELEASED = 'RELEASED'

    this.keys = new SimpleDict()
    this.btns = new SimpleDict()

    window.mousePressed = (e) => {
      const props = this.btns.get(e.button, undefined)
      if (props !== undefined)
        this.btns.add(e.button, {state: props.state, down: true})
    }
    window.mouseReleased = (e) => {
      const props = this.btns.get(e.button, undefined)
      if (props !== undefined)
        this.btns.add(e.button, {state: props.state, down: false})
    }
  }

  addKey(keycode) {
    const props = this.keys.get(keycode, {state: this.NONE})
    this.keys.add(keycode, props)
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

  addBtn(button) {
    const props = this.btns.get(button, {state: this.NONE, down: false})
    this.btns.add(button, props)
  }

  delBtn(button) {
    this.btns.pop(button)
  }

  addBtns(buttons) {
    for (let button of buttons)
      this.addBtn(button)
  }

  delBtns(buttons) {
    for (let button of buttons)
      this.delBtn(button)
  }

  switchState(state, down) {
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

    return newState
  }

  inputsUpdate() {
    for (let key of this.keys.keys()) {
      const keycode = parseInt(key, 10)

      const props = this.keys.get(keycode)
      const down = keyIsDown(keycode)

      const newState = this.switchState(props.state, down)
      this.keys.add(keycode, {state: newState})
    }

    for (let btn in this.btns.keys()) {
      const button = parseInt(btn, 10)

      const props = this.btns.get(button)

      const newState = this.switchState(props.state, props.down)
      this.btns.add(button, {state: newState, down: props.down})
    }
  }

  keyState(keycode) {
    const props = this.keys.get(keycode)
    return props.state
  }

  btnState(button) {
    const props = this.btns.get(button)
    return props.state
  }
}
