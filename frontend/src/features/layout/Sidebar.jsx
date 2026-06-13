import { useEffect, useRef, useState } from 'react'
import { features } from '../../shared/data/features'
import { agents } from '../../shared/data/agents'
import { profile } from '../../shared/data/profile'
import { Icon } from '../../shared/components/Icon'
import { StartMateLogo } from '../../shared/components/StartMateLogo'
import { categoryLabel } from '../../shared/data/itemCategory'
import { buildFeatureNavTheme } from './sidebarFeatureNav'

// 사이드바 기능을 창업 단계별로 묶는다. (아이템 추천은 워크스페이스 드롭다운의 '아이템 추가하기'로 진입)
const PRE_STARTUP_FEATURES = ['simulator', 'support', 'plan']
const POST_STARTUP_FEATURES = ['operation', 'sns']

export const Sidebar = ({ route, go, workspaces = [], workspace, setWorkspace, user, onLogout, onAddItem }) => {
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

  const renderFeatureLink = (id) => {
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
  }

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

      <div className="workspace-switcher" ref={switcherRef}>
        <button
          type="button"
          className="ws-switcher-trigger"
          aria-expanded={workspaceOpen}
          aria-label="워크스페이스 전환"
          onClick={() => setWorkspaceOpen((open) => !open)}
        >
          <span className="ws-switcher-text">
            <small>워크스페이스</small>
            <b>{workspace?.name ?? '워크스페이스'}</b>
          </span>
          <Icon name="chevron" size={15} />
        </button>

        {workspaceOpen && (
          <div className="workspace-modal">
            <div className="workspace-modal-list">
              {workspaces.length === 0 && (
                <p className="workspace-empty">아직 워크스페이스가 없어요.<br />아이템을 추가해 시작하세요.</p>
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
                    <b>{nextWorkspace.name}</b>
                    <small>{categoryLabel(nextWorkspace.desc)}</small>
                  </div>
                </button>
              ))}
            </div>
            <button
              type="button"
              className="workspace-add-item"
              onClick={() => {
                setWorkspaceOpen(false)
                onAddItem?.()
              }}
            >
              <Icon name="plus" size={14} /> 아이템 추가하기
            </button>
          </div>
        )}
      </div>

      <nav>
        <button className={route === 'home' ? 'on' : ''} onClick={() => go('home')}>
          <Icon name="home" size={18} /> 홈
        </button>

        <p>창업 전</p>
        {PRE_STARTUP_FEATURES.map((id) => renderFeatureLink(id))}
        <p>창업 후</p>
        {POST_STARTUP_FEATURES.map((id) => renderFeatureLink(id))}
      </nav>

      <button className={route === 'discuss' ? 'discuss-btn on' : 'discuss-btn'} onClick={() => go('discuss')}>
        <Icon name="discuss" size={18} /> 파트너들과 논의하기
      </button>

      <div className="user-box">
        <span>{displayName.slice(0, 1)}</span>
        <b>{displayName}</b>
        <small>{user?.email || `${profile.role} · ${profile.loc}`}</small>
        <button type="button" onClick={onLogout}>로그아웃</button>
      </div>
    </aside>
  )
}
