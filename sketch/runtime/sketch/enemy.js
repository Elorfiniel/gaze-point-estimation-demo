/**
 * Enemy definition and emitter.
 */
class Enemy {
  constructor() {
    const minX = 0.12 * windowWidth
    const maxX = windowWidth - minX

    this.x = minX + (maxX - minX) * Math.random()
    this.y = windowHeight + random(40, 60)
    this.r = 0.2 * HALF_PI * (Math.random() - 0.5)

    const quadA = -8 * windowHeight / (15 * pow(windowWidth, 2))
    const quadB = 8 * windowHeight / (15 * windowWidth)
    const quadC = 0.24 * windowHeight

    const minY = quadA * pow(this.x, 2) + quadB * this.x + quadC
    const maxY = windowHeight - 40

    this.endX = this.x
    this.endY = minY + (maxY - minY) * Math.random()
    this.endR = 0.1 * HALF_PI * (Math.random() - 0.5)

    this.moveLifespan = random(4, 8)

    this.deltaY = (this.endY - this.y) / this.moveLifespan
    this.deltaR = (this.endR - this.r) / this.moveLifespan
  }

  draw() {
    push()

    translate(this.x, this.y)
    rotate(this.r)

    // Weapons
    noFill()
    stroke(39, 55, 77)
    strokeWeight(2.0)
    line(16, -2, 16, -20)
    line(-16, -2, -16, -20)
    line(12, -10, 12, -24)
    line(-12, -10, -12, -24)

    // Ship
    fill(39, 55, 77)
    noStroke()
    triangle(20, 2, 2, -38, 2, 22)
    triangle(-20, 2, -2, -38, -2, 22)

    fill(221, 230, 237)
    circle(0, 0, 18)

    fill(169, 29, 58)
    circle(0, 0, 11)

    pop()
  }

  update() {
    if (this.moveLifespan > 0) {
      this.moveLifespan -= 1
      this.y += this.deltaY
      this.r += this.deltaR
    }
  }
}
