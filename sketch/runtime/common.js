/**
 * Sequence generator, commonly referred to as "range".
 *
 * Excerpt from the MDN docs:
 *   https://developer.mozilla.org/en-US/docs/Web/JavaScript/Reference/Global_Objects/Array/from
 */
function range(start, stop, step) {
  return Array.from(
    { length: Math.ceil((stop - start) / step) },
    (_, i) => start + i * step,
  )
}


/**
 * Simple dictionary to store key-value pairs.
 */
class SimpleDict {
  constructor() {
    this.dict = {}
  }

  add(key, value) {
    this.dict[key] = value
  }

  get(key, defaultValue = undefined) {
    const retval = this.dict[key]
    return retval !== undefined ? retval : defaultValue
  }

  pop(key, defaultValue = undefined) {
    const value = this.get(key, defaultValue)

    if (value !== undefined) {
      delete this.dict[key]
    }

    return value
  }

  keys() {
    return Object.keys(this.dict)
  }

  values() {
    return Object.values(this.dict)
  }
}
