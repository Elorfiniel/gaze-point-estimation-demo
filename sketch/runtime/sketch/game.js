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

class AutoAimRecord {
  constructor(lockDelay) {
    this.trackingValue = 0
    this.lockDelay = lockDelay
  }

  lockedFaith() {
    return this.trackingValue / this.lockDelay
  }

  draw(x, y, lockedFaith) {
    push()

    const deltaC = 1 - this.lockedFaith() / lockedFaith

    translate(x, y)

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

  update(isAimed) {
    this.trackingValue += isAimed ? 1 : -1
    this.trackingValue = constrain(this.trackingValue, 0, this.lockDelay)
  }
}

class SuperAimRecord {
  constructor(lockDelay) {
    this.trackingValue = 0
    this.lockDelay = lockDelay
  }

  lockedFaith() {
    return this.trackingValue / this.lockDelay
  }

  draw(x, y) {
    push()

    /**
     * Use the following color gradient:
     *   rgb(255, 191, 0) -> rgb(169, 29, 58)
     *   hsl(45, 100, 50) -> hsl(10, 100, 33)
     */

    colorMode(HSL)

    const ratio = this.lockedFaith()
    const deltaC = ratio < 1 ? 1 - ratio : ratio - 1
    const deltaC_2 = deltaC > 0 ? pow(deltaC, 0.32) : 0

    translate(x, y)

    noStroke()
    fill(35 * deltaC_2 + 10, 100, 17 * deltaC_2 + 33)
    circle(0, 0, (1 - deltaC) * 5 + 11)

    noFill()
    stroke(35 * deltaC_2 + 10, 100, 17 * deltaC_2 + 33)

    strokeWeight((1 - deltaC) * 1.8 + 3.2)
    circle(0, 0, deltaC * 22 + 18)

    pop()
  }

  update(isAimed) {
    this.trackingValue += isAimed ? 1 : -1
    const value = this.trackingValue % (2 * this.lockDelay)
    this.trackingValue = constrain(value, 0, 2 * this.lockDelay)
  }
}

class AimingSystem {
  constructor(
    originX, originY, autoAimRange, autoAimAngle,
    autoAimDelay, autoAimSaveFaith, autoAimKillFaith,
    superAimDelay, superAimSaveFaith, superAimKillFaith,
  ) {
    this.aimRecord = undefined

    this.originX = originX
    this.originY = originY

    this.autoAimRange = autoAimRange
    this.autoAimAngle = autoAimAngle
    this.autoAimDelay = autoAimDelay
    this.autoAimSaveFaith = autoAimSaveFaith
    this.autoAimKillFaith = autoAimKillFaith

    this.superAimDelay = superAimDelay
    this.superAimSaveFaith = superAimSaveFaith
    this.superAimKillFaith = superAimKillFaith
  }

  switchSystem(judge, spacebar) {
    if (this.aimRecord === undefined) {
      if (spacebar == true) {
        this.aimRecord = new SuperAimRecord(this.superAimDelay)
      } else if (judge == true) {
        this.aimRecord = new AutoAimRecord(this.autoAimDelay)
      }
    } else if (this.aimRecord instanceof AutoAimRecord && spacebar == true) {
      this.aimRecord = new SuperAimRecord(this.superAimDelay)
    }
  }

  judgeAutoAim(targetX, targetY, aimX, aimY, w_angle = 1.0) {
    const radius = sqrt(pow(targetX - aimX, 2) + pow(targetY - aimY, 2))
    const fieldAimed = radius < this.autoAimRange

    const enemyAng = calculateRotation(targetX, targetY, this.originX, this.originY)
    const aimAng = calculateRotation(aimX, aimY, this.originX, this.originY)
    const sectorAimed = abs(aimAng - enemyAng) < w_angle * this.autoAimAngle

    return fieldAimed || sectorAimed
  }

  isEnemyAimed() {
    let enemyAimed = false

    if (this.aimRecord !== undefined) {
      if (this.aimRecord instanceof AutoAimRecord) {
        const faith = this.aimRecord.lockedFaith()
        if (faith >= this.autoAimSaveFaith) {
          enemyAimed = true
        }
      }

      if (this.aimRecord instanceof SuperAimRecord) {
        const faith = this.aimRecord.lockedFaith()
        if (faith >= this.superAimSaveFaith) {
          enemyAimed = true
        }
      }
    }

    return enemyAimed
  }

  draw(activeEnemy) {
    if (this.aimRecord !== undefined) {
      if (this.aimRecord instanceof AutoAimRecord) {
        this.aimRecord.draw(activeEnemy.x, activeEnemy.y, this.autoAimKillFaith)
      }

      if (this.aimRecord instanceof SuperAimRecord) {
        this.aimRecord.draw(activeEnemy.x, activeEnemy.y)
      }
    }
  }

