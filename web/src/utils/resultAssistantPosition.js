export function clamp(value, min, max) {
  return Math.min(Math.max(value, min), Math.max(min, max))
}

export function getAssistantPosition({ edge = 'right', offset = 0, viewportWidth, viewportHeight, robotSize = 76, margin = 16 }) {
  const maxLeft = Math.max(margin, viewportWidth - robotSize - margin)
  const maxTop = Math.max(margin, viewportHeight - robotSize - margin)
  const crossOffset = edge === 'top' || edge === 'bottom'
    ? clamp(offset, margin, maxLeft)
    : clamp(offset, margin, maxTop)

  if (edge === 'left') return { left: margin, top: crossOffset }
  if (edge === 'top') return { left: crossOffset, top: margin }
  if (edge === 'bottom') return { left: crossOffset, top: maxTop }
  return { left: maxLeft, top: crossOffset }
}

export function snapAssistantEdge({ left, top, viewportWidth, viewportHeight, robotSize = 76, margin = 16 }) {
  const maxLeft = Math.max(margin, viewportWidth - robotSize - margin)
  const maxTop = Math.max(margin, viewportHeight - robotSize - margin)
  const distances = {
    left: Math.abs(left - margin),
    right: Math.abs(maxLeft - left),
    top: Math.abs(top - margin),
    bottom: Math.abs(maxTop - top),
  }
  const edge = Object.keys(distances).reduce((nearest, candidate) => distances[candidate] < distances[nearest] ? candidate : nearest, 'right')
  return {
    edge,
    offset: edge === 'left' || edge === 'right' ? clamp(top, margin, maxTop) : clamp(left, margin, maxLeft),
  }
}
