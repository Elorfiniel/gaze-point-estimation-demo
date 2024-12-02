/**
 * Helper functions.
 */
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
 * Gaze aiming: when PoG (eg. mouse simulated) falls within close range to the target
 * Hard aiming: press SPACEBAR, until the aiming hint covers the heart of the enemy
 */
class PoGAiming {
  constructor() {
    this.limit = 120
    this.saveThres = 0.20
    this.killThres = 0.90
  }

  cannonUpdate(status) {
    return status.glared
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
    const ratio = value / this.limit
    const killc = ratio >= this.killThres

    let newValue = value + (status.glared ? 1 : -1)
    newValue = constrain(newValue, 0, this.limit)

    let change = {
      init: !track && status.glared,
      value: track ? newValue : value,
      drop: track && newValue == 0,
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
    const ratio = value / this.limit
    const killc = ratio >= this.killThres && ratio <= 2 - this.killThres

    let newValue = value + (status.spacebar ? 1 : -1)
    newValue = newValue % (2 * this.limit)
    newValue = constrain(newValue, 0, 2 * this.limit)

    let change = {
      init: !track && status.spacebar,
      value: track ? newValue : value,
      drop: track && !status.spacebar,
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
        () => { this.value = change.value },
      )
      retval.kill = change.kill
    }

    return retval
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

    aimingStateUpdate(
      change,
      () => { this.record.track = true },
      () => { this.resetRecord() },
      () => { this.record.value = change.value },
    )

    return change.kill
  }
}
