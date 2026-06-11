import { useCallback, useEffect, useRef, useState } from 'react'
import '../App.css'
import { features } from '../shared/data/features'
import { workspaces } from '../shared/data/workspaces'
import { authApi, startupProfileApi } from '../shared/api/client'
import { Sidebar } from '../features/layout/Sidebar'
import { DiscussPage } from '../features/pages/DiscussPage'
import { FeaturePage } from '../features/pages/feature/FeaturePage'
import { HomePage } from '../features/pages/HomePage'
import { Landing } from '../features/pages/Landing'
import { LoginPage } from '../features/pages/LoginPage'
import { Onboarding } from '../features/pages/Onboarding'
import { SavedPage } from '../features/pages/SavedPage'
import { SignupPage } from '../features/pages/SignupPage'
import { SimulatorPage } from '../features/pages/SimulatorPage'
import { pathToRoute, routeToPath } from './routePaths'

const publicRoutes = new Set(['landing', 'login', 'signup'])
const LOGIN_HINT_KEY = 'sm_logged_in'
const featureIds = Object.keys(features)

export default function App() {
  const [route, setRoute] = useState(() => (
    pathToRoute(window.location.pathname, featureIds)
    || localStorage.getItem('sm_route')
    || 'landing'
  ))
  const [workspace, setWorkspace] = useState(workspaces[0])
  const [user, setUser] = useState(null)
  const [profileStatus, setProfileStatus] = useState(null)
  const [startupProfile, setStartupProfile] = useState(null)
  const [featureWorkspace, setFeatureWorkspace] = useState({})
  const [checkingSession, setCheckingSession] = useState(
    () => !publicRoutes.has(route) || localStorage.getItem(LOGIN_HINT_KEY) === 'true',
  )
  const sessionRestored = useRef(false)

  const refreshStartupProfile = useCallback(async () => {
    try {
      const profile = await startupProfileApi.get()
      setStartupProfile(profile)
      return profile
    } catch {
      setStartupProfile(null)
      return null
    }
  }, [])

  useEffect(() => {
    localStorage.setItem('sm_route', route)
    const nextPath = routeToPath(route, featureIds)

    if (window.location.pathname !== nextPath) {
      window.history.pushState({ route }, '', nextPath)
    }
  }, [route])

  useEffect(() => {
    const syncRouteFromUrl = () => {
      const nextRoute = pathToRoute(window.location.pathname, featureIds)
      setRoute(nextRoute || 'landing')
    }

    window.addEventListener('popstate', syncRouteFromUrl)
    return () => window.removeEventListener('popstate', syncRouteFromUrl)
  }, [])

  const moveByProfileStatus = async (nextRoute = route) => {
    const status = await startupProfileApi.status()
    setProfileStatus(status)

    if (status.requiresOnboarding) {
      setStartupProfile(null)
      setRoute('onboarding')
      return status
    }

    await refreshStartupProfile()

    setRoute(nextRoute === 'onboarding' || publicRoutes.has(nextRoute) ? 'home' : nextRoute)

    return status
  }

  const handleAuthSuccess = async (nextUser) => {
    localStorage.setItem(LOGIN_HINT_KEY, 'true')
    setUser(nextUser)
    setFeatureWorkspace({})
    await moveByProfileStatus('home')
  }

  const handleOnboardingComplete = async (nextProfile) => {
    const status = await startupProfileApi.status()
    setProfileStatus(status)
    setStartupProfile(nextProfile ?? await refreshStartupProfile())
    setRoute('home')
  }

  const handleLogout = async () => {
    try {
      await authApi.logout()
    } finally {
      setUser(null)
      setProfileStatus(null)
      setStartupProfile(null)
      setFeatureWorkspace({})
      localStorage.removeItem(LOGIN_HINT_KEY)
      setRoute('landing')
    }
  }

  const handleFeatureWorkspaceChange = useCallback((patch) => {
    setFeatureWorkspace((prev) => {
      const next = { ...prev, ...patch }
      return JSON.stringify(prev) === JSON.stringify(next) ? prev : next
    })
  }, [])

  useEffect(() => {
    if (sessionRestored.current) {
      return
    }
    sessionRestored.current = true

    if (publicRoutes.has(route) && localStorage.getItem(LOGIN_HINT_KEY) !== 'true') {
      return
    }

    const restoreSession = async () => {
      try {
        const currentUser = await authApi.me()
        setUser(currentUser)
        await moveByProfileStatus(route)
      } catch {
        setUser(null)
        setProfileStatus(null)
        localStorage.removeItem(LOGIN_HINT_KEY)
        if (!publicRoutes.has(route)) {
          setRoute('landing')
        }
      } finally {
        setCheckingSession(false)
      }
    }

    restoreSession()
    // Only check the server session once on initial app entry.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  const guardedRoute = !user && !publicRoutes.has(route) ? 'landing' : route
  const full = publicRoutes.has(guardedRoute) || guardedRoute === 'onboarding'

  let page
  if (checkingSession) {
    page = <main className="loading-page"><h2>StartMate AI를 준비하고 있어요</h2><p>세션 상태를 확인하는 중입니다.</p></main>
  } else if (guardedRoute === 'landing') {
    page = <Landing go={setRoute} user={user} onLogout={handleLogout} />
  } else if (guardedRoute === 'login') {
    page = <LoginPage go={setRoute} onLogin={handleAuthSuccess} />
  } else if (guardedRoute === 'signup') {
    page = <SignupPage go={setRoute} onSignup={handleAuthSuccess} />
  } else if (guardedRoute === 'onboarding' || profileStatus?.requiresOnboarding) {
    page = <Onboarding onComplete={handleOnboardingComplete} />
  } else if (guardedRoute === 'discuss') {
    page = <DiscussPage user={user} />
  } else if (guardedRoute === 'saved') {
    page = <SavedPage go={setRoute} />
  } else if (guardedRoute === 'simulator') {
    page = <SimulatorPage go={setRoute} workspace={workspace} />
  } else if (features[guardedRoute]) {
    page = (
      <FeaturePage
        key={guardedRoute}
        id={guardedRoute}
        go={setRoute}
        user={user}
        startupProfile={startupProfile}
        workspaceContext={featureWorkspace}
        onWorkspaceContextChange={handleFeatureWorkspaceChange}
        workspace={workspace}
        setWorkspace={setWorkspace}
      />
    )
  } else {
    page = <HomePage go={setRoute} workspace={workspace} />
  }

  if (full) {
    return <div className="app-root">{page}</div>
  }

  return (
    <div className="app-root">
      <Sidebar
        route={guardedRoute}
        go={setRoute}
        workspace={workspace}
        setWorkspace={setWorkspace}
        user={user}
        onLogout={handleLogout}
      />
      {page}
    </div>
  )
}
