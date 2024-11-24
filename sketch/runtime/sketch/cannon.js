/**
 * Cannon and Laser.
 */
class Laser {
  constructor(cannonRotate, hitRadius, scatterAngle) {
    this.size = sqrt(pow(windowWidth, 2) + pow(windowHeight, 2))

    this.rotate = cannonRotate
    this.radius = hitRadius
    this.angle = scatterAngle

    this.lifespan = 2
  }

  isAlive() {
    return this.lifespan > 0
  }

  draw() {
    push()

    rotate(this.rotate)

    noFill()
    stroke(169, 29, 58)
    strokeWeight(8.0)
    line(0, 0, 0, this.size)

    ellipseMode(RADIUS)
    strokeWeight(4.0)
    arc(0, 0, this.radius, this.radius, HALF_PI - this.angle, HALF_PI + this.angle)
    stroke(169, 29, 58, 24)
    strokeWeight(2.0)
    circle(0, 0, this.radius)

    pop()
  }

  update() {
    this.lifespan -= 1
  }
}

class Cannon {
  constructor(x, y) {
    this.x = x
    this.y = y
    this.lasers = []
  }

  draw(rot = 0) {
    push()

    translate(this.x, this.y)

    // Ship
    fill(39, 55, 77)
    noStroke()
    quad(45, -56, 56, 14, 7, 112, 7, -56)
    quad(-45, -56, -56, 14, -7, 112, -7, -56)

    fill(221, 230, 237)
    circle(0, 0, 52)
    circle(0, 98, 50)

    // Fire
    for (let laser of this.lasers) {
      laser.draw()
    }

    rotate(rot)

    // Weapons
    fill(39, 55, 77)
    stroke(221, 230, 237)
    strokeWeight(3.0)
    quad(-8, 0, -8, 76, 8, 76, 8, 0)

    fill(39, 55, 77)
    noStroke()
    circle(0, 0, 26)

    noFill()
    stroke(169, 29, 58)
    strokeWeight(4.0)
    circle(0, 0, 38)

    fill(169, 29, 58)
    stroke(221, 230, 237)
    strokeWeight(3.0)
    quad(-8, 76, -14, 86, 14, 86, 8, 76)

    fill(39, 55, 77)
    stroke(221, 230, 237)
    strokeWeight(3.0)
    quad(-14, 86, -14, 104, 14, 104, 14, 86)
    quad(-14, 86, -14, 104, 14, 104, 14, 86)

    pop()
  }

  openFire(cannonRotate, hitRadius, scatterAngle) {
    const laser = new Laser(cannonRotate, hitRadius, scatterAngle)
    this.lasers.push(laser)
  }

  update() {
    let nextLasers = []

    for (let laser of this.lasers) {
      laser.update()

      if (laser.isAlive()) {
        nextLasers.push(laser)
      }
    }

    this.lasers = nextLasers
  }
}
