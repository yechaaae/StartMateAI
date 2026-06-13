import { useEffect, useRef, useState } from 'react'
import { features, featureOrder } from '../../shared/data/features'
import { agents } from '../../shared/data/agents'
import { profile } from '../../shared/data/profile'
import { Icon } from '../../shared/components/Icon'
import { StartMateLogo } from '../../shared/components/StartMateLogo'
import { buildFeatureNavTheme } from './sidebarFeatureNav'

export const Sidebar = ({ route, go, workspace, workspaces = [], setWorkspace, onCreateWorkspace, user, onLogout }) => {
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
                {workspaces.length === 0 && (
                  <p className="workspace-empty">아직 워크스페이스가 없어요.<br />아이템을 확정하면 만들어져요.</p>
                )}
                {workspaces.map((nextWorkspace) => (
                  <button
                    className={workspace?.id === nextWorkspace.id ? 'on' : ''}
                    key={nextWorkspace.id}
                    onClick={() => {
                      setWorkspace(nextWorkspace)
                      setWorkspaceOpen(false)
                      go('home')
                    }}
                  >
                    <div>
                      <b>{nextWorkspace.title}</b>
                      <small>{nextWorkspace.selectedIdeaTitle ? (nextWorkspace.selectedIdeaCategory ?? '확정 아이템') : '작업공간'}</small>
                    </div>
                  </button>
                ))}
                {onCreateWorkspace && (
                  <button
                    className="workspace-create"
                    type="button"
                    onClick={() => {
                      setWorkspaceOpen(false)
                      onCreateWorkspace()
                    }}
                  >
                    <Icon name="plus" size={15} /> 새 워크스페이스
                  </button>
                )}
              </div>
            </div>
          )}
        </div>

        <button className={route === 'home' ? 'on' : ''} onClick={() => go('home')}>
          {workspace?.title ?? '내 작업공간'}
        </button>

        <p>AI 기능</p>
        {featureOrder.map((id) => {
          const feature = features[id]
          const navTheme = buildFeatureNavTheme(feature, agents)
          return (
            <button
              key={id}
              className={route === id ? 'sidebar-feature-link on' : 'sidebar-feature-link'}
              style={navTheme}
              onClick={() => go(id)}
            >
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
