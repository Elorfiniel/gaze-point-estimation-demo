class DisplayConvert {
  constructor() {
    this.actualSize = undefined
    this.windowSize = undefined
    this.screenOrigin = undefined
  }

  setScreenOrigin(cx, cy) {
    this.screenOrigin = [cx, cy]
  }

  setActualSize(ah, aw) {
    this.actualSize = [ah, aw]
  }

  setWindowSize(wh, ww) {
    this.windowSize = [wh, ww]
  }

  actual2window(ax, ay) {
    const sx = ax - this.screenOrigin[0]
    const sy = -ay + this.screenOrigin[1]

    const wx = this.windowSize[1] * sx / this.actualSize[1]
    const wy = this.windowSize[0] * sy / this.actualSize[0]

    return [wx, wy]
  }

  window2actual(wx, wy) {
    const sx = this.actualSize[1] * wx / this.windowSize[1]
    const sy = this.actualSize[0] * wy / this.windowSize[0]

    const ax = sx + this.screenOrigin[0]
    const ay = -sy + this.screenOrigin[1]

    return [ax, ay]
  }
}
