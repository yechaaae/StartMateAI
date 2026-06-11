import assert from 'node:assert/strict'
import test from 'node:test'

import { agents } from '../../shared/data/agents.js'
import { features } from '../../shared/data/features.js'
import { buildFeatureNavTheme } from './sidebarFeatureNav.js'

test('buildFeatureNavTheme exposes the feature agent color as sidebar nav variables', () => {
  const theme = buildFeatureNavTheme(features.operation, agents)

  assert.deepEqual(theme, {
    '--nav-accent': 'var(--a-operation)',
    '--nav-tint': 'var(--a-operation-t)',
  })
})
