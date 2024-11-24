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
    const [cx, cy] = this.screenOrigin
    const [ah, aw] = this.actualSize
    const [wh, ww] = this.screenSize

    const tx = ax - cx
    const ty = -ay + cy

    const sx = ww * tx / aw
    const sy = wh * ty / ah

    return [sx, sy]
  }

  screen2actual(sx, sy) {
    const [cx, cy] = this.screenOrigin
    const [ah, aw] = this.actualSize
    const [wh, ww] = this.screenSize

    const tx = aw * sx / ww
    const ty = ah * sy / wh

    const ax = tx + cx
    const ay = -ty + cy

    return [ax, ay]
  }

  screen2canvas(sx, sy, sxu, syu) {
    const [vsx, vsy] = this.viewportOffset

    const cx = sx - vsx - sxu
    const cy = sy - vsy - syu

    return [cx, cy]
  }

  canvas2screen(cx, cy, sxu, syu) {
    const [vsx, vsy] = this.viewportOffset

    const sx = cx + vsx + sxu
    const sy = cy + vsy + syu

    return [sx, sy]
  }
}
