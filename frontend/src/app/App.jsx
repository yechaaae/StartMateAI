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
  // 워크스페이스 = 아이템. 아이템 추천에서 '이 아이템으로 시작'을 누르면 새 워크스페이스가 생긴다.
  const [workspaceList, setWorkspaceList] = useState(workspaces)
  const [workspace, setWorkspace] = useState(workspaces[0] ?? null)
  const [user, setUser] = useState(null)
  const [profileStatus, setProfileStatus] = useState(null)
  const [startupProfile, setStartupProfile] = useState(null)
  const [featureWorkspace, setFeatureWorkspace] = useState({})
  // '아이템 추가하기'로 진입하면 아이템 기능의 추천/직접입력 선택 화면을 보여준다.
  // nonce는 이미 아이템 페이지에 있을 때도 강제로 remount해서 선택 화면부터 다시 시작하게 한다.
  const [itemEntryNonce, setItemEntryNonce] = useState(0)
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
    const resolvedProfile = nextProfile ?? await refreshStartupProfile()
    setStartupProfile(resolvedProfile)
    // 처음 가입 직후 창업 아이템이 없으면 '추천 받기 / 직접 입력' 선택 화면을 먼저 보여준다.
    // (창업 후로 이미 운영 아이템을 입력했다면 홈으로 바로 이동)
    const hasItem = Boolean(resolvedProfile?.currentItemName && resolvedProfile.currentItemName.trim())
    setRoute(hasItem ? 'home' : 'item')
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

  const handleAddItem = useCallback(() => {
    // 추천/직접입력 선택 화면을 먼저 보여준다(아이템 기능에 choice 단계로 진입).
    setItemEntryNonce((nonce) => nonce + 1)
    setRoute('item')
  }, [])

  // '이 아이템으로 시작'(추천/직접입력) → 그 아이템으로 새 워크스페이스를 만들어 현재 워크스페이스로 설정한다.
  // 워크스페이스 자체가 아이템이므로, 이후 창업 전/후 기능들이 이 워크스페이스(=아이템)를 기준으로 동작한다.
  const handleCreateWorkspaceFromItem = useCallback((item) => {
    const created = {
      id: `item-${Date.now()}`,
      name: item.title,
      desc: item.category || item.location || '추천 아이템',
      fit: item.score ?? null,
      recommend: item.reason ?? '',
      selectedIdea: { ...item },
    }
    setWorkspaceList((list) => [...list, created])
    setWorkspace(created)
    setFeatureWorkspace((prev) => ({ ...prev, selectedIdea: created.selectedIdea }))
    setRoute('home')
  }, [])

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
    page = <DiscussPage user={user} go={setRoute} />
  } else if (guardedRoute === 'saved') {
    page = <SavedPage go={setRoute} />
  } else if (guardedRoute === 'simulator') {
    page = <SimulatorPage go={setRoute} workspace={workspace} user={user} startupProfile={startupProfile} />
  } else if (features[guardedRoute]) {
    page = (
      <FeaturePage
        key={guardedRoute === 'item' ? `item-${itemEntryNonce}` : guardedRoute}
        id={guardedRoute}
        go={setRoute}
        user={user}
        startupProfile={startupProfile}
        workspaceContext={featureWorkspace}
        onWorkspaceContextChange={handleFeatureWorkspaceChange}
        workspace={workspace}
        setWorkspace={setWorkspace}
        onCreateWorkspace={handleCreateWorkspaceFromItem}
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
        workspaces={workspaceList}
        workspace={workspace}
        setWorkspace={setWorkspace}
        user={user}
        onLogout={handleLogout}
        onAddItem={handleAddItem}
      />
      {page}
    </div>
  )
}
