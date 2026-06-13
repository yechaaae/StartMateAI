const staticRoutePaths = {
  landing: '/',
  login: '/login',
  signup: '/signup',
  onboarding: '/onboarding',
  generating: '/generating',
  home: '/home',
  discuss: '/discuss',
  saved: '/saved',
}

const pathRoutes = Object.fromEntries(
  Object.entries(staticRoutePaths).map(([route, path]) => [path, route]),
)

export const routeToPath = (route, featureIds = []) => {
  if (staticRoutePaths[route]) {
    return staticRoutePaths[route]
  }

  if (featureIds.includes(route)) {
    return `/features/${route}`
  }

  return '/'
}

export const pathToRoute = (pathname, featureIds = []) => {
  const normalized = pathname.endsWith('/') && pathname !== '/'
    ? pathname.slice(0, -1)
    : pathname

  if (pathRoutes[normalized]) {
    return pathRoutes[normalized]
  }

  const featureMatch = normalized.match(/^\/features\/([^/]+)$/)
  if (featureMatch && featureIds.includes(featureMatch[1])) {
    return featureMatch[1]
  }

  return null
}
