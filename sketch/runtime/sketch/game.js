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

function buildAiming(aiming) {
  const strategies = {
    'pog': PoGAiming,
    'key': KeyAiming,
    'key+pog': KeyPoGAiming
  }
  const strategy = new strategies[aiming]()
  return new Aiming(strategy)
}


/**
 * Game system: eye gaze shooting game.
 */
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

    this.aiming = buildAiming(aiming)
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
