class DisplayConvert {
  setScreenSize(sh, sw) {
    this.screenSize = [sh, sw]

    const xz = sw / screen.width
    const yz = sh / screen.height
    this.zoom = 0.5 * (xz + yz)
  }

  setActualSize(ah, aw) {
    this.actualSize = [ah, aw]
  }

  setscreenOrig(cx, cy) {
    this.screenOrig = [cx, cy]
  }

  setClientOrig(msx, msy, mcx, mcy) {
    const pmcx = mcx * window.devicePixelRatio
    const pmcy = mcy * window.devicePixelRatio

    const clix = msx * this.zoom - pmcx
    const cliy = msy * this.zoom - pmcy
    this.clientOrig = [clix, cliy]

    this.clientShift = [screenLeft, screenTop]
  }

  canvasScale(canvas, w, h) {
    const rect = canvas.getBoundingClientRect()

    const csw = canvas.scrollWidth / w || 1
    const csh = canvas.scrollHeight / h || 1

    return [csw, csh, rect.left, rect.top]
  }

  actual2screen(ax, ay) {
    // Return point in screen coordinates, in physical pixels

    const [cx, cy] = this.screenOrig
    const [ah, aw] = this.actualSize

    const [sh, sw] = this.screenSize

    const tx = ax - cx
    const ty = -ay + cy

    const sx = sw * tx / aw
    const sy = sh * ty / ah

    return [sx, sy]
  }

  screen2actual(sx, sy) {
    // Return point in camera coordinates, in centimeters

    const [cx, cy] = this.screenOrig
    const [ah, aw] = this.actualSize

    const [sh, sw] = this.screenSize

    const tx = aw * sx / sw
    const ty = ah * sy / sh

    const ax = tx + cx
    const ay = -ty + cy

    return [ax, ay]
  }

  screen2canvas(sx, sy, canvas, w, h) {
    // Return point in canvas coordinates, in canvas pixels

    const [csw, csh, csl, cst] = this.canvasScale(canvas, w, h)

    const [clix, cliy] = this.clientOrig

    const [sxu, syu] = this.clientShift
    const psxu = (screenLeft - sxu) * this.zoom
    const psyu = (screenTop - syu) * this.zoom

    const vx = (sx - clix - psxu) / window.devicePixelRatio
    const vy = (sy - cliy - psyu) / window.devicePixelRatio

    const cx = (vx - csl) / csw
    const cy = (vy - cst) / csh

    return [cx, cy]
  }

  canvas2screen(cx, cy, canvas, w, h) {
    // Return point in screen coordinates, in physical pixels

    const [csw, csh, csl, cst] = this.canvasScale(canvas, w, h)

    const [clix, cliy] = this.clientOrig

    const [sxu, syu] = this.clientShift
    const psxu = (screenLeft - sxu) * this.zoom
    const psyu = (screenTop - syu) * this.zoom

    const vx = cx * csw + csl
    const vy = cy * csh + cst

    const sx = vx * window.devicePixelRatio + clix + psxu
    const sy = vy * window.devicePixelRatio + cliy + psyu

    return [sx, sy]
  }
}
