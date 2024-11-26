class Meteor {
  constructor() {
    this.x = random(0, windowWidth)
    this.y = 0
    this.a = random(80, 160)
    this.tail = random(6, 32)
    this.size = random(2, 10)
    this.vel = random(2, 6)
  }

  draw() {
    push()

    translate(this.x, this.y)

    noFill()
    stroke(157, 178, 191, this.a)
    strokeWeight(1.0 + 0.12 * (this.size - 5))
    line(0, 0, 0, -this.tail)

    pop()
  }

  update() {
    this.y = this.y + this.vel
  }

  isVisible() {
    return this.y - this.tail < windowHeight
  }
}

class Space {
  constructor(maxMeteors) {
    this.maxMeteors = maxMeteors
    this.meteors = []

    for (let i = 0; i < this.maxMeteors; i++) {
      if (random() < 0.2) continue;

      let meteor = new Meteor()
      meteor.y = random(0, windowHeight)
      this.meteors.push(meteor)
    }
  }

  draw() {
    push()

    for (let meteor of this.meteors) {
      meteor.draw()
    }

    pop()
  }

  update() {
    let nextMeteors = []

    for (let meteor of this.meteors) {
      meteor.update()

      if (meteor.isVisible()) {
        nextMeteors.push(meteor)
      }
    }

    for (let i = nextMeteors.length; i < this.maxMeteors; i++) {
      if (random() < 0.5) continue;

      let meteor = new Meteor()
      nextMeteors.push(meteor)
    }

    this.meteors = nextMeteors
  }
}
