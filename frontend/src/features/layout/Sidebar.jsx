import { useEffect, useRef, useState } from 'react'
import { features, featureOrder } from '../../shared/data/features'
import { profile } from '../../shared/data/profile'
import { workspaces } from '../../shared/data/workspaces'
import { Icon } from '../../shared/components/Icon'
import { StartMateLogo } from '../../shared/components/StartMateLogo'

export const Sidebar = ({ route, go, workspace, setWorkspace, user, onLogout }) => {
  const [workspaceOpen, setWorkspaceOpen] = useState(false)
  const switcherRef = useRef(null)
  const displayName = user?.nickname || profile.name

  useEffect(() => {
    const close = (event) => {
      if (switcherRef.current && !switcherRef.current.contains(event.target)) {
        setWorkspaceOpen(false)
      }
    }
    document.addEventListener('mousedown', close)
    return () => document.removeEventListener('mousedown', close)
  }, [])

  return (
    <aside className="sidebar">
      <div className="sidebar-brand">
        <div className="sidebar-logo">
          <StartMateLogo />
        </div>
        <div>
          <b>StartMate AI</b>
          <small>AI 창업 파트너</small>
        </div>
      </div>

      <button className={route === 'discuss' ? 'discuss-btn on' : 'discuss-btn'} onClick={() => go('discuss')}>
        <Icon name="discuss" size={18} /> AI와 논의하기
      </button>

      <nav>
        <div className="workspace-modal-anchor" ref={switcherRef}>
          <button
            className="workspace-section-trigger"
            type="button"
            aria-expanded={workspaceOpen}
            onClick={() => setWorkspaceOpen((open) => !open)}
          >
            <span>워크스페이스</span>
            <Icon name="chevron" size={14} />
          </button>

          {workspaceOpen && (
            <div className="workspace-modal">
              <div className="workspace-modal-list">
                {workspaces.map((nextWorkspace) => (
                  <button
                    className={workspace.id === nextWorkspace.id ? 'on' : ''}
                    key={nextWorkspace.id}
                    onClick={() => {
                      setWorkspace(nextWorkspace)
                      setWorkspaceOpen(false)
                      go('home')
                    }}
                  >
                    <div>
                      <b>{nextWorkspace.name}</b>
                      <small>{nextWorkspace.desc}</small>
                    </div>
                  </button>
                ))}
              </div>
            </div>
          )}
        </div>

        <button className={route === 'home' ? 'on' : ''} onClick={() => go('home')}>
          {workspace.name}
        </button>

        <p>AI 기능</p>
        {featureOrder.map((id) => {
          const feature = features[id]
          return (
            <button key={id} className={route === id ? 'on' : ''} onClick={() => go(id)}>
              <Icon name={feature.icon} />{feature.title}
            </button>
          )
        })}
        <p>보관함</p>
        <button className={route === 'saved' ? 'on' : ''} onClick={() => go('saved')}>
          <Icon name="bookmark" />저장한 결과
        </button>
      </nav>

      <div className="user-box">
        <span>{displayName.slice(0, 1)}</span>
        <b>{displayName}</b>
        <small>{user?.email || `${profile.role} · ${profile.loc}`}</small>
        <button type="button" onClick={onLogout}>로그아웃</button>
      </div>
    </aside>
  )
}
