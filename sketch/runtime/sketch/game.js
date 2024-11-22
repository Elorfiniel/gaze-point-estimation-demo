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

function aimingStateUpdate(change, initFn, resetFn, updateFn) {
  if (change.init) {
    initFn()    // Initialize tracking record
  } else if (change.drop || change.kill) {
    resetFn()   // Reset tracking record
  } else {
    updateFn()  // Update tracking record
  }
}


/**
 * Class definitions.
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


class PoGAiming {
  constructor() {
    this.limit = 120
    this.saveThres = 0.20
    this.killThres = 0.90
  }

  cannonUpdate(status) {
    return status.glared
  }

  draw(enemyX, enemyY, value) {
    push()

    const ratio = value / this.limit
    const deltaC = 1 - ratio / this.killThres

    translate(enemyX, enemyY)

    noFill()
    stroke(169, 29, 58, (1 - deltaC) * 240 + 16)

    strokeWeight(8.0 * deltaC + 4.0)
    circle(0, 0, deltaC * 60 + 20)

    const length = 8 + (1 - deltaC) * 12

    strokeWeight(1.0 + (1 - deltaC) * 3.0)
    line(-length, 0, length, 0)
    line(0, -length, 0, length)

    pop()
  }

  update(status, track, value) {
    const ratio = value / this.limit
    const killc = ratio >= this.killThres

    let newValue = value + (status.glared ? 1 : -1)
    newValue = constrain(newValue, 0, this.limit)

    let change = {
      init: !track && status.glared,
      value: track ? newValue : value,
      drop: track && newValue == 0
    }
    change.kill = killc

    return change
  }
}

class KeyAiming {
  constructor() {
    this.limit = 120
    this.saveThres = 0.40
    this.killThres = 0.90
  }

  cannonUpdate(status) {
    return status.spacebar
  }

  draw(enemyX, enemyY, value) {
    push()

    /**
     * Use the following color gradient:
     *   rgb(255, 191, 0) -> rgb(169, 29, 58)
     *   hsl(45, 100, 50) -> hsl(10, 100, 33)
     */

    colorMode(HSL)

    const ratio = value / this.limit
    const deltaC = ratio < 1 ? 1 - ratio : ratio - 1
    const deltaC_2 = deltaC > 0 ? pow(deltaC, 0.32) : 0

    translate(enemyX, enemyY)

    noStroke()
    fill(35 * deltaC_2 + 10, 100, 17 * deltaC_2 + 33)
    circle(0, 0, (1 - deltaC) * 5 + 11)

    noFill()
    stroke(35 * deltaC_2 + 10, 100, 17 * deltaC_2 + 33)

    strokeWeight((1 - deltaC) * 1.8 + 3.2)
    circle(0, 0, deltaC * 22 + 18)

    pop()
  }

  update(status, track, value) {
    const ratio = value / this.limit
    const killc = ratio >= this.killThres && ratio <= 2 - this.killThres

    let newValue = value + (status.spacebar ? 1 : -1)
    newValue = newValue % (2 * this.limit)
    newValue = constrain(newValue, 0, 2 * this.limit)

    let change = {
      init: !track && status.spacebar,
      value: track ? newValue : value,
      drop: track && !status.spacebar
    }
    change.kill = change.drop && killc

    return change
  }
}

class KeyPoGAiming {
  constructor() {
    this.strategy = undefined
    this.value = 0
  }

  cannonUpdate(status) {
    return this.strategy !== undefined && this.strategy.cannonUpdate(status)
  }

  draw(enemyX, enemyY, value) {
    if (this.strategy !== undefined) {
      this.strategy.draw(enemyX, enemyY, this.value)
    }
  }

  switchAimingStrategy(status) {
    let newStartegy = undefined

    if (this.strategy === undefined) {
      newStartegy = status.spacebar ? new KeyAiming() :
        (status.glared ? new PoGAiming() : undefined)
    } else if (status.spacebar && this.strategy instanceof PoGAiming) {
      newStartegy = new KeyAiming()
    }

    if (newStartegy !== undefined) {
      this.strategy = newStartegy
      this.value = 0
    }
  }

  update(status, track, value) {
    this.switchAimingStrategy(status)

    let retval = {init: false, value: 0, drop: false, kill: false}

    if (this.strategy !== undefined) {
      const change = this.strategy.update(status, track, this.value)

      aimingStateUpdate(
        change,
        () => { retval.init = change.init },
        () => {
          retval.drop = change.drop
          this.strategy = undefined
          this.value = 0
        },
        () => { this.value = change.value }
      )
      retval.kill = change.kill
    }

    return retval
  }
}

class Aiming {
  constructor(strategy) {
    const strategies = {
      'pog': PoGAiming,
      'key': KeyAiming,
      'key+pog': KeyPoGAiming
    }
    this.strategy = new strategies[strategy]()
    this.resetRecord()
  }

  resetRecord(record) {
    this.record = record || {track: false, value: 0}
  }

  onTarget() {
    if (this.record.track != false) {
      const ratio = this.record.value / this.strategy.limit
      if (ratio >= this.strategy.saveThres) return true
    }
    return false
  }

  cannonUpdate(status) {
    return this.record.track && this.strategy.cannonUpdate(status)
  }

  draw(enemyX, enemyY) {
    if (this.record.track != false) {
      this.strategy.draw(enemyX, enemyY, this.record.value)
    }
  }

  update(status) {
    const change = this.strategy.update(
      status, this.record.track, this.record.value
    )

    aimingStateUpdate(
      change,
      () => { this.record.track = true },
      () => { this.resetRecord() },
      () => { this.record.value = change.value }
    )

    return change.kill
  }
}


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

    const rgb = this.randomColor()

    fill(rgb[0], rgb[1], rgb[2])
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

    /**
     * gaze aiming: when PoG (eg. mouse simulated) falls within close range to the target
     * hard aiming: press SPACEBAR, until the aiming hint covers the heart of the enemy
     */
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
