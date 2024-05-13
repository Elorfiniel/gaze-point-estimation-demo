class UiComponent {
  constructor(name, ctx, draw_fn = (c) => {}, update_fn = (c) => {}) {
    this.name = name
    this.ctx = ctx

    this.setDraw(draw_fn)
    this.setUpdate(update_fn)
  }

  setDraw(draw_fn) {
    this.draw = () => { push(); draw_fn(this.ctx); pop() }
  }

  setUpdate(update_fn) {
    this.update = () => { update_fn(this.ctx) }
  }
}
