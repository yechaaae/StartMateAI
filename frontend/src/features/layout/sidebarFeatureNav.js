export const buildFeatureNavTheme = (feature, agentMap) => {
  const agent = agentMap[feature.agent]

  return {
    '--nav-accent': agent.color,
    '--nav-tint': agent.tint,
  }
}
