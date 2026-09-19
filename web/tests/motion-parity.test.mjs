import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import { test } from 'node:test'
import { fileURLToPath } from 'node:url'
import { dirname, resolve } from 'node:path'

const root = resolve(dirname(fileURLToPath(import.meta.url)), '..')
const read = path => readFileSync(resolve(root, path), 'utf8')

const scanPage = read('src/pages/ScanPage.jsx')
const appShell = read('src/components/AppShell.jsx')
const globalCss = read('src/styles/global.css')
const pagesCss = read('src/styles/pages.css')

test('scan illustration keeps the native animated frame structure', () => {
  assert.match(scanPage, /scan-frame/)
  assert.match(scanPage, /scan-line/)
  assert.match(scanPage, /scan-corner lt/)
  assert.match(scanPage, /scan-corner rt/)
  assert.match(scanPage, /scan-corner lb/)
  assert.match(scanPage, /scan-corner rb/)
  assert.match(pagesCss, /@keyframes scanSweep/)
  assert.match(pagesCss, /animation:\s*scanSweep 2\.2s ease-in-out infinite/)
})

test('shared motion covers routes tabs overlays and panels', () => {
  assert.match(appShell, /route-stage/)
  assert.match(globalCss, /@keyframes routeEnter/)
  assert.match(globalCss, /@keyframes scanTabPop/)
  assert.match(globalCss, /@keyframes overlayFadeIn/)
  assert.match(globalCss, /@keyframes panelSlideIn/)
  assert.match(globalCss, /@keyframes dialogPopIn/)
})

test('home entrance choreography and reduced motion are present', () => {
  assert.match(pagesCss, /@keyframes cardRise/)
  assert.match(pagesCss, /@keyframes scorePop/)
  assert.match(pagesCss, /@keyframes softPop/)
  assert.match(globalCss, /prefers-reduced-motion:\s*reduce/)
  assert.match(globalCss, /\.scan-line\s*\{\s*animation:\s*none !important/)
})
