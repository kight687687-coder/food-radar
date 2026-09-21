import assert from 'node:assert/strict'
import { test } from 'node:test'
import { clamp, getAssistantPosition, snapAssistantEdge } from '../src/utils/resultAssistantPosition.js'

test('clamp keeps offsets inside the viewport range', () => {
  assert.equal(clamp(-4, 16, 200), 16)
  assert.equal(clamp(88, 16, 200), 88)
  assert.equal(clamp(240, 16, 200), 200)
})

test('getAssistantPosition places the robot on every viewport edge', () => {
  const base = { viewportWidth: 400, viewportHeight: 800, robotSize: 76, margin: 16 }
  assert.deepEqual(getAssistantPosition({ ...base, edge: 'left', offset: 120 }), { left: 16, top: 120 })
  assert.deepEqual(getAssistantPosition({ ...base, edge: 'right', offset: 120 }), { left: 308, top: 120 })
  assert.deepEqual(getAssistantPosition({ ...base, edge: 'top', offset: 180 }), { left: 180, top: 16 })
  assert.deepEqual(getAssistantPosition({ ...base, edge: 'bottom', offset: 180 }), { left: 180, top: 708 })
})

test('getAssistantPosition clamps offsets on a narrow viewport', () => {
  assert.deepEqual(getAssistantPosition({ edge: 'right', offset: 500, viewportWidth: 120, viewportHeight: 100, robotSize: 76, margin: 16 }), { left: 28, top: 16 })
})

test('snapAssistantEdge chooses the nearest edge and preserves the cross-axis offset', () => {
  const viewport = { viewportWidth: 400, viewportHeight: 800, robotSize: 76, margin: 16 }
  assert.deepEqual(snapAssistantEdge({ ...viewport, left: 20, top: 230 }), { edge: 'left', offset: 230 })
  assert.deepEqual(snapAssistantEdge({ ...viewport, left: 305, top: 230 }), { edge: 'right', offset: 230 })
  assert.deepEqual(snapAssistantEdge({ ...viewport, left: 160, top: 20 }), { edge: 'top', offset: 160 })
  assert.deepEqual(snapAssistantEdge({ ...viewport, left: 160, top: 700 }), { edge: 'bottom', offset: 160 })
})
