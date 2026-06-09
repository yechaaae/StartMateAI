import { useEffect, useMemo, useState } from 'react'
import '../App.css'
import { features } from '../shared/data/features'
import { workspaces } from '../shared/data/workspaces'
import { Sidebar } from '../features/layout/Sidebar'
import { DiscussPage } from '../features/pages/DiscussPage'
import { FeaturePage } from '../features/pages/FeaturePage'
import { HomePage } from '../features/pages/HomePage'
import { Landing } from '../features/pages/Landing'
import { Onboarding } from '../features/pages/Onboarding'
import { SavedPage } from '../features/pages/SavedPage'

export default function App() {
  const [route, setRoute] = useState(() => localStorage.getItem('sm_route') || 'landing')
  const [workspace, setWorkspace] = useState(workspaces[0])
  useEffect(() => localStorage.setItem('sm_route', route), [route])
  const full = route === 'landing' || route === 'onboarding'
  const page = useMemo(() => {
    if (route === 'landing') return <Landing go={setRoute} />
    if (route === 'onboarding') return <Onboarding go={setRoute} />
    if (route === 'discuss') return <DiscussPage />
    if (route === 'saved') return <SavedPage />
    if (features[route]) return <FeaturePage key={route} id={route} go={setRoute} />
    return <HomePage go={setRoute} workspace={workspace} />
  }, [route, workspace])

  if (full) return <div className="app-root">{page}</div>
  return <div className="app-root"><Sidebar route={route} go={setRoute} workspace={workspace} setWorkspace={setWorkspace} />{page}</div>
}
