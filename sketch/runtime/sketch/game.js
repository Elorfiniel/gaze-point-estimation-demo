/**
 * Helper functions.
 */
function calculateRotation(x, y, cx, cy) {
  const ax = x - cx
  const ay = y - cy
  const al = sqrt(ax * ax + ay * ay)

  const sign = Math.sign(ay) || Math.sign(ax)
  let ang = acos(ax / al) * sign

  return ang
}


/**
 * Class definitions.
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


class ExplosionFragments {
  constructor(x, y) {
    this.x = x
    this.y = y
    this.r = Math.random() * TWO_PI
    this.s = 1
    this.sz = random(8, 12)

    this.lifespan = random(6, 36)

    this.deltaX = random(-60, 60) / this.lifespan
    this.deltaY = random(-60, 60) / this.lifespan

    this.deltaR = 0.4 * HALF_PI * (Math.random() - 0.5)
    this.deltaS = random([0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8]) / this.lifespan

    this.type = random(['l', 'c', 's', 's', 't', 't'])
  }

  isAlive() {
    return this.lifespan > 0
  }

  randomColor() {
    const rnd = Math.random()

    if (rnd < 0.6) return [221, 230, 237]
    if (rnd < 0.8) return [39, 55, 77]

    return [169, 29, 58]
  }

  draw() {
    push()

    translate(this.x, this.y)
    rotate(this.r)
    scale(this.s)

    const [R, G, B] = this.randomColor()

    fill(R, G, B)
    stroke(39, 55, 77)
    strokeWeight(2.0)

    switch(this.type) {
      case 'l':
        line(0, 0, 0, this.sz)
        break
      case 'c':
        circle(0, 0, this.sz)
        break
      case 's':
        rectMode(CENTER)
        square(0, 0, this.sz)
        break
      case 't':
        triangle(-0.866 * this.sz, 0.5 * this.sz, 0.866 * this.sz, 0.5 * this.sz, 0, -this.sz)
        break
    }

    pop()
  }

  update() {
    this.lifespan -= 1
    this.x += this.deltaX
    this.y += this.deltaY
    this.r += this.deltaR
    this.s -= this.deltaS
  }
}

class Explosion {
  constructor(x, y, maxFragments) {
    this.fragments = []

    for (let i = 0; i < maxFragments; i++) {
      let fragment = new ExplosionFragments(x, y)
      this.fragments.push(fragment)
    }
  }

  isAlive() {
    return this.fragments.length > 0
  }

  draw() {
    push()

    for (let fragment of this.fragments) {
      fragment.draw()
    }

    pop()
  }

  update() {
    let nextFragments = []

    for (let fragment of this.fragments) {
      fragment.update()

      if (fragment.isAlive()) {
        nextFragments.push(fragment)
      }
    }

    this.fragments = nextFragments
  }
}


class GameSystem {
  constructor(sx, sy, aiming) {
    this.cannon = new Cannon(sx, sy)
    this.cannonRestAngle = HALF_PI
    this.cannonCurrAngle = HALF_PI
    this.cannonRotDelta = 0.05

    this.cannonNbDist = 80
    this.cannonNbAng = HALF_PI / 10

    this.activeEnemy = undefined
    this.enemyCorpse = undefined
    this.enemyKilled = 0

    this.explosions = []
    this.explosionMinDensity = 28
    this.explosionMaxDensity = 42

    this.aiming = new Aiming(aiming)
  }

  getGameScore() {
    return this.enemyKilled
  }

  getAimedEnemy() {
    return this.aiming.onTarget() ? this.activeEnemy : undefined
  }

  cannonRotate() {
    return this.cannonCurrAngle - this.cannonRestAngle
  }

  cannonTargetRotate(aimX, aimY) {
    return calculateRotation(aimX, aimY, this.cannon.x, this.cannon.y)
  }

  cannonDeltaRotate(aimX, aimY) {
    const targetRot = this.cannonTargetRotate(aimX, aimY)
    let deltaAngle = targetRot - this.cannonCurrAngle

    if (abs(deltaAngle) >= PI) {
      deltaAngle += -Math.sign(deltaAngle) * TWO_PI
    }

    return this.cannonRotDelta * deltaAngle
  }

  cannonUpdateAngle(aimX, aimY) {
    const delta = this.cannonDeltaRotate(aimX, aimY)
    let updated = this.cannonCurrAngle + delta

    if (abs(updated) >= TWO_PI) {
      updated -= Math.sign(updated) * TWO_PI
    }

    this.cannonCurrAngle = updated
  }

  cannonUpdate(aimX, aimY, status) {
    this.cannon.update()

    if (this.aiming.cannonUpdate(status)) {
      aimX = this.activeEnemy.x
      aimY = this.activeEnemy.y
    }

    if (status.gaze || status.spacebar) {
      this.cannonUpdateAngle(aimX, aimY)
    }
  }

  cannonNeighbors(x1, y1, x2, y2, dist, ang) {
    const radius = sqrt(pow(x1 - x2, 2) + pow(y1 - y2, 2))

    const a1 = calculateRotation(x1, y1, this.cannon.x, this.cannon.y)
    const a2 = calculateRotation(x2, y2, this.cannon.x, this.cannon.y)
    const angle = abs(a1 - a2)

    return radius < dist || angle < ang
  }

  enemyCreate(probability, maxTrials, avoid_corpse = false) {
    if (Math.random() < probability) {

      let newEnemy = undefined

      for (let i = 0; newEnemy === undefined && i < maxTrials; i++) {
        let tempEnemy = new Enemy()

        if (avoid_corpse == true && this.enemyCorpse !== undefined) {
          const collide = this.cannonNeighbors(
            this.enemyCorpse.endX, this.enemyCorpse.endY,
            tempEnemy.endX, tempEnemy.endY,
            this.cannonNbDist, 2.0 * this.cannonNbAng
          )
          if (collide == true) continue
        }

        newEnemy = tempEnemy
      }

      if (newEnemy !== undefined) this.activeEnemy = newEnemy
    }
  }

  enemyUpdate(status) {
    if (this.activeEnemy !== undefined) {
      const killEnemy = this.aiming.update(status)
      if (killEnemy == true) {
        const hitRadius = sqrt(
          pow(this.cannon.x - this.activeEnemy.x, 2) +
          pow(this.cannon.y - this.activeEnemy.y, 2)
        )
        this.cannon.openFire(this.cannonRotate(), hitRadius, this.cannonNbAng)
        this.explosionCreate(this.activeEnemy.x, this.activeEnemy.y)

        this.enemyCorpse = this.activeEnemy
        this.enemyKilled += 1
        this.activeEnemy = undefined
      } else {
        this.activeEnemy.update()
      }
    } else {
      this.enemyCreate(0.2, 4, true)
    }
  }

  explosionCreate(x, y) {
    const maxFragments = round(
      Math.random() * (this.explosionMaxDensity - this.explosionMinDensity)
    ) + this.explosionMinDensity

    let explosion = new Explosion(x, y, maxFragments)
    this.explosions.push(explosion)
  }

  explosionUpdate() {
    let nextExplosion = []

    for (let explosion of this.explosions) {
      explosion.update()

      if (explosion.isAlive()) {
        nextExplosion.push(explosion)
      }
    }

    this.explosions = nextExplosion
  }

  draw() {
    push()

    this.cannon.draw(this.cannonRotate())

    if (this.activeEnemy !== undefined) {
      this.activeEnemy.draw()
      this.aiming.draw(this.activeEnemy.x, this.activeEnemy.y)
    }

    for (let explosion of this.explosions) {
      explosion.draw()
    }

    pop()
  }

  update(aimX, aimY, spacebar = false, gazeValid = false) {
    const glared = this.activeEnemy !== undefined &&
        gazeValid && this.cannonNeighbors(
      aimX, aimY, this.activeEnemy.x, this.activeEnemy.y,
      this.cannonNbDist, this.cannonNbAng
    )
    const status = {glared: glared, spacebar: spacebar, gaze: gazeValid}

    this.cannonUpdate(aimX, aimY, status)
    this.enemyUpdate(status)
    this.explosionUpdate()
  }
}
