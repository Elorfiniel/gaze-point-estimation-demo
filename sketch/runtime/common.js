class SimpleDict {
  constructor() {
    this.dict = {}
  }

  add(key, value) {
    this.dict[key] = value
  }

  get(key) {
    return this.dict[key]
  }

  pop(key) {
    const value = this.get(key)
    delete this.dict[key]
    return value
  }
}
