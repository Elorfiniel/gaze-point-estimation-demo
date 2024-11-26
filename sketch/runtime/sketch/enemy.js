/**
 * Enemy and EnemyEmitter.
 */
class Enemy {
  constructor(startX, startY, endX, endY) {
    this.x = startX
    this.y = startY
    this.endX = endX
    this.endY = endY

    this.r = 0.2 * HALF_PI * (random() - 0.5)
    this.endR = 0.1 * HALF_PI * (random() - 0.5)

    this.moveLifespan = random(range(4, 9, 1))

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

class EnemyEmitter {
  constructor(generator) {
    this.generator = generator
  }

  emit() {
    const [sx, sy, ex, ey] = this.generator.gen()
    return new Enemy(sx, sy, ex, ey)
  }
}


/**
 * Generate random positions within the given rectangle.
 */
class RectScatterGenerator {
  constructor(padT = 0, padL = 0, padB = 0, padR = 0) {
    this.minX = padL
    this.maxX = windowWidth - padR
    this.minY = padT
    this.maxY = windowHeight - padB
  }

  gen() {
    const sx = this.minX + (this.maxX - this.minX) * random()
    const ex = sx

    const sy = windowHeight + random(40, 60)
    const ey = this.minY + (this.maxY - this.minY) * random()

    return [sx, sy, ex, ey]
  }
}

/**
 * Generate random positions between the given quadratic curve
 * and the bottom of the screen. In other words:
 *   y_min(x) = Ax^2 + Bx + C <= y <= y_max(x) = windowHeight
 */
class QuadScatterGenerator {
  constructor(A, B, C, padL = 0, padB = 0, padR = 0) {
    this.coefs = [A, B, C]
    this.minX = padL
    this.maxX = windowWidth - padR
    this.maxY = windowHeight - padB
  }

  gen() {
    const [A, B, C] = this.coefs

    const sx = this.minX + (this.maxX - this.minX) * random()
    const ex = sx

    const minY = A * pow(sx, 2) + B * sx + C
    const sy = windowHeight + random(40, 60)
    const ey = minY + (this.maxY - minY) * random()

    return [sx, sy, ex, ey]
  }
}

/**
 * Generate random positions from a predefined grid.
 */
class GridScatterGenerator {
  constructor(rows, cols, padT = 0, padL = 0, padB = 0, padR = 0) {
    this.rows = rows
    this.cols = cols
    this.total = rows * cols

    this.origX = padL
    this.origY = padT
    this.deltaX = (windowWidth - padL - padR) / cols
    this.deltaY = (windowHeight - padT - padB) / rows

    this.count = rows * cols
  }

  gen() {
    if (this.count >= this.total) this.refresh()

    const index = this.order[this.count++]
    const i = index % this.cols, j = Math.floor(index / this.cols)

    const sx = this.origX + (i + random()) * this.deltaX
    const ex = sx

    const sy = windowHeight + random(40, 60)
    const ey = this.origY + (j + random()) * this.deltaY

    return [sx, sy, ex, ey]
  }

  refresh() {
    this.shuffle()
    this.count = 0
  }

  shuffle() {
    let array = Array.from({ length: this.total }, (_, i) => i)
    for (let i = this.total - 1; i > 0; i--) {
      // Semicolon is intentional here, otherwise ASI gives unexpected result
      const j = Math.floor(random() * (i + 1));
      [array[i], array[j]] = [array[j], array[i]];
    }

    this.order = array
  }
}
