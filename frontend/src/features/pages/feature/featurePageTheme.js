export const buildFeaturePageTheme = (feature, agentMap) => {
  const agent = agentMap[feature.agent]

  return {
    '--feature-accent': agent.color,
    '--feature-accent-tint': agent.tint,
  }
}
