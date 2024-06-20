class DisplayConvert {
  constructor() {
    this.actualSize = undefined
    this.screenSize = undefined
    this.screenOrigin = undefined
    this.viewportOffset = undefined
  }

  setScreenOrigin(cx, cy) {
    this.screenOrigin = [cx, cy]
  }

  setActualSize(ah, aw) {
    this.actualSize = [ah, aw]
  }

  setScreenSize(wh, ww) {
    this.screenSize = [wh, ww]
  }

  setViewportOffset(vsx, vsy) {
    this.viewportOffset = [vsx, vsy]
  }

  actual2screen(ax, ay) {
    const tx = ax - this.screenOrigin[0]
    const ty = -ay + this.screenOrigin[1]

    const sx = this.screenSize[1] * tx / this.actualSize[1]
    const sy = this.screenSize[0] * ty / this.actualSize[0]

    return [sx, sy]
  }

  screen2actual(sx, sy) {
    const tx = this.actualSize[1] * sx / this.screenSize[1]
    const ty = this.actualSize[0] * sy / this.screenSize[0]

    const ax = tx + this.screenOrigin[0]
    const ay = -ty + this.screenOrigin[1]

    return [ax, ay]
  }

  screen2canvas(sx, sy, sxu, syu) {
    const cx = sx - this.viewportOffset[0] - sxu
    const cy = sy - this.viewportOffset[1] - syu

    return [cx, cy]
  }

  canvas2screen(cx, cy, sxu, syu) {
    const sx = cx + this.viewportOffset[0] + sxu
    const sy = cy + this.viewportOffset[1] + syu

    return [sx, sy]
  }
}