  update(judge, spacebar) {
    let killEnemy = false

    if (this.aimRecord !== undefined) {
      if (this.aimRecord instanceof AutoAimRecord) {
        this.aimRecord.update(judge)

        const faith = this.aimRecord.lockedFaith()

        if (faith >= this.autoAimKillFaith) {
          killEnemy = true
          this.aimRecord = undefined
        }
        if (faith <= 0) this.aimRecord = undefined
      }

      if (this.aimRecord instanceof SuperAimRecord) {
        if (spacebar == false) {
          const faith = this.aimRecord.lockedFaith()

          if (faith >= this.superAimKillFaith &&
            faith <= 2 - this.superAimKillFaith
          ) {
            killEnemy = true
          }

          this.aimRecord = undefined
        } else {
          this.aimRecord.update(true)
        }
      }
    }

    return killEnemy
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
  constructor(sx, sy) {
    this.cannon = new Cannon(sx, sy)
    this.cannonRestAngle = HALF_PI
    this.cannonCurrAngle = HALF_PI
    this.cannonRotDelta = 0.05

    this.activeEnemy = undefined
    this.enemyCorpse = undefined
    this.enemyKilled = 0

    this.autoAimRange = 60
    this.autoAimAngle = HALF_PI / 10
    this.autoAimDelay = 120
    this.autoAimSaveFaith = 0.20
    this.autoAimKillFaith = 0.90

    this.superAimDelay = 120
    this.superAimSaveFaith = 0.40
    this.superAimKillFaith = 0.90

    this.explosions = []
    this.explosionMinDensity = 28
    this.explosionMaxDensity = 42

    /**
     * Auto aiming: when PoG (eg. mouse simulated) falls within close range to the target
     * Super aiming: pressing SPACEBAR, until the aiming hint covers the heart of the enemy
     */
    this.aimingSystem = new AimingSystem(
      this.cannon.x, this.cannon.y, this.autoAimRange, this.autoAimAngle,
      this.autoAimDelay, this.autoAimSaveFaith, this.autoAimKillFaith,
      this.superAimDelay, this.superAimSaveFaith, this.superAimKillFaith
    )
  }

  getGameScore() {
    return this.enemyKilled
  }

  getAimedEnemy() {
    return this.aimingSystem.isEnemyAimed() ? this.activeEnemy : undefined
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

  cannonUpdate(aimX, aimY, spacebar, gazeValid) {
    this.cannon.update()

    if (gazeValid == false && spacebar == false) return
    if (this.activeEnemy !== undefined && spacebar == true) {
      aimX = this.activeEnemy.x
      aimY = this.activeEnemy.y
    }

    this.cannonUpdateAngle(aimX, aimY)
  }

  enemyCreate(probability, maxTrials, avoid_corpse = false) {
    if (Math.random() < probability) {

      let newEnemy = undefined

      for (let i = 0; newEnemy === undefined && i < maxTrials; i++) {
        let tempEnemy = new Enemy()

        if (avoid_corpse == true && this.enemyCorpse !== undefined) {
          const judge = this.aimingSystem.judgeAutoAim(
            this.enemyCorpse.endX, this.enemyCorpse.endY,
            tempEnemy.endX, tempEnemy.endY, 2.0
          )
          if (judge == true) continue
        }

        newEnemy = tempEnemy
      }

      if (newEnemy !== undefined) this.activeEnemy = newEnemy
    }
  }

  enemyUpdate(aimX, aimY, spacebar, gazeValid) {
    if (this.activeEnemy !== undefined) {
      const judge = gazeValid && this.aimingSystem.judgeAutoAim(
        this.activeEnemy.x, this.activeEnemy.y, aimX, aimY
      )

      this.aimingSystem.switchSystem(judge, spacebar)

      const killEnemy = this.aimingSystem.update(judge, spacebar)
      if (killEnemy == true) {
        const hitRadius = sqrt(
          pow(this.cannon.x - this.activeEnemy.x, 2) +
          pow(this.cannon.y - this.activeEnemy.y, 2)
        )
        this.cannon.openFire(this.cannonRotate(), hitRadius, this.autoAimAngle)
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
      this.aimingSystem.draw(this.activeEnemy)
    }

    for (let explosion of this.explosions) {
      explosion.draw()
    }

    pop()
  }

  update(aimX, aimY, spacebar = false, gazeValid = false) {
    this.cannonUpdate(aimX, aimY, spacebar, gazeValid)
    this.enemyUpdate(aimX, aimY, spacebar, gazeValid)
    this.explosionUpdate()
  }
}
