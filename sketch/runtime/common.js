class SimpleDict {
  constructor() {
    this.dict = {}
  }

  add(key, value) {
    this.dict[key] = value
  }

  get(key, defaultValue = undefined) {
    const retval = this.dict[key]
    return retval !== undefined ? retval : defaultValue
  }

  pop(key, defaultValue = undefined) {
    const value = this.get(key, defaultValue)

    if (value !== undefined) {
      delete this.dict[key]
    }

    return value
  }
}
