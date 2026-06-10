import test from 'node:test'
import assert from 'node:assert/strict'
import { pathToRoute, routeToPath } from './routePaths.js'

const featureIds = ['item', 'simulator', 'support']

test('maps public and workspace routes to stable browser paths', () => {
  assert.equal(routeToPath('landing', featureIds), '/')
  assert.equal(routeToPath('login', featureIds), '/login')
  assert.equal(routeToPath('signup', featureIds), '/signup')
  assert.equal(routeToPath('home', featureIds), '/home')
  assert.equal(routeToPath('discuss', featureIds), '/discuss')
  assert.equal(routeToPath('saved', featureIds), '/saved')
  assert.equal(routeToPath('onboarding', featureIds), '/onboarding')
})

test('maps feature routes under a shared feature URL namespace', () => {
  assert.equal(routeToPath('item', featureIds), '/features/item')
  assert.equal(pathToRoute('/features/simulator', featureIds), 'simulator')
})

test('falls back cleanly for unknown browser paths', () => {
  assert.equal(pathToRoute('/', featureIds), 'landing')
  assert.equal(pathToRoute('/login', featureIds), 'login')
  assert.equal(pathToRoute('/features/not-real', featureIds), null)
  assert.equal(pathToRoute('/nope', featureIds), null)
})
