import { useCallback, useEffect, useRef, useState } from 'react'
import '../App.css'
import { features } from '../shared/data/features'
import { authApi, startupProfileApi, workspaceApi } from '../shared/api/client'
import { Sidebar } from '../features/layout/Sidebar'
import { DiscussPage } from '../features/pages/DiscussPage'
import { FeaturePage } from '../features/pages/feature/FeaturePage'
import { GeneratingPage } from '../features/pages/GeneratingPage'
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
  const [workspace, setWorkspace] = useState(null)
  const [workspaceList, setWorkspaceList] = useState([])
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

  const refreshWorkspaces = useCallback(async () => {
    try {
      const list = await workspaceApi.list()
      setWorkspaceList(list)
      setWorkspace((prev) => (
        prev
          ? (list.find((item) => item.id === prev.id) ?? list[0] ?? null)
          : (list[0] ?? null)
      ))
      return list
    } catch {
      return []
    }
  }, [])

  const handleCreateWorkspace = useCallback(async () => {
    try {
      const created = await workspaceApi.create({})
      await refreshWorkspaces()
      setWorkspace(created)
      setFeatureWorkspace({})
      setRoute('home')
    } catch {
      // 생성 실패는 무시 (사용자가 다시 시도)
    }
  }, [refreshWorkspaces])

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

  // 홈 진입 시 워크스페이스 목록을 최신화 (확정/생성 직후 반영)
  useEffect(() => {
    if (user && route === 'home') {
      refreshWorkspaces()
    }
  }, [user, route, refreshWorkspaces])

  const moveByProfileStatus = async (nextRoute = route) => {
    const status = await startupProfileApi.status()
    setProfileStatus(status)

    if (status.requiresOnboarding) {
      setStartupProfile(null)
      setRoute('onboarding')
      return status
    }

    await refreshStartupProfile()
    await refreshWorkspaces()

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
    // 온보딩 직후 아이템 추천을 미리 생성하는 "생성 중" 화면으로 보낸다.
    setRoute('generating')
  }

  const handleLogout = async () => {
    try {
      await authApi.logout()
    } finally {
      setUser(null)
      setProfileStatus(null)
      setStartupProfile(null)
      setFeatureWorkspace({})
      setWorkspace(null)
      setWorkspaceList([])
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
  const full = publicRoutes.has(guardedRoute) || guardedRoute === 'onboarding' || guardedRoute === 'generating'

  let page
  if (checkingSession) {
    page = <main className="loading-page"><h2>StartMate AI를 준비하고 있어요</h2><p>세션 상태를 확인하는 중입니다.</p></main>
  } else if (guardedRoute === 'landing') {
    page = <Landing go={setRoute} user={user} onLogout={handleLogout} />
  } else if (guardedRoute === 'login') {
    page = <LoginPage go={setRoute} onLogin={handleAuthSuccess} />
  } else if (guardedRoute === 'signup') {
    page = <SignupPage go={setRoute} onSignup={handleAuthSuccess} />
  } else if (guardedRoute === 'generating') {
    page = <GeneratingPage go={setRoute} user={user} startupProfile={startupProfile} />
  } else if (guardedRoute === 'onboarding' || profileStatus?.requiresOnboarding) {
    page = <Onboarding onComplete={handleOnboardingComplete} />
  } else if (guardedRoute === 'discuss') {
    page = <DiscussPage user={user} go={setRoute} />
  } else if (guardedRoute === 'saved') {
    page = <SavedPage go={setRoute} />
  } else if (guardedRoute === 'simulator') {
    page = <SimulatorPage go={setRoute} workspace={workspace} user={user} startupProfile={startupProfile} />
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
        workspaces={workspaceList}
        setWorkspace={setWorkspace}
        onCreateWorkspace={handleCreateWorkspace}
        user={user}
        onLogout={handleLogout}
      />
      {page}
    </div>
  )
}
