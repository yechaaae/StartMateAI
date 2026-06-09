import { useEffect, useRef, useState } from 'react'
import { features, featureOrder } from '../../shared/data/features'
import { profile } from '../../shared/data/profile'
import { workspaces } from '../../shared/data/workspaces'
import { Icon } from '../../shared/components/Icon'

const StartMateLogo = () => (
  <svg viewBox="0 0 64 64" aria-hidden="true">
    <defs>
      <linearGradient id="logoBg" x1="8" x2="56" y1="6" y2="58" gradientUnits="userSpaceOnUse">
        <stop stopColor="#f7f9ff" />
        <stop offset="1" stopColor="#dfe5ff" />
      </linearGradient>
      <linearGradient id="logoBlue" x1="18" x2="50" y1="8" y2="48" gradientUnits="userSpaceOnUse">
        <stop stopColor="#1f5fff" />
        <stop offset="1" stopColor="#5d8cff" />
      </linearGradient>
      <linearGradient id="logoLeaf" x1="17" x2="53" y1="36" y2="59" gradientUnits="userSpaceOnUse">
        <stop stopColor="#c7e96d" />
        <stop offset="1" stopColor="#7fbe43" />
      </linearGradient>
    </defs>
    <rect width="64" height="64" rx="17" fill="url(#logoBg)" />
    <path d="M17 39c-6-17 5-34 22-33 9 .5 17 5 22 12l-8 5c-4-5-9-8-16-8-11-.5-19 11-15 22l-5 2Z" fill="url(#logoBlue)" />
    <path d="M41 10 59 1l-1 19-5-5c-8 17-18 21-20 43-3-21 9-34 17-46l-9-2Z" fill="url(#logoBlue)" />
    <circle cx="31" cy="22" r="6" fill="#fff" />
    <path d="M31 29c-8 4-13 8-14 16 5-5 12-1 14 13 1-16 5-23 13-29-5 2-9 3-13 0Z" fill="#fff" />
    <path d="M31 58c4-15 12-21 22-24 5-2 8-8 8-15-5 10-16 9-23 17-4 5-6 12-7 22Z" fill="url(#logoLeaf)" />
    <path d="M31 58c-4-12-10-17-19-19 3 8 9 10 14 11 3 1 4 4 5 8Z" fill="url(#logoLeaf)" />
  </svg>
)

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
