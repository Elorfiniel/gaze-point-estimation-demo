/**
 * Helper functions.
 */
function aimingStateUpdate(change, initFn, resetFn, updateFn) {
  /**
   * The update status contains these flags:
   *   1. skip: reset tracking record (skip current enemy)
   *   2. init: initialize tracking record
   *   3. kill: reset tracking record (kill current enemy)
   *   4. fail: reset tracking record (unsuccessful aiming)
   */

  if (change.skip) {
    resetFn()
    return 'skip'
  } else if (change.init) {
    initFn()
    return 'init'
  } else if (change.kill) {
    resetFn()
    return 'kill'
  } else if (change.fail) {
    resetFn()
    return 'fail'
  } else {
    updateFn()
    return 'update'
  }
}


/**
 * PointAim: when PoG (eg. mouse simulated) falls within close range to the target
 * SpaceAim: press SPACEBAR, until the aiming hint covers the center of the enemy
 */
class PoGAiming {
  constructor() {
    this.limit = 120
    this.saveThres = 0.20
    this.killThres = 0.90
  }

  cannonUpdate(status) {
    return status.pointAimed
  }

  onTarget(track, value) {
    return track == true && value / this.limit >= this.saveThres
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
    const currThres = value / this.limit

    let newValue = value + (status.pointAimed ? 1 : -1)
    newValue = constrain(newValue, 0, this.limit)

    const change = {
      skip: status.skipTarget,
      init: !track && status.pointAimed,
      fail: track && newValue == 0,
      kill: track && currThres >= this.killThres,
    }

    return { ...change, value: newValue }
  }
}

class KeyAiming {
  constructor() {
    this.limit = 120
    this.saveThres = 0.40
    this.killThres = 0.90
  }

  cannonUpdate(status) {
    return status.spaceAimed
  }

  onTarget(track, value) {
    return track == true && value / this.limit >= this.saveThres
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
    const currThres = value / this.limit

    let newValue = value + (status.spaceAimed ? 1 : -1)
    newValue = newValue % (2 * this.limit)
    newValue = constrain(newValue, 0, 2 * this.limit)

    const change = {
      skip: status.skipTarget,
      init: !track && status.spaceAimed,
      fail: track && !status.spaceAimed,
      kill: track && !status.spaceAimed &&
        currThres >= this.killThres &&
        currThres <= 2 - this.killThres,
    }

    return { ...change, value: newValue }
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

  onTarget(track, value) {
    return this.strategy !== undefined && this.strategy.onTarget(track, this.value)
  }

  draw(enemyX, enemyY, value) {
    if (this.strategy !== undefined) {
      this.strategy.draw(enemyX, enemyY, this.value)
    }
  }

  switchAimingStrategy(status) {
    let newStartegy = undefined

    if (this.strategy === undefined) {
      newStartegy = status.spaceAimed ? new KeyAiming() :
        (status.pointAimed ? new PoGAiming() : undefined)
    } else if (status.spaceAimed && this.strategy instanceof PoGAiming) {
      newStartegy = new KeyAiming()
    }

    if (newStartegy !== undefined) {
      this.strategy = newStartegy
      this.value = 0
    }
  }

  update(status, track, value) {
    this.switchAimingStrategy(status)

    let retval = {skip: false, init: false, kill: false, fail: false}
    if (this.strategy !== undefined) {
      const change = this.strategy.update(status, track, this.value)

      aimingStateUpdate(
        change,
        () => {},
        () => {
          this.strategy = undefined
          this.value = 0
        },
        () => { this.value = change.value },
      )
      retval = Object.assign(retval, change)
    }

    return { ...retval, value: 0 }
  }
}

class Aiming {
  constructor(strategy) {
    this.strategy = strategy
    this.resetRecord()
  }

  resetRecord(record) {
    this.record = record || {track: false, value: 0}
  }

  onTarget() {
    return this.strategy.onTarget(this.record.track, this.record.value)
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

    return aimingStateUpdate(
      change,
      () => { this.record.track = true },
      () => { this.resetRecord() },
      () => { this.record.value = change.value },
    )
  }
}
