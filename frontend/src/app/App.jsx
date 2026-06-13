import { useCallback, useEffect, useRef, useState } from 'react'
import '../App.css'
import { features } from '../shared/data/features'
import { authApi, savedResultApi, startupProfileApi, workspaceApi } from '../shared/api/client'
import { buildFeatureSavedReport } from '../features/reports/savedReportPayload'
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
import { WorkspacePreparing } from '../features/pages/WorkspacePreparing'
import { OnboardingItemModal } from '../features/pages/OnboardingItemModal'
import { decodeHtmlEntities } from '../shared/lib/text'
import { pathToRoute, routeToPath } from './routePaths'

const publicRoutes = new Set(['landing', 'login', 'signup'])
const LOGIN_HINT_KEY = 'sm_logged_in'
const featureIds = Object.keys(features)

// 백엔드 워크스페이스 응답을 사이드바/홈이 쓰는 형태(name/desc/selectedIdea)로 매핑한다.
// AI 생성 텍스트의 HTML 엔티티(&lsquo; 등)가 화면에 날것으로 노출되지 않게 제목/근거는 디코딩한다.
const toClientWorkspace = (ws) => ({
  id: ws.id,
  name: decodeHtmlEntities(ws.title),
  desc: ws.selectedIdeaCategory || '작업공간',
  fit: ws.selectedIdeaScore ?? null,
  recommend: decodeHtmlEntities(ws.selectedIdeaReason || ''),
  selectedIdea: ws.selectedIdeaTitle
    ? {
        title: decodeHtmlEntities(ws.selectedIdeaTitle),
        category: ws.selectedIdeaCategory,
        score: ws.selectedIdeaScore,
        reason: decodeHtmlEntities(ws.selectedIdeaReason),
      }
    : null,
})

export default function App() {
  const [route, setRoute] = useState(() => (
    pathToRoute(window.location.pathname, featureIds)
    || localStorage.getItem('sm_route')
    || 'landing'
  ))
  // 워크스페이스 = 아이템. 아이템 추천에서 '이 아이템으로 시작'을 누르면 새 워크스페이스가 생긴다.
  // 백엔드 API로 영속화하므로 새로고침해도 유지된다.
  const [workspaceList, setWorkspaceList] = useState([])
  const [workspace, setWorkspace] = useState(null)
  const [user, setUser] = useState(null)
  const [profileStatus, setProfileStatus] = useState(null)
  const [startupProfile, setStartupProfile] = useState(null)
  const [featureWorkspace, setFeatureWorkspace] = useState({})
  // '아이템 추가하기'로 진입하면 아이템 기능의 추천/직접입력 선택 화면을 보여준다.
  // nonce는 이미 아이템 페이지에 있을 때도 강제로 remount해서 선택 화면부터 다시 시작하게 한다.
  const [itemEntryNonce, setItemEntryNonce] = useState(0)
  // 아이템 선택 직후 워크스페이스를 만드는 동안 보여주는 짧은 준비 로딩 (null이면 비활성)
  const [preparing, setPreparing] = useState(null)
  // 회원가입 직후 아이템(추천/직접입력)을 고르는 모달 흐름
  const [itemModal, setItemModal] = useState(false)
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
      const list = (await workspaceApi.list()).map(toClientWorkspace)
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
    const resolvedProfile = nextProfile ?? await refreshStartupProfile()
    setStartupProfile(resolvedProfile)
    // 처음 가입 직후 창업 아이템이 없으면 home으로 가지 않고 '추천/직접입력' 모달을 띄운다.
    // (창업 후로 이미 운영 아이템을 입력했다면 홈으로 바로 이동)
    const hasItem = Boolean(resolvedProfile?.currentItemName && resolvedProfile.currentItemName.trim())
    setRoute('home')
    if (!hasItem) {
      setItemModal(true)
    }
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

  const handleAddItem = useCallback(() => {
    // 추천/직접입력 선택부터 추천목록·아이템 입력까지 모달(OnboardingItemModal)로 진행한다.
    setItemModal(true)
  }, [])

  // '이 아이템으로 시작'(추천/직접입력) → 그 아이템으로 워크스페이스를 만들어(백엔드 영속화) 현재 워크스페이스로 설정한다.
  // 워크스페이스 자체가 아이템이므로, 이후 창업 전/후 기능들이 이 워크스페이스(=아이템)를 기준으로 동작한다.
  const handleCreateWorkspaceFromItem = useCallback(async (item, reportData = null) => {
    const selectedIdea = {
      title: item.title,
      category: item.category || item.location || '추천 아이템',
      score: item.score ?? null,
      reason: item.reason ?? '',
    }
    // 짧은 준비 로딩을 띄우고(최소 표시 시간 보장) 워크스페이스를 만든 뒤 홈으로 진입한다.
    setPreparing({ itemTitle: item.title })
    const startedAt = Date.now()
    const MIN_DISPLAY_MS = 1400
    try {
      // 리포트 생성 시 자동 생성된 미확정 워크스페이스(draft)가 있으면 재사용, 없으면 새로 만든다.
      const list = await workspaceApi.list()
      const draft = [...list].reverse().find((ws) => !ws.selectedIdeaTitle)
      const target = draft ?? await workspaceApi.create({ title: item.title })
      const created = toClientWorkspace(await workspaceApi.update(target.id, { title: item.title, selectedIdea }))
      // 선택한 아이템 리포트를 자동 저장해 home에서 추천 근거/상세 방안을 보여줄 수 있게 한다(best-effort).
      if (reportData?.items?.length) {
        try {
          await savedResultApi.save(
            buildFeatureSavedReport({
              featureId: 'item',
              workspaceId: target.id,
              data: reportData,
              selectedIdeaRank: item.rank ?? null,
            }),
          )
        } catch {
          /* 리포트 저장 실패는 워크스페이스 생성 흐름을 막지 않는다 */
        }
      }
      await refreshWorkspaces()
      setWorkspace(created)
      setFeatureWorkspace((prev) => ({ ...prev, selectedIdea: created.selectedIdea }))
    } catch {
      // 실패 시 메모리 상태로라도 반영
      const fallback = {
        id: `item-${Date.now()}`,
        name: decodeHtmlEntities(item.title),
        desc: selectedIdea.category,
        fit: item.score ?? null,
        recommend: decodeHtmlEntities(item.reason ?? ''),
        selectedIdea: { ...item, title: decodeHtmlEntities(item.title), reason: decodeHtmlEntities(item.reason) },
      }
      setWorkspaceList((prev) => [...prev, fallback])
      setWorkspace(fallback)
      setFeatureWorkspace((prev) => ({ ...prev, selectedIdea: fallback.selectedIdea }))
    } finally {
      const elapsed = Date.now() - startedAt
      if (elapsed < MIN_DISPLAY_MS) {
        await new Promise((resolve) => { window.setTimeout(resolve, MIN_DISPLAY_MS - elapsed) })
      }
      setPreparing(null)
      setRoute('home')
    }
  }, [refreshWorkspaces])

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
    page = <HomePage go={setRoute} workspace={workspace} user={user} />
  }

  if (itemModal) {
    return (
      <div className="app-root">
        <OnboardingItemModal
          stage={startupProfile?.stage}
          user={user}
          startupProfile={startupProfile}
          onSelect={(item, reportData) => {
            setItemModal(false)
            handleCreateWorkspaceFromItem(item, reportData)
          }}
          onClose={() => setItemModal(false)}
        />
      </div>
    )
  }

  if (preparing) {
    return <div className="app-root"><WorkspacePreparing itemTitle={preparing.itemTitle} /></div>
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
