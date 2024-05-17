class Enemy {
  constructor() {
    const minX = 0.06 * windowWidth
    const maxX = windowWidth - minX

    this.x = minX + (maxX - minX) * Math.random()
    this.y = windowHeight + random(40, 60)
    this.r = 0.2 * HALF_PI * (Math.random() - 0.5)

    const quadA = -8 * windowHeight / (15 * pow(windowWidth, 2))
    const quadB = 8 * windowHeight / (15 * windowWidth)
    const quadC = 0.2 * windowHeight

    const minY = quadA * pow(this.x, 2) + quadB * this.x + quadC
    const maxY = windowHeight - 40

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

class AutoAimed {
  constructor(enemy, lockDelay) {
    this.trackedEnemy = enemy
    this.trackingValue = 0
    this.lockDelay = lockDelay
  }

  markAimed(isAimed) {
    this.trackingValue += isAimed ? 1 : -1
    this.trackingValue = constrain(this.trackingValue, 0, this.lockDelay)
  }

  lockedConfidence() {
    return this.trackingValue / this.lockDelay
  }

  draw(lockedConfidence) {
    push()

    const deltaC = 1 - this.lockedConfidence() / lockedConfidence

    translate(this.trackedEnemy.x, this.trackedEnemy.y)

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
}

class Laser {
  constructor(hitRadius, scatterAngle) {
    this.size = sqrt(pow(windowWidth, 2) + pow(windowHeight, 2))

    this.radius = hitRadius
    this.angle = scatterAngle

    this.lifespan = 2
  }

  isAlive() {
    return this.lifespan > 0
  }

  draw() {
    push()

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
    quad(32, -40, 40, 10, 5, 80, 5, -40)
    quad(-32, -40, -40, 10, -5, 80, -5, -40)

    fill(221, 230, 237)
    circle(0, 0, 40)
    circle(0, 70, 36)

    rotate(rot)

    // Fire

    for (let laser of this.lasers) {
      laser.draw()
    }

    // Weapons
    fill(39, 55, 77)
    stroke(221, 230, 237)
    strokeWeight(3.0)
    quad(-6, 0, -6, 54, 6, 54, 6, 0)

    fill(39, 55, 77)
    noStroke()
    circle(0, 0, 18)

    noFill()
    stroke(169, 29, 58)
    strokeWeight(4.0)
    circle(0, 0, 28)

    fill(169, 29, 58)
    stroke(221, 230, 237)
    strokeWeight(3.0)
    quad(-6, 54, -10, 62, 10, 62, 6, 54)

    fill(39, 55, 77)
    stroke(221, 230, 237)
    strokeWeight(3.0)
    quad(-10, 62, -10, 74, 10, 74, 10, 62)
    quad(-10, 62, -10, 74, 10, 74, 10, 62)

    pop()
  }

  openFire(hitRadius, scatterAngle) {
    const laser = new Laser(hitRadius, scatterAngle)
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

    if (rnd < 0.6) {
      return [221, 230, 237]
    }
    if (rnd < 0.8) {
      return [39, 55, 77]
    }

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

    this.enemies = []
    this.enemyKilled = 0
    this.maxEnemies = 1
    this.autoAimed = []
    this.fieldAutoAimRadius = 48
    this.sectorAutoAimAngle = HALF_PI / 8
    this.autoEnemyLockDelay = 100
    this.enemyLockedConfidence = 0.8

    this.explosions = []
    this.explosionMinDensity = 28
    this.explosionMaxDensity = 42
  }

  cannonRotate() {
    return this.cannonCurrAngle - this.cannonRestAngle
  }

  cannonTargetRotate(aimX, aimY) {
    const ax = aimX - this.cannon.x
    const ay = aimY - this.cannon.y
    const al = sqrt(ax * ax + ay * ay)

    const sign = Math.sign(ay) || Math.sign(ax)
    let ang = acos(ax / al) * sign

    return ang
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

  cannonUpdate(aimX, aimY) {
    this.cannon.update()
    this.cannonUpdateAngle(aimX, aimY)
  }

  searchAimed(enemy) {
    for (let aim of this.autoAimed) {
      if (aim.trackedEnemy === enemy) {
        return aim
      }
    }

    return undefined
  }

  fieldAutoAim(enemy, aimX, aimY) {
    const radius = sqrt(pow(enemy.x - aimX, 2) + pow(enemy.y - aimY, 2))
    return radius < this.fieldAutoAimRadius
  }

  sectorAutoAim(enemy, aimX, aimY) {
    const enemyAng = this.cannonTargetRotate(enemy.x, enemy.y)
    const aimAng = this.cannonTargetRotate(aimX, aimY)
    return abs(aimAng - enemyAng) < this.sectorAutoAimAngle
  }

  enemyUpdate(aimX, aimY) {
    for (let enemy of this.enemies) {
      const fieldAimed = this.fieldAutoAim(enemy, aimX, aimY)
      const sectorAimed = this.sectorAutoAim(enemy, aimX, aimY)

      let aimed = this.searchAimed(enemy)
      if (aimed !== undefined) {
        aimed.markAimed(fieldAimed || sectorAimed)
      } else if (fieldAimed || sectorAimed) {
        let newAimed = new AutoAimed(enemy, this.autoEnemyLockDelay)
        newAimed.markAimed(true)
        this.autoAimed.push(newAimed)
      }

      enemy.update()
    }

    if (this.enemies.length < this.maxEnemies && Math.random() < 0.4) {
      let newEnemy = new Enemy()
      this.enemies.push(newEnemy)
    }
  }

  addExplosion(x, y) {
    const maxFragments = round(
      Math.random() * (this.explosionMaxDensity - this.explosionMinDensity)
    ) + this.explosionMinDensity

    let explosion = new Explosion(x, y, maxFragments)
    this.explosions.push(explosion)
  }

  explosionsUpdate() {
    let nextExplosion = []

    for (let explosion of this.explosions) {
      explosion.update()

      if (explosion.isAlive()) {
        nextExplosion.push(explosion)
      }
    }

    this.explosions = nextExplosion
  }

  destroyKilledEnemies() {
    let destroyedEnemies = []
    let nextAutoAimed = []

    for (let aim of this.autoAimed) {
      const conf = aim.lockedConfidence()

      if (conf >= this.enemyLockedConfidence) {
        const enemy = aim.trackedEnemy
        destroyedEnemies.push(enemy)

        const hitRadius = sqrt(
          pow(this.cannon.x - enemy.x, 2) +
          pow(this.cannon.y - enemy.y, 2)
        )
        this.cannon.openFire(hitRadius, this.sectorAutoAimAngle)

        this.addExplosion(enemy.x, enemy.y)
      } else if (conf > 0) {
        nextAutoAimed.push(aim)
      }
    }

    this.autoAimed = nextAutoAimed
    this.enemies = this.enemies.filter((e) => {
      for (let enemy of destroyedEnemies) {
        if (e === enemy) return false
      }

      return true
    })

    this.enemyKilled += destroyedEnemies.length
  }

  draw(aimX, aimY) {
    push()

    this.cannon.draw(this.cannonRotate())

    for (let enemy of this.enemies) {
      enemy.draw()
    }

    for (let explosion of this.explosions) {
      explosion.draw()
    }

    for (let aim of this.autoAimed) {
      aim.draw(this.enemyLockedConfidence)
    }

    pop()
  }

  update(aimX, aimY) {
    this.cannonUpdate(aimX, aimY)
    this.enemyUpdate(aimX, aimY)
    this.explosionsUpdate()
    this.destroyKilledEnemies()
  }
}
