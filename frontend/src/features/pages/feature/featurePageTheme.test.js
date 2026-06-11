import assert from 'node:assert/strict'
import test from 'node:test'

import { agents } from '../../../shared/data/agents.js'
import { features } from '../../../shared/data/features.js'
import { buildFeaturePageTheme } from './featurePageTheme.js'

test('buildFeaturePageTheme exposes the feature agent color as page accent variables', () => {
  const theme = buildFeaturePageTheme(features.support, agents)

  assert.deepEqual(theme, {
    '--feature-accent': 'var(--a-policy)',
    '--feature-accent-tint': 'var(--a-policy-t)',
  })
})
